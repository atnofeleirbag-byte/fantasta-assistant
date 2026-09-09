
import io
import re
import urllib.parse
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="FantAsta Assistant Pro V3",
    page_icon="⚡",
    layout="wide",
)

SEASON = "2026-27"

GAZZETTA_LIST_URL = (
    "https://www.gazzetta.it/calcio/fantanews/"
    "lista-giocatori-fantacalcio-serie-a-2026-27/"
)
FANTACALCIO_STATS_URL = (
    "https://www.fantacalcio.it/statistiche-serie-a/"
    "2026-27/fantacalcio/riepilogo"
)
FANTACALCIO_QUOTES_URL = "https://www.fantacalcio.it/quotazioni-fantacalcio"

SOS_SEARCH_URL = "https://www.sosfanta.com/?s={query}"
GAZZETTA_SEARCH_URL = "https://www.gazzetta.it/ricerca/?q={query}"
FANTACALCIO_SEARCH_URL = "https://www.fantacalcio.it/cerca?q={query}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124 Safari/537.36"
    )
}

DEFAULT_SLOTS = {"P": 3, "D": 8, "C": 8, "A": 6}
DEFAULT_PERC = {"P": 0.08, "D": 0.12, "C": 0.25, "A": 0.55}

STAT_COLS = [
    "PV", "MV", "FM", "Gol", "Assist", "Amm", "Esp",
    "BonusScore", "TitolaritaProxy", "FormaScore",
    "BonusIndex", "RendimentoScore",
]

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.2rem; padding-bottom: 3rem;}
    div[data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,.20);
        padding: 12px;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# STATO
# ------------------------------------------------------------

def init_state():
    defaults = {
        "budget_iniziale": 500,
        "num_partecipanti": 10,
        "slot": DEFAULT_SLOTS.copy(),
        "perc_reparto": DEFAULT_PERC.copy(),
        "rosa": [],
        "speso": 0,
        "giocatori": None,
        "online_stats": None,
        "source_status": {},
        "last_update": None,
        "listone_source": "Nessuno",
        "uploaded_signature": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ------------------------------------------------------------
# UTILITÀ DATI
# ------------------------------------------------------------

def clean_name(value):
    return re.sub(r"\s+", " ", str(value).strip())


def key_name(value):
    s = str(value).lower().strip()
    s = (
        s.replace("á", "a").replace("à", "a")
        .replace("é", "e").replace("è", "e")
        .replace("í", "i").replace("ì", "i")
        .replace("ó", "o").replace("ò", "o")
        .replace("ú", "u").replace("ù", "u")
    )
    s = re.sub(r"[^a-z0-9' ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_role(value):
    s = str(value).strip().upper()

    # Classic: P, D, C, A
    if s in {"P", "D", "C", "A"}:
        return s

    # Alcuni listoni esportano diciture complete
    mapping = {
        "PORTIERE": "P",
        "PORTIERI": "P",
        "DIFENSORE": "D",
        "DIFENSORI": "D",
        "CENTROCAMPISTA": "C",
        "CENTROCAMPISTI": "C",
        "ATTACCANTE": "A",
        "ATTACCANTI": "A",
    }
    if s in mapping:
        return mapping[s]

    # Formati come "A (Pc)" / "D; Ds"
    m = re.match(r"^\s*([PDCA])(?:\s|$|\(|;|,|-)", s)
    return m.group(1) if m else None


def to_num(series):
    s = series.astype(str).str.strip()

    # Formato italiano 1.234,5 -> 1234.5
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    s = s.str.replace(r"[^\d\.-]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def flatten_columns(df):
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [
            " ".join(str(x) for x in tup if str(x).lower() != "nan").strip()
            for tup in out.columns
        ]
    else:
        out.columns = [str(c).strip() for c in out.columns]
    return out


def norm_header(value):
    s = str(value).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


ALIASES = {
    "Nome": {
        "nome", "calciatore", "giocatore", "nome giocatore",
        "player", "calciatore nome",
    },
    "Ruolo": {
        "r", "ruolo", "ruolo classic", "classic",
    },
    "Squadra": {
        "sq", "sqd", "squadra", "team", "club",
    },
    "Quotazione": {
        "quotazione", "quotazioni", "q", "qa", "qt.a", "qta",
        "quot. att.", "quot att", "quotazione attuale",
    },
    "FVM": {
        "fvm", "fvm / 1000", "fvm/1000",
    },
}


def detect_column_map(df):
    result = {}
    normalized = {norm_header(c): c for c in df.columns}

    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                result[canonical] = normalized[alias]
                break

    return result


def looks_like_listone(df):
    m = detect_column_map(df)
    # Squadra non è obbligatoria: alcuni export hanno abbreviazioni particolari.
    return "Nome" in m and "Ruolo" in m


def normalize_listone(df):
    df = flatten_columns(df)
    m = detect_column_map(df)

    if "Nome" not in m or "Ruolo" not in m:
        raise ValueError(
            "Non riconosco le colonne del listone. "
            "Servono almeno Nome/Calciatore e Ruolo/R."
        )

    out = pd.DataFrame()
    out["Nome"] = df[m["Nome"]].map(clean_name)
    out["Ruolo"] = df[m["Ruolo"]].map(normalize_role)

    if "Squadra" in m:
        out["Squadra"] = df[m["Squadra"]].astype(str).str.strip()
    else:
        out["Squadra"] = ""

    if "Quotazione" in m:
        out["Quotazione"] = to_num(df[m["Quotazione"]])
    elif "FVM" in m:
        # Se manca la quotazione uso FVM solo come riferimento numerico.
        out["Quotazione"] = to_num(df[m["FVM"]])
    else:
        out["Quotazione"] = np.nan

    out = out[
        out["Nome"].notna()
        & (out["Nome"].str.len() > 1)
        & out["Ruolo"].isin(["P", "D", "C", "A"])
    ].copy()

    out["_key"] = out["Nome"].map(key_name)
    out = out.drop_duplicates("_key", keep="first").reset_index(drop=True)

    if out.empty:
        raise ValueError(
            "Il file è stato aperto, ma non ho trovato giocatori Classic P/D/C/A."
        )

    return out


def read_uploaded_listone(uploaded_file):
    data = uploaded_file.getvalue()
    filename = uploaded_file.name.lower()

    candidates = []

    if filename.endswith(".csv"):
        # Prova separatore automatico e codifiche comuni.
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                text = data.decode(enc)
                # Prova intestazione su più righe: alcuni CSV hanno righe descrittive.
                for header in range(0, 7):
                    try:
                        df = pd.read_csv(
                            io.StringIO(text),
                            sep=None,
                            engine="python",
                            header=header,
                        )
                        candidates.append(df)
                    except Exception:
                        pass
            except Exception:
                pass

    else:
        # Prova tutte le intestazioni iniziali e tutti i fogli.
        excel = pd.ExcelFile(io.BytesIO(data))
        for sheet in excel.sheet_names:
            for header in range(0, 10):
                try:
                    df = pd.read_excel(
                        io.BytesIO(data),
                        sheet_name=sheet,
                        header=header,
                    )
                    candidates.append(df)
                except Exception:
                    pass

    # Scegli il candidato con il maggior numero di righe che sembra un listone.
    valid = []
    for df in candidates:
        try:
            flat = flatten_columns(df)
            if looks_like_listone(flat):
                normalized = normalize_listone(flat)
                valid.append(normalized)
        except Exception:
            pass

    if not valid:
        raise ValueError(
            "Non riesco a riconoscere il formato. "
            "Nel listone devono esserci almeno una colonna Nome/Calciatore "
            "e una colonna Ruolo/R."
        )

    return max(valid, key=len)


# ------------------------------------------------------------
# FONTI ONLINE
# ------------------------------------------------------------

@st.cache_data(ttl=1800, show_spinner=False)
def read_html_tables(url):
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    return pd.read_html(io.StringIO(response.text))


def pick_col(df, candidates):
    low = {norm_header(c): c for c in df.columns}

    for cand in candidates:
        if norm_header(cand) in low:
            return low[norm_header(cand)]

    for cand in candidates:
        c = norm_header(cand)
        for header, original in low.items():
            if c in header:
                return original

    return None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_gazzetta_listone():
    tables = read_html_tables(GAZZETTA_LIST_URL)

    best = None
    best_score = -1

    for raw in tables:
        df = flatten_columns(raw)
        text = " ".join(map(str, df.columns)).lower()
        score = (
            int("giocatore" in text)
            + int("ruolo" in text)
            + int("quot" in text)
            + int("sqd" in text or "squadra" in text)
        )
        if len(df) >= 20 and score > best_score:
            best = df
            best_score = score

    if best is None:
        raise ValueError("tabella Gazzetta non trovata")

    c_nome = pick_col(best, ["Giocatore", "Nome"])
    c_ruolo = pick_col(best, ["Ruolo"])
    c_squadra = pick_col(best, ["Sqd", "Squadra"])
    c_quote = pick_col(best, ["Quotazioni", "Quotazione", "Q"])

    if c_nome is None or c_ruolo is None:
        raise ValueError("colonne Gazzetta non riconosciute")

    out = pd.DataFrame({
        "Nome": best[c_nome].map(clean_name),
        "Ruolo": best[c_ruolo].map(normalize_role),
        "Squadra": (
            best[c_squadra].astype(str).str.strip()
            if c_squadra is not None else ""
        ),
        "Quotazione": (
            to_num(best[c_quote])
            if c_quote is not None else np.nan
        ),
    })

    # Se Gazzetta espone anche dati stagionali li prendiamo.
    for new_col, aliases in {
        "PV_GAZ": ["PG", "Partite giocate"],
        "Gol_GAZ": ["G", "Gol"],
        "Assist_GAZ": ["A", "Assist"],
        "MV_GAZ": ["MV"],
        "FM_GAZ": ["MM", "Media Magic Voto"],
    }.items():
        c = pick_col(best, aliases)
        out[new_col] = to_num(best[c]) if c is not None else np.nan

    out = out[
        out["Nome"].notna()
        & out["Ruolo"].isin(["P", "D", "C", "A"])
    ].copy()

    out["_key"] = out["Nome"].map(key_name)
    return out.drop_duplicates("_key").reset_index(drop=True)


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fantacalcio_stats():
    tables = read_html_tables(FANTACALCIO_STATS_URL)

    best = None
    best_score = -1

    for raw in tables:
        df = flatten_columns(raw)
        text = " ".join(map(str, df.columns)).lower()
        score = sum(x in text for x in ["pv", "mv", "fm", "gol", "ass"])
        if len(df) >= 20 and score > best_score:
            best = df
            best_score = score

    if best is None:
        raise ValueError("tabella statistiche Fantacalcio non trovata")

    c_nome = pick_col(best, ["Calciatore", "Giocatore", "Nome"])

    if c_nome is None:
        object_cols = [
            c for c in best.columns
            if best[c].dtype == object
        ]
        if object_cols:
            c_nome = max(
                object_cols,
                key=lambda c: best[c].astype(str).str.len().mean()
            )

    if c_nome is None:
        raise ValueError("nome giocatore Fantacalcio non riconosciuto")

    out = pd.DataFrame({"Nome": best[c_nome].map(clean_name)})

    mapping = {
        "PV": ["PV"],
        "MV": ["MV"],
        "FM": ["FM"],
        "Gol": ["Gol"],
        "Assist": ["Ass", "Assist"],
        "Amm": ["Amm"],
        "Esp": ["Esp"],
    }

    for new_col, aliases in mapping.items():
        col = pick_col(best, aliases)
        out[new_col] = to_num(best[col]) if col is not None else np.nan

    out["_key"] = out["Nome"].map(key_name)
    out = out[out["Nome"].str.len() > 1]
    return out.drop_duplicates("_key").reset_index(drop=True)


def compute_scores(df):
    out = df.copy()

    for c in ["PV", "MV", "FM", "Gol", "Assist", "Amm", "Esp"]:
        if c not in out.columns:
            out[c] = np.nan

    pv = out["PV"].fillna(0).clip(lower=0)
    mv = out["MV"].fillna(6.0)
    fm = out["FM"].fillna(mv)
    bonus = out["Gol"].fillna(0) * 3 + out["Assist"].fillna(0)

    out["BonusScore"] = bonus

    max_pv = max(float(pv.max()), 1.0)
    max_bonus = max(float(bonus.max()), 1.0)

    out["TitolaritaProxy"] = np.clip(pv / max_pv * 100, 0, 100)
    out["FormaScore"] = np.clip((fm - 5.5) / 3.0 * 10, 0, 10)
    out["BonusIndex"] = np.clip(bonus / max_bonus * 10, 0, 10)

    out["RendimentoScore"] = (
        out["FormaScore"] * 0.45
        + out["BonusIndex"] * 0.35
        + (out["TitolaritaProxy"] / 10) * 0.20
    )

    return out


def merge_listone_stats(listone, stats):
    base = listone.copy()

    if stats is not None and not stats.empty:
        keep = ["_key", "PV", "MV", "FM", "Gol", "Assist", "Amm", "Esp"]
        keep = [c for c in keep if c in stats.columns]
        base = base.merge(stats[keep], on="_key", how="left")
    else:
        for c in ["PV", "MV", "FM", "Gol", "Assist", "Amm", "Esp"]:
            base[c] = np.nan

    return compute_scores(base)


def load_online_data():
    status = {}

    listone = None
    stats = None

    try:
        listone = fetch_gazzetta_listone()
        status["Gazzetta listone"] = f"OK ({len(listone)})"
    except Exception as e:
        status["Gazzetta listone"] = f"KO: {e}"

    try:
        stats = fetch_fantacalcio_stats()
        status["Fantacalcio statistiche"] = f"OK ({len(stats)})"
    except Exception as e:
        status["Fantacalcio statistiche"] = f"KO: {e}"

    if listone is None or listone.empty:
        raise RuntimeError(
            "Non sono riuscito a costruire il listone online. "
            "Puoi comunque caricare il listone ufficiale nella sidebar."
        )

    data = merge_listone_stats(listone, stats)
    return data, stats, status


@st.cache_data(ttl=900, show_spinner=False)
def fetch_sos_news(player_name, max_items=6):
    q = urllib.parse.quote(player_name)
    url = SOS_SEARCH_URL.format(query=q)

    items = []

    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        surname = player_name.split()[-1].lower()
        seen = set()

        for a in soup.find_all("a", href=True):
            title = " ".join(a.get_text(" ", strip=True).split())
            href = a["href"]

            if (
                len(title) >= 20
                and surname in title.lower()
                and href.startswith("http")
                and href not in seen
            ):
                seen.add(href)
                items.append({
                    "Fonte": "SOS Fanta",
                    "Titolo": title[:180],
                    "Link": href,
                })

                if len(items) >= max_items:
                    break

    except Exception:
        pass

    return items


def news_signal(items):
    text = " ".join(i["Titolo"].lower() for i in items)

    positive = [
        "titolare", "recuper", "rientra", "convoc",
        "rigor", "bonus", "gol", "assist", "ok",
    ]
    negative = [
        "infortun", "stop", "out", "panchina",
        "dubbio", "problema", "salta", "rischio",
    ]

    score = (
        sum(text.count(x) for x in positive)
        - sum(text.count(x) for x in negative)
    )

    return float(np.clip(score, -4, 4))


# ------------------------------------------------------------
# ROSA / BUDGET
# ------------------------------------------------------------

def slot_occupati(role):
    return sum(
        1 for x in st.session_state["rosa"]
        if x["Ruolo"] == role
    )


def slot_liberi(role):
    return max(
        int(st.session_state["slot"][role]) - slot_occupati(role),
        0,
    )


def speso_reparto(role):
    return sum(
        float(x["Prezzo"])
        for x in st.session_state["rosa"]
        if x["Ruolo"] == role
    )


def target_reparto(role):
    return (
        st.session_state["budget_iniziale"]
        * st.session_state["perc_reparto"][role]
    )


def budget_rimasto():
    return (
        st.session_state["budget_iniziale"]
        - st.session_state["speso"]
    )


def crediti_minimi_da_salvare():
    return sum(slot_liberi(r) for r in "PDCA")


def max_theoretical_bid(role):
    # Dopo l'acquisto devo riuscire a comprare almeno a 1 FM tutti gli slot rimanenti.
    slots_after_this = max(crediti_minimi_da_salvare() - 1, 0)
    return max(int(budget_rimasto() - slots_after_this), 1)


def squad_need_score(role):
    if role not in "PDCA" or slot_liberi(role) <= 0:
        return 0.0

    free_ratio = slot_liberi(role) / max(
        st.session_state["slot"][role], 1
    )

    target = max(target_reparto(role), 1)
    target_gap = max(target - speso_reparto(role), 0) / target

    return float(
        np.clip(
            (free_ratio * 0.55 + target_gap * 0.45) * 10,
            0,
            10,
        )
    )


def reserve_for_other_roles(current_role):
    budget = budget_rimasto()
    reserve = 0.0

    for role in "PDCA":
        if role == current_role or slot_liberi(role) == 0:
            continue

        target_gap = max(
            target_reparto(role) - speso_reparto(role),
            slot_liberi(role),
        )
        reserve += target_gap

    max_reserve = max(
        budget - max(slot_liberi(current_role), 1),
        0,
    )

    return min(reserve, max_reserve)


def recommended_price(row, available_df):
    role = row.get("Ruolo")

    if role not in "PDCA":
        return 1

    free = max(slot_liberi(role), 1)

    role_budget = max(
        budget_rimasto() - reserve_for_other_roles(role),
        free,
    )

    avg = role_budget / free

    quality = (
        float(row["RendimentoScore"])
        if pd.notna(row.get("RendimentoScore"))
        else 5.0
    )

    quote = (
        float(row["Quotazione"])
        if pd.notna(row.get("Quotazione"))
        else 1.0
    )

    role_quotes = pd.to_numeric(
        available_df.loc[
            available_df["Ruolo"] == role,
            "Quotazione"
        ],
        errors="coerce",
    ).dropna()

    role_max_quote = (
        max(float(role_quotes.max()), 1.0)
        if not role_quotes.empty
        else max(quote, 1.0)
    )

    quote_factor = np.clip(
        quote / role_max_quote,
        0.15,
        1.0,
    )

    multiplier = (
        0.55
        + 0.55 * (quality / 10)
        + 0.35 * quote_factor
    )

    price = round(avg * multiplier)

    return int(
        np.clip(
            price,
            1,
            max_theoretical_bid(role),
        )
    )


def verdict(current_price, recommended):
    if current_price <= max(1, round(recommended * 0.70)):
        return "AFFARE"
    if current_price <= round(recommended * 0.90):
        return "OTTIMO"
    if current_price <= recommended:
        return "OK"
    if current_price <= round(recommended * 1.12):
        return "CARO"
    return "STOP"


def add_player_to_roster(player_name, price, dataframe):
    found = dataframe[dataframe["Nome"] == player_name]

    if found.empty:
        return False, "Giocatore non trovato nel listone."

    row = found.iloc[0]
    role = row["Ruolo"]

    if any(x["Nome"] == player_name for x in st.session_state["rosa"]):
        return False, "Giocatore già presente nella tua rosa."

    if role not in "PDCA":
        return False, "Ruolo non valido."

    if slot_liberi(role) <= 0:
        return False, f"Il reparto {role} è già completo."

    if int(price) > budget_rimasto():
        return False, "Il prezzo supera il budget residuo."

    if int(price) > max_theoretical_bid(role):
        return (
            False,
            "Con questo prezzo non avresti più almeno 1 FM "
            "per ogni slot ancora da completare."
        )

    st.session_state["rosa"].append({
        "Nome": player_name,
        "Ruolo": role,
        "Prezzo": int(price),
    })
    st.session_state["speso"] += int(price)

    return True, f"{player_name} aggiunto alla rosa per {int(price)} FM."


# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------

st.title("⚡ FantAsta Assistant Pro V3")
st.caption(
    "La tua rosa e il tuo budget al centro. "
    "Statistiche online + valutazione dinamica dell'acquisto."
)

with st.sidebar:
    st.header("⚙️ Impostazioni lega")

    budget = st.number_input(
        "Budget iniziale",
        min_value=100,
        max_value=2000,
        value=int(st.session_state["budget_iniziale"]),
        step=50,
    )

    partecipanti = st.number_input(
        "Numero partecipanti",
        min_value=4,
        max_value=20,
        value=int(st.session_state["num_partecipanti"]),
    )

    st.subheader("Slot rosa")

    slot_new = {
        "P": st.number_input(
            "Portieri", 1, 5,
            int(st.session_state["slot"]["P"])
        ),
        "D": st.number_input(
            "Difensori", 1, 12,
            int(st.session_state["slot"]["D"])
        ),
        "C": st.number_input(
            "Centrocampisti", 1, 12,
            int(st.session_state["slot"]["C"])
        ),
        "A": st.number_input(
            "Attaccanti", 1, 10,
            int(st.session_state["slot"]["A"])
        ),
    }

    if st.button(
        "Salva impostazioni",
        use_container_width=True,
    ):
        st.session_state["budget_iniziale"] = int(budget)
        st.session_state["num_partecipanti"] = int(partecipanti)
        st.session_state["slot"] = {
            k: int(v) for k, v in slot_new.items()
        }
        st.rerun()

    st.divider()
    st.header("📥 Listone")

    if st.button(
        "🌐 Carica / aggiorna automaticamente",
        use_container_width=True,
        type="primary",
    ):
        try:
            with st.spinner(
                "Recupero listone Gazzetta e statistiche Fantacalcio..."
            ):
                data, stats, status = load_online_data()

            st.session_state["giocatori"] = data
            st.session_state["online_stats"] = stats
            st.session_state["source_status"] = status
            st.session_state["listone_source"] = "Online"
            st.session_state["last_update"] = datetime.now().strftime(
                "%d/%m/%Y %H:%M"
            )
            st.session_state["uploaded_signature"] = None

            st.success(
                f"Listone online caricato: {len(data)} giocatori."
            )

        except Exception as e:
            st.error(str(e))

    st.caption("Oppure carica il listone ufficiale Classic:")

    uploaded = st.file_uploader(
        "CSV o Excel",
        type=["csv", "xlsx", "xls"],
        help=(
            "Riconosco automaticamente intestazioni come "
            "R, Ruolo, Nome, Calciatore, Squadra, Qt.A, Quotazione."
        ),
    )

    if uploaded is not None:
        signature = (
            uploaded.name,
            len(uploaded.getvalue()),
            hash(uploaded.getvalue()[:2048]),
        )

        if signature != st.session_state["uploaded_signature"]:
            try:
                parsed = read_uploaded_listone(uploaded)

                # Se riesco, arricchisco con statistiche online.
                stats = st.session_state.get("online_stats")

                if stats is None:
                    try:
                        stats = fetch_fantacalcio_stats()
                        st.session_state["online_stats"] = stats
                        st.session_state["source_status"][
                            "Fantacalcio statistiche"
                        ] = f"OK ({len(stats)})"
                    except Exception as e:
                        st.session_state["source_status"][
                            "Fantacalcio statistiche"
                        ] = f"KO: {e}"

                data = merge_listone_stats(parsed, stats)

                st.session_state["giocatori"] = data
                st.session_state["listone_source"] = (
                    f"File: {uploaded.name}"
                )
                st.session_state["uploaded_signature"] = signature
                st.session_state["last_update"] = datetime.now().strftime(
                    "%d/%m/%Y %H:%M"
                )

                st.success(
                    f"✓ Letti correttamente {len(data)} giocatori."
                )

            except Exception as e:
                st.error(f"Errore nel listone: {e}")

    current = st.session_state["giocatori"]

    if current is not None and not current.empty:
        st.success(
            f"LISTONE ATTIVO: {len(current)} giocatori"
        )
        st.caption(
            f"Fonte: {st.session_state['listone_source']}"
        )
        with st.expander("Controlla anteprima"):
            preview_cols = [
                c for c in
                ["Nome", "Ruolo", "Squadra", "Quotazione"]
                if c in current.columns
            ]
            st.dataframe(
                current[preview_cols].head(8),
                hide_index=True,
                use_container_width=True,
            )
    else:
        st.warning("Nessun listone attivo.")


# ------------------------------------------------------------
# CARICAMENTO INIZIALE ONLINE
# ------------------------------------------------------------

if st.session_state["giocatori"] is None:
    try:
        with st.spinner("Provo a caricare il listone online..."):
            data, stats, status = load_online_data()

        st.session_state["giocatori"] = data
        st.session_state["online_stats"] = stats
        st.session_state["source_status"] = status
        st.session_state["listone_source"] = "Online"
        st.session_state["last_update"] = datetime.now().strftime(
            "%d/%m/%Y %H:%M"
        )
    except Exception:
        st.session_state["giocatori"] = pd.DataFrame(
            columns=[
                "Nome", "Ruolo", "Squadra", "Quotazione",
                *STAT_COLS,
            ]
        )


df = st.session_state["giocatori"].copy()

for c in ["Nome", "Ruolo", "Squadra", "Quotazione", *STAT_COLS]:
    if c not in df.columns:
        df[c] = np.nan

if "_key" not in df.columns:
    df["_key"] = df["Nome"].map(key_name)

taken_names = {
    x["Nome"] for x in st.session_state["rosa"]
}

df_disponibili = df[
    ~df["Nome"].isin(taken_names)
].copy()


# ------------------------------------------------------------
# RIEPILOGO PRINCIPALE
# ------------------------------------------------------------

b_left = budget_rimasto()
slots_left = sum(slot_liberi(r) for r in "PDCA")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Budget residuo",
    f"{b_left} FM",
)
c2.metric(
    "Budget speso",
    f"{st.session_state['speso']} FM",
)
c3.metric(
    "Giocatori in rosa",
    f"{len(st.session_state['rosa'])}",
)
c4.metric(
    "Slot ancora liberi",
    f"{slots_left}",
)

if not df.empty:
    st.caption(
        f"Listone: {len(df)} giocatori · "
        f"Fonte: {st.session_state['listone_source']} · "
        f"Aggiornato: {st.session_state['last_update'] or '-'}"
    )
else:
    st.error(
        "Non c'è ancora un listone utilizzabile. "
        "Apri la sidebar e premi “Carica / aggiorna automaticamente” "
        "oppure carica il file ufficiale."
    )


# ------------------------------------------------------------
# TAB
# ------------------------------------------------------------

tab_rosa, tab_asta, tab_giocatori, tab_news = st.tabs([
    "📋 LA MIA ROSA",
    "🎯 ASSISTENTE ASTA",
    "📊 GIOCATORI",
    "📰 NEWS",
])


# ------------------------------------------------------------
# TAB ROSA — aggiunta giocatori molto evidente
# ------------------------------------------------------------

with tab_rosa:
    st.subheader("➕ Registra un acquisto")

    if df_disponibili.empty:
        st.info(
            "Non ci sono giocatori disponibili nel listone."
        )
    else:
        st.write(
            "Quando acquisti un giocatore all'asta, "
            "selezionalo qui, inserisci il prezzo pagato e premi "
            "**AGGIUNGI ALLA MIA ROSA**."
        )

        with st.form(
            "quick_add_roster",
            clear_on_submit=False,
        ):
            add_c1, add_c2 = st.columns([3, 1])

            player_to_add = add_c1.selectbox(
                "Giocatore acquistato",
                options=df_disponibili["Nome"].tolist(),
                index=None,
                placeholder="Scrivi il nome del giocatore...",
            )

            max_price_input = max(
                int(budget_rimasto()),
                1,
            )

            price_to_add = add_c2.number_input(
                "Prezzo pagato (FM)",
                min_value=1,
                max_value=max_price_input,
                value=1,
            )

            submitted = st.form_submit_button(
                "➕ AGGIUNGI ALLA MIA ROSA",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not player_to_add:
                st.error("Seleziona prima un giocatore.")
            else:
                ok, msg = add_player_to_roster(
                    player_to_add,
                    price_to_add,
                    df,
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    st.divider()
    st.subheader("Situazione della rosa")

    reparto_rows = []

    for role in "PDCA":
        reparto_rows.append({
            "Ruolo": role,
            "Giocatori": (
                f"{slot_occupati(role)}/"
                f"{st.session_state['slot'][role]}"
            ),
            "Slot liberi": slot_liberi(role),
            "Speso": int(speso_reparto(role)),
            "Target budget": round(target_reparto(role)),
            "Priorità": round(squad_need_score(role), 1),
        })

    st.dataframe(
        pd.DataFrame(reparto_rows),
        hide_index=True,
        use_container_width=True,
    )

    if st.session_state["rosa"]:
        rosa_df = pd.DataFrame(
            st.session_state["rosa"]
        )

        st.dataframe(
            rosa_df,
            hide_index=True,
            use_container_width=True,
        )

        with st.expander("Rimuovi un acquisto errato"):
            remove_name = st.selectbox(
                "Giocatore da rimuovere",
                rosa_df["Nome"].tolist(),
                key="remove_roster_player",
            )

            if st.button(
                "Rimuovi dalla rosa",
                key="remove_roster_btn",
            ):
                item = next(
                    x for x in st.session_state["rosa"]
                    if x["Nome"] == remove_name
                )

                st.session_state["rosa"].remove(item)
                st.session_state["speso"] -= item["Prezzo"]
                st.rerun()

    else:
        st.info(
            "La tua rosa è ancora vuota. "
            "Usa il modulo qui sopra per registrare il primo acquisto."
        )

    with st.expander("Reset completo asta"):
        if st.button(
            "🗑️ Azzera rosa e budget speso",
            key="reset_roster",
        ):
            st.session_state["rosa"] = []
            st.session_state["speso"] = 0
            st.rerun()


# ------------------------------------------------------------
# TAB ASSISTENTE
# ------------------------------------------------------------

with tab_asta:
    st.subheader("Giocatore attualmente all'asta")

    valid = df_disponibili.dropna(
        subset=["Nome", "Ruolo"]
    ).copy()

    if valid.empty:
        st.info(
            "Carica prima un listone oppure completa la rosa."
        )
    else:
        selected = st.selectbox(
            "Cerca il giocatore chiamato",
            options=valid["Nome"].tolist(),
            index=None,
            placeholder="Inizia a digitare il nome...",
            key="auction_player",
        )

        if selected:
            row = valid[
                valid["Nome"] == selected
            ].iloc[0]

            role = row["Ruolo"]

            rec = recommended_price(
                row,
                df_disponibili,
            )

            theoretical = max_theoretical_bid(role)

            current_bid = st.number_input(
                "Offerta attuale / prezzo finale (FM)",
                min_value=1,
                max_value=max(theoretical, 1),
                value=min(max(rec, 1), max(theoretical, 1)),
                key="auction_bid",
            )

            result = verdict(
                current_bid,
                rec,
            )

            m1, m2, m3, m4 = st.columns(4)

            m1.metric(
                "Ruolo",
                role,
            )
            m2.metric(
                "Prezzo consigliato",
                f"{rec} FM",
            )
            m3.metric(
                "Massimo teorico",
                f"{theoretical} FM",
            )
            m4.metric(
                "Priorità reparto",
                f"{squad_need_score(role):.1f}/10",
            )

            if result == "AFFARE":
                st.success(
                    f"🟢 AFFARE — a {current_bid} FM "
                    "sei molto sotto il prezzo obiettivo."
                )
            elif result == "OTTIMO":
                st.success(
                    f"🟢 OTTIMO — a {current_bid} FM "
                    "l'acquisto è conveniente."
                )
            elif result == "OK":
                st.info(
                    f"🟡 OK — sei vicino al limite consigliato "
                    f"di {rec} FM."
                )
            elif result == "CARO":
                st.warning(
                    f"🟠 CARO — sei oltre il prezzo consigliato "
                    f"di {rec} FM."
                )
            else:
                st.error(
                    f"🔴 STOP — per la tua rosa attuale "
                    f"io lo lascerei andare oltre {rec} FM."
                )

            data_c1, data_c2, data_c3, data_c4, data_c5 = st.columns(5)

            def fmt(value, digits=1):
                if pd.isna(value):
                    return "n.d."
                return f"{float(value):.{digits}f}"

            data_c1.metric("Presenze", fmt(row["PV"], 0))
            data_c2.metric("Media voto", fmt(row["MV"], 2))
            data_c3.metric("Fantamedia", fmt(row["FM"], 2))
            data_c4.metric("Gol", fmt(row["Gol"], 0))
            data_c5.metric("Assist", fmt(row["Assist"], 0))

            if st.button(
                f"➕ ACQUISTATO A {current_bid} FM — AGGIUNGI ALLA ROSA",
                type="primary",
                use_container_width=True,
                key="auction_add_btn",
            ):
                ok, msg = add_player_to_roster(
                    selected,
                    current_bid,
                    df,
                )

                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


# ------------------------------------------------------------
# TAB GIOCATORI
# ------------------------------------------------------------

with tab_giocatori:
    st.subheader("Listone e classifica guidata")

    if df_disponibili.empty:
        st.info("Nessun giocatore disponibile.")
    else:
        filt = st.selectbox(
            "Filtra per ruolo",
            ["Tutti", "P", "D", "C", "A"],
            key="role_filter",
        )

        view = df_disponibili.copy()

        if filt != "Tutti":
            view = view[
                view["Ruolo"] == filt
            ]

        view["PrioritaRosa"] = view["Ruolo"].map(
            lambda r: squad_need_score(r)
            if r in "PDCA" else 0
        )

        view["ScoreGuidato"] = (
            view["RendimentoScore"].fillna(5) * 0.75
            + view["PrioritaRosa"] * 0.25
        )

        view = view.sort_values(
            "ScoreGuidato",
            ascending=False,
        )

        show_cols = [
            "Nome", "Ruolo", "Squadra", "Quotazione",
            "PV", "MV", "FM", "Gol", "Assist",
            "RendimentoScore", "PrioritaRosa",
            "ScoreGuidato",
        ]

        st.dataframe(
            view[show_cols],
            hide_index=True,
            use_container_width=True,
        )


# ------------------------------------------------------------
# TAB NEWS
# ------------------------------------------------------------

with tab_news:
    st.subheader("News e contesto del giocatore")

    if df.empty:
        st.info("Carica prima il listone.")
    else:
        player = st.selectbox(
            "Cerca giocatore",
            df["Nome"].tolist(),
            index=None,
            placeholder="Scrivi il nome...",
            key="news_player",
        )

        if player:
            news = fetch_sos_news(player)
            signal = news_signal(news)

            st.metric(
                "Segnale SOS Fanta",
                f"{signal:+.0f}",
                help=(
                    "Indicatore sintetico basato sui titoli recenti. "
                    "Non sostituisce la lettura della notizia."
                ),
            )

            if news:
                for item in news:
                    st.markdown(
                        f"- **{item['Fonte']}** — "
                        f"[{item['Titolo']}]({item['Link']})"
                    )
            else:
                st.info(
                    "Nessun titolo SOS Fanta trovato automaticamente."
                )

            q = urllib.parse.quote(player)

            st.markdown(
                f"[Fantacalcio.it]("
                f"{FANTACALCIO_SEARCH_URL.format(query=q)})"
                " · "
                f"[Gazzetta]("
                f"{GAZZETTA_SEARCH_URL.format(query=q)})"
                " · "
                f"[SOS Fanta]("
                f"{SOS_SEARCH_URL.format(query=q)})"
            )


st.divider()

if st.session_state["source_status"]:
    with st.expander("Stato fonti online"):
        for source, status in st.session_state["source_status"].items():
            st.write(f"**{source}:** {status}")

st.caption(
    "Le fonti web possono modificare la struttura delle proprie pagine. "
    "Per questo il caricamento del listone ufficiale resta disponibile come fallback."
)
