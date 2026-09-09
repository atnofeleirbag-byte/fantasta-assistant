
import io
import re
import urllib.parse
import time
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="FantAsta Assistant Pro V6",
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

FBREF_PLAYINGTIME_URL = (
    "https://fbref.com/en/comps/11/2026-2027/playingtime/"
    "2026-2027-Serie-A-M-Stats"
)

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
    "PV", "Starts", "TitolaritaPct", "MV", "FM", "Gol", "Assist",
    "Amm", "Esp", "BonusScore", "TitolaritaProxy", "FormaScore",
    "BonusIndex", "RendimentoScore",
]

st.markdown(
    """
    <style>
    :root {
        --bg: #f5f7fb;
        --panel: #ffffff;
        --ink: #111827;
        --muted: #6b7280;
        --line: #e5e7eb;
        --brand: #111827;
        --accent: #22c55e;
        --warning: #f59e0b;
        --danger: #ef4444;
        --soft: #eef2f7;
    }

    .stApp {
        background: var(--bg);
        color: var(--ink);
    }

    .block-container {
        max-width: 1480px;
        padding-top: 1rem;
        padding-bottom: 4rem;
    }

    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid var(--line);
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.2rem;
    }

    h1, h2, h3 {
        letter-spacing: -0.025em;
    }

    .app-hero {
        background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
        color: white;
        border-radius: 22px;
        padding: 24px 28px;
        margin-bottom: 18px;
        box-shadow: 0 10px 30px rgba(17,24,39,.10);
    }

    .hero-row {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:20px;
    }

    .hero-title {
        font-size: 28px;
        line-height: 1.1;
        font-weight: 760;
        letter-spacing: -0.035em;
        margin: 0;
    }

    .hero-sub {
        color: #cbd5e1;
        font-size: 14px;
        margin-top: 8px;
    }

    .live-badge {
        display:inline-flex;
        align-items:center;
        gap:8px;
        border:1px solid rgba(255,255,255,.18);
        background:rgba(255,255,255,.08);
        padding:8px 12px;
        border-radius:999px;
        font-size:12px;
        white-space:nowrap;
    }

    .live-dot {
        width:8px;
        height:8px;
        border-radius:999px;
        background:#22c55e;
        box-shadow:0 0 0 5px rgba(34,197,94,.12);
    }

    div[data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--line);
        padding: 16px 17px;
        border-radius: 16px;
        box-shadow: 0 4px 14px rgba(17,24,39,.035);
    }

    div[data-testid="stMetricLabel"] {
        color: var(--muted);
    }

    div[data-testid="stMetricValue"] {
        letter-spacing: -0.03em;
    }

    .section-card {
        background: #fff;
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 18px 20px;
        margin: 10px 0 16px;
        box-shadow: 0 5px 18px rgba(17,24,39,.035);
    }

    .micro-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: .08em;
        color: var(--muted);
        font-weight: 700;
    }

    .source-strip {
        display:flex;
        gap:10px;
        flex-wrap:wrap;
        align-items:center;
        margin:8px 0 18px;
    }

    .source-pill {
        padding:7px 10px;
        border-radius:999px;
        background:white;
        border:1px solid var(--line);
        color:#374151;
        font-size:12px;
    }

    .source-pill strong {
        color:#111827;
    }

    div[data-testid="stDataFrame"] {
        border:1px solid var(--line);
        border-radius:14px;
        overflow:hidden;
        background:white;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 7px;
        background: transparent;
        border-bottom: 0;
        flex-wrap: wrap;
    }

    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 12px;
        padding: 0 15px;
        background: white;
        border: 1px solid var(--line);
        color: #4b5563;
    }

    .stTabs [aria-selected="true"] {
        background: #111827 !important;
        color: white !important;
        border-color: #111827 !important;
    }

    .stButton > button, .stFormSubmitButton > button {
        border-radius: 12px;
        min-height: 42px;
        font-weight: 650;
    }

    .stTextInput input,
    .stNumberInput input,
    div[data-baseweb="select"] > div {
        border-radius: 11px !important;
    }

    .decision {
        border-radius:16px;
        padding:15px 17px;
        margin:12px 0;
        font-weight:700;
        border:1px solid;
    }
    .decision.good {background:#ecfdf3; border-color:#bbf7d0; color:#166534;}
    .decision.ok {background:#fffbeb; border-color:#fde68a; color:#92400e;}
    .decision.bad {background:#fef2f2; border-color:#fecaca; color:#991b1b;}

    @media (max-width: 700px) {
        .app-hero {padding:20px;}
        .hero-row {align-items:flex-start; flex-direction:column;}
        .hero-title {font-size:24px;}
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
        "live_sync": True,
        "last_sync_epoch": 0,
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

@st.cache_data(ttl=45, show_spinner=False)
def read_html_tables(url, cache_bucket=None):
    # cache_bucket cambia ogni minuto e impedisce a CDN/browser di restituire
    # una copia vecchia della pagina Fantacalcio.
    bucket = cache_bucket if cache_bucket is not None else int(time.time() // 60)
    separator = "&" if "?" in url else "?"
    fresh_url = f"{url}{separator}_fantasta_refresh={bucket}"
    response = requests.get(
        fresh_url,
        headers={
            **HEADERS,
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
        timeout=20,
    )
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


@st.cache_data(ttl=45, show_spinner=False)
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



@st.cache_data(ttl=45, show_spinner=False)
def fetch_fantacalcio_quotes():
    """
    Recupera dalla pagina Quotazioni Fantacalcio.it i valori Classic correnti:
    QI, QA e FVM. La fonte viene usata per aggiornare il listone già dotato
    di ruoli (Gazzetta o file ufficiale caricato dall'utente).
    """
    tables = read_html_tables(FANTACALCIO_QUOTES_URL)

    best = None
    best_score = -1

    for raw in tables:
        df = flatten_columns(raw)
        text = " ".join(map(str, df.columns)).lower()
        score = (
            int("fvm" in text) * 2
            + int("qa" in text) * 2
            + int("qi" in text)
            + int("calciatore" in text)
        )
        if len(df) >= 100 and score > best_score:
            best = df
            best_score = score

    if best is None:
        raise ValueError("tabella quotazioni Fantacalcio non trovata")

    c_nome = pick_col(best, ["Calciatore", "Giocatore", "Nome"])
    c_sq = pick_col(best, ["Sq", "Squadra"])

    # In pagina ci sono colonne Classic e Mantra duplicate.
    # Pandas di solito rende le seconde QA.1 / QI.1 ecc.; prendiamo la prima.
    cols_norm = [(c, norm_header(c)) for c in best.columns]

    def first_matching(prefix):
        exact = [c for c, n in cols_norm if n == prefix]
        if exact:
            return exact[0]
        begins = [c for c, n in cols_norm if n.startswith(prefix)]
        return begins[0] if begins else None

    c_qi = first_matching("qi")
    c_qa = first_matching("qa")
    c_fvm = next(
        (c for c, n in cols_norm if n.startswith("fvm")),
        None
    )

    if c_nome is None:
        object_cols = [c for c in best.columns if best[c].dtype == object]
        object_cols = [
            c for c in object_cols
            if c != c_sq
        ]
        if object_cols:
            c_nome = max(
                object_cols,
                key=lambda c: best[c].astype(str).str.len().mean()
            )

    if c_nome is None or c_qa is None:
        raise ValueError("colonne quotazioni Fantacalcio non riconosciute")

    out = pd.DataFrame({
        "Nome": best[c_nome].map(clean_name),
        "Squadra_FC": (
            best[c_sq].astype(str).str.strip()
            if c_sq is not None else ""
        ),
        "QI_FC": (
            to_num(best[c_qi])
            if c_qi is not None else np.nan
        ),
        "QA_FC": to_num(best[c_qa]),
        "FVM": (
            to_num(best[c_fvm])
            if c_fvm is not None else np.nan
        ),
    })

    out = out[out["Nome"].notna() & (out["Nome"].str.len() > 1)].copy()
    out["_key"] = out["Nome"].map(key_name)

    return out.drop_duplicates("_key").reset_index(drop=True)


def merge_live_quotes(dataframe, quotes):
    """
    Aggiorna Quotazione con QA Fantacalcio e aggiunge QI/FVM.
    Mantiene ruolo e squadra del listone di base.
    """
    out = dataframe.copy()

    # evita duplicati se la funzione viene richiamata più volte
    for c in ["QI_FC", "QA_FC", "FVM", "Squadra_FC"]:
        if c in out.columns:
            out = out.drop(columns=[c])

    if quotes is None or quotes.empty:
        if "FVM" not in out.columns:
            out["FVM"] = np.nan
        return out

    keep = ["_key", "QI_FC", "QA_FC", "FVM", "Squadra_FC"]
    out = out.merge(quotes[keep], on="_key", how="left")

    if "Quotazione" not in out.columns:
        out["Quotazione"] = np.nan

    # Fantacalcio QA è la quotazione prioritaria; se non c'è resta quella del listone.
    out["Quotazione"] = out["QA_FC"].combine_first(
        pd.to_numeric(out["Quotazione"], errors="coerce")
    )

    return out



def surname_key(name):
    """
    Chiave cognome semplificata per far combaciare Fantacalcio con FBref.
    Fantacalcio usa spesso forme come 'Martinez L.' mentre FBref usa il nome completo.
    """
    s = key_name(name)
    tokens = [t for t in s.split() if len(t) > 1]
    return tokens[-1] if tokens else s


def team_code_map():
    return {
        "ATA": "atalanta",
        "BOL": "bologna",
        "CAG": "cagliari",
        "COM": "como",
        "FIO": "fiorentina",
        "FRO": "frosinone",
        "GEN": "genoa",
        "INT": "inter",
        "JUV": "juventus",
        "LAZ": "lazio",
        "LEC": "lecce",
        "MIL": "milan",
        "MON": "monza",
        "NAP": "napoli",
        "PAR": "parma",
        "PIS": "pisa",
        "ROM": "roma",
        "SAS": "sassuolo",
        "TOR": "torino",
        "UDI": "udinese",
        "VER": "verona",
    }


def normalize_team_name(value):
    s = key_name(value)
    code_map = team_code_map()
    if s.upper() in code_map:
        return code_map[s.upper()]
    # normalizza alcune forme frequenti
    replacements = {
        "internazionale": "inter",
        "hellas verona": "verona",
        "ac milan": "milan",
    }
    return replacements.get(s, s)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_fbref_starts():
    """
    Legge FBref Playing Time: Player, Squad, MP e Starts.
    Restituisce anche il numero di partite della squadra, necessario per
    TitolaritaPct = Starts / TeamMP.
    """
    tables = read_html_tables(FBREF_PLAYINGTIME_URL)

    player_table = None
    squad_table = None

    for raw in tables:
        df = flatten_columns(raw)
        text = " ".join(map(str, df.columns)).lower()

        if (
            len(df) >= 50
            and ("player" in text or "giocatore" in text)
            and "starts" in text
        ):
            player_table = df

        if (
            len(df) >= 10
            and len(df) <= 40
            and "squad" in text
            and "mp" in text
            and "starts" in text
        ):
            # tabella squadra
            squad_table = df

    if player_table is None:
        # fallback: cerca tabella con nome e Starts anche se gli header sono duplicati
        for raw in tables:
            df = flatten_columns(raw)
            pcol = pick_col(df, ["Player"])
            scol = pick_col(df, ["Starts"])
            if len(df) >= 50 and pcol is not None and scol is not None:
                player_table = df
                break

    if player_table is None:
        raise ValueError("tabella giocatori FBref non trovata")

    c_player = pick_col(player_table, ["Player"])
    c_squad = pick_col(player_table, ["Squad"])
    c_starts = pick_col(player_table, ["Starts"])
    c_mp = pick_col(player_table, ["MP"])

    if c_player is None or c_starts is None:
        raise ValueError("colonne Starts FBref non riconosciute")

    out = pd.DataFrame({
        "Nome_FB": player_table[c_player].map(clean_name),
        "Squadra_FB": (
            player_table[c_squad].astype(str).str.strip()
            if c_squad is not None else ""
        ),
        "Starts": to_num(player_table[c_starts]),
        "MP_FB": (
            to_num(player_table[c_mp])
            if c_mp is not None else np.nan
        ),
    })

    out = out[out["Nome_FB"].notna() & (out["Nome_FB"].str.len() > 1)].copy()
    out["_key_fb"] = out["Nome_FB"].map(key_name)
    out["_surname"] = out["Nome_FB"].map(surname_key)
    out["_team_fb"] = out["Squadra_FB"].map(normalize_team_name)

    # TeamMP: se disponibile dalla tabella squadre lo integriamo.
    team_mp = {}
    if squad_table is not None:
        c_team = pick_col(squad_table, ["Squad"])
        c_team_mp = pick_col(squad_table, ["MP"])
        if c_team is not None and c_team_mp is not None:
            for _, r in squad_table.iterrows():
                t = normalize_team_name(r[c_team])
                val = pd.to_numeric(pd.Series([r[c_team_mp]]), errors="coerce").iloc[0]
                if pd.notna(val):
                    team_mp[t] = float(val)

    # Fallback: max MP dei giocatori della squadra approssima le giornate giocate.
    if not team_mp:
        tmp = out.groupby("_team_fb")["MP_FB"].max()
        team_mp = {k: float(v) for k, v in tmp.dropna().items()}

    out["TeamMP"] = out["_team_fb"].map(team_mp)
    out["TitolaritaPct_FB"] = np.where(
        out["TeamMP"].fillna(0) > 0,
        (out["Starts"].fillna(0) / out["TeamMP"]) * 100,
        np.nan,
    )
    out["TitolaritaPct_FB"] = out["TitolaritaPct_FB"].clip(0, 100)

    return out.reset_index(drop=True)


def merge_fbref_starts(dataframe, fb):
    """
    Matching prudente:
    1. nome normalizzato esatto;
    2. cognome + squadra, solo se la combinazione identifica un solo giocatore.
    """
    out = dataframe.copy()

    for c in ["Starts", "TitolaritaPct"]:
        if c in out.columns:
            out = out.drop(columns=[c])

    out["_key_match"] = out["Nome"].map(key_name)
    out["_surname_match"] = out["Nome"].map(surname_key)
    out["_team_match"] = out["Squadra"].map(normalize_team_name)

    if fb is None or fb.empty:
        out["Starts"] = np.nan
        out["TitolaritaPct"] = np.nan
        return out.drop(
            columns=["_key_match", "_surname_match", "_team_match"],
            errors="ignore",
        )

    # 1) exact-name matching
    exact = fb.drop_duplicates("_key_fb").set_index("_key_fb")
    out["Starts"] = out["_key_match"].map(exact["Starts"])
    out["TitolaritaPct"] = out["_key_match"].map(exact["TitolaritaPct_FB"])

    # 2) cognome+squadra solo per combinazioni univoche
    fb_pair = fb.copy()
    counts = (
        fb_pair.groupby(["_surname", "_team_fb"])
        .size()
        .rename("_n")
        .reset_index()
    )
    unique_pairs = counts[counts["_n"] == 1][["_surname", "_team_fb"]]
    fb_unique = fb_pair.merge(
        unique_pairs,
        on=["_surname", "_team_fb"],
        how="inner",
    )
    pair_lookup = {
        (r["_surname"], r["_team_fb"]): (r["Starts"], r["TitolaritaPct_FB"])
        for _, r in fb_unique.iterrows()
    }

    missing = out["Starts"].isna()
    for idx in out.index[missing]:
        key = (out.at[idx, "_surname_match"], out.at[idx, "_team_match"])
        if key in pair_lookup:
            starts, pct = pair_lookup[key]
            out.at[idx, "Starts"] = starts
            out.at[idx, "TitolaritaPct"] = pct

    return out.drop(
        columns=["_key_match", "_surname_match", "_team_match"],
        errors="ignore",
    )


@st.cache_data(ttl=45, show_spinner=False)
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

    # Titolarità reale da FBref, se disponibile; altrimenti proxy PV.
    if "TitolaritaPct" in out.columns:
        tit_real = pd.to_numeric(out["TitolaritaPct"], errors="coerce")
    else:
        tit_real = pd.Series(np.nan, index=out.index)

    pv_proxy = np.clip(pv / max_pv * 100, 0, 100)
    out["TitolaritaProxy"] = tit_real.combine_first(pv_proxy).clip(0, 100)

    out["FormaScore"] = np.clip((fm - 5.5) / 3.0 * 10, 0, 10)
    out["BonusIndex"] = np.clip(bonus / max_bonus * 10, 0, 10)

    out["RendimentoScore"] = (
        out["FormaScore"] * 0.40
        + out["BonusIndex"] * 0.35
        + (out["TitolaritaProxy"] / 10) * 0.25
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
    quotes = None
    fb_starts = None

    try:
        listone = fetch_gazzetta_listone()
        status["Gazzetta listone"] = f"OK ({len(listone)})"
    except Exception as e:
        status["Gazzetta listone"] = f"KO: {e}"

    try:
        quotes = fetch_fantacalcio_quotes()
        status["Fantacalcio quotazioni/FVM"] = f"OK ({len(quotes)})"
    except Exception as e:
        status["Fantacalcio quotazioni/FVM"] = f"KO: {e}"

    try:
        stats = fetch_fantacalcio_stats()
        status["Fantacalcio statistiche"] = f"OK ({len(stats)})"
    except Exception as e:
        status["Fantacalcio statistiche"] = f"KO: {e}"

    try:
        fb_starts = fetch_fbref_starts()
        status["FBref titolarità"] = f"OK ({len(fb_starts)})"
    except Exception as e:
        status["FBref titolarità"] = f"KO: {e}"

    if listone is None or listone.empty:
        raise RuntimeError(
            "Non sono riuscito a costruire automaticamente il listone con i ruoli. "
            "Carica il listone ufficiale Classic: l'app lo aggiornerà poi "
            "automaticamente con QA, FVM e statistiche."
        )

    listone = merge_live_quotes(listone, quotes)
    data = merge_listone_stats(listone, stats)
    data = merge_fbref_starts(data, fb_starts)
    data = compute_scores(data)

    return data, stats, status


@st.cache_data(ttl=60, show_spinner=False)
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
# CONSIGLI ACQUISTI: SLOT 1-8, JOLLY, SCOMMESSE
# ------------------------------------------------------------

def minmax_0_10(series):
    s = pd.to_numeric(series, errors="coerce")
    valid = s.dropna()
    if valid.empty:
        return pd.Series(5.0, index=series.index)
    lo, hi = float(valid.min()), float(valid.max())
    if hi <= lo:
        return pd.Series(5.0, index=series.index)
    return ((s.fillna(lo) - lo) / (hi - lo) * 10).clip(0, 10)


def build_buying_advice(available_df):
    """
    Costruisce fasce di acquisto dinamiche per ruolo.
    Slot 1 = prima fascia del ruolo, Slot 8 = fascia più economica/profonda.
    Jolly e Scommesse sono segnali calcolati dall'app, non etichette editoriali
    copiate dalle testate.
    """
    if available_df is None or available_df.empty:
        return pd.DataFrame()

    chunks = []

    for role in "PDCA":
        g = available_df[available_df["Ruolo"] == role].copy()
        if g.empty:
            continue

        g["QA_num"] = pd.to_numeric(g["Quotazione"], errors="coerce")
        if "FVM" not in g.columns:
            g["FVM"] = np.nan
        g["FVM_num"] = pd.to_numeric(g["FVM"], errors="coerce")

        g["QAIndex"] = minmax_0_10(g["QA_num"])
        g["FVMIndex"] = minmax_0_10(g["FVM_num"])

        rendimento = pd.to_numeric(
            g.get("RendimentoScore", pd.Series(5, index=g.index)),
            errors="coerce",
        ).fillna(5).clip(0, 10)

        tit = (
            pd.to_numeric(
                g.get("TitolaritaProxy", pd.Series(50, index=g.index)),
                errors="coerce",
            ).fillna(50).clip(0, 100) / 10
        )

        need = squad_need_score(role)

        # FVM e quotazione definiscono il valore di mercato;
        # dati partita/titolarità possono spostare la gerarchia.
        g["IndiceAcquisto"] = (
            g["FVMIndex"] * 0.32
            + g["QAIndex"] * 0.23
            + rendimento * 0.28
            + tit * 0.12
            + need * 0.05
        ).clip(0, 10)

        g = g.sort_values(
            ["IndiceAcquisto", "FVM_num", "QA_num"],
            ascending=False,
        ).reset_index(drop=True)

        # 8 fasce per ruolo, basate sulla posizione relativa.
        n = len(g)
        g["Slot"] = [
            min(8, int((i * 8) / max(n, 1)) + 1)
            for i in range(n)
        ]
        g["Fascia"] = g["Slot"].map(lambda x: f"Slot {x}")

        # Valore rispetto al prezzo: utile per trovare giocatori meno costosi
        # che stanno rendendo sopra il prezzo/listone.
        qa_denom = g["QAIndex"].replace(0, 0.5)
        g["ValueGap"] = rendimento - g["QAIndex"]

        # Jolly: fascia media ma rendimento/valore sopra la quotazione.
        g["Jolly"] = (
            g["Slot"].between(3, 6)
            & (rendimento >= 6.0)
            & (g["ValueGap"] >= 1.0)
        )

        # Scommessa: prezzo basso / slot profondo con segnali positivi.
        pv = pd.to_numeric(
            g.get("PV", pd.Series(0, index=g.index)),
            errors="coerce",
        ).fillna(0)

        fm = pd.to_numeric(
            g.get("FM", pd.Series(np.nan, index=g.index)),
            errors="coerce",
        )

        g["Scommessa"] = (
            (g["Slot"] >= 6)
            & (g["QAIndex"] <= 4.5)
            & (
                (rendimento >= 5.2)
                | (fm >= 6.5)
                | ((pv <= 3) & (g["FVMIndex"] >= 4.5))
            )
        )

        g["PrioritaRosa"] = need
        chunks.append(g)

    if not chunks:
        return pd.DataFrame()

    return pd.concat(chunks, ignore_index=True)


# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------

live_text = (
    st.session_state.get("last_update")
    or "sincronizzazione iniziale"
)

st.markdown(
    f"""
    <div class="app-hero">
      <div class="hero-row">
        <div>
          <div class="micro-label" style="color:#94a3b8;">FANTACALCIO · ASTA</div>
          <div class="hero-title">FantAsta Assistant</div>
          <div class="hero-sub">Rosa, budget e decisioni d'acquisto in un'unica dashboard.</div>
        </div>
        <div class="live-badge">
          <span class="live-dot"></span>
          Fantacalcio LIVE · {live_text}
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### FANTA ASTA")
    st.caption("Assistant Pro · V6")

    st.markdown("#### Sincronizzazione")
    st.session_state["live_sync"] = st.toggle(
        "Aggiornamento automatico",
        value=bool(st.session_state.get("live_sync", True)),
        help="Ricarica quotazioni e statistiche Fantacalcio circa ogni 60 secondi.",
    )

    if st.session_state["live_sync"]:
        st.components.v1.html(
            """
            <script>
            setTimeout(function() {
                window.parent.location.reload();
            }, 60000);
            </script>
            """,
            height=0,
        )
        st.caption("● LIVE · refresh ~60 sec")
    else:
        st.caption("○ Aggiornamento automatico disattivato")

    if st.button("↻ Aggiorna ora", use_container_width=True):
        st.cache_data.clear()
        st.session_state["last_sync_epoch"] = 0
        st.rerun()

    st.divider()
    st.markdown("#### Impostazioni lega")

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
        "Sincronizza listone online",
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

                # Aggiorna sempre quotazione attuale e FVM da Fantacalcio,
                # mantenendo i ruoli del file ufficiale caricato.
                try:
                    live_quotes = fetch_fantacalcio_quotes()
                    parsed = merge_live_quotes(parsed, live_quotes)
                    st.session_state["source_status"][
                        "Fantacalcio quotazioni/FVM"
                    ] = f"OK ({len(live_quotes)})"
                except Exception as e:
                    st.session_state["source_status"][
                        "Fantacalcio quotazioni/FVM"
                    ] = f"KO: {e}"

                data = merge_listone_stats(parsed, stats)

                try:
                    fb_starts = fetch_fbref_starts()
                    data = merge_fbref_starts(data, fb_starts)
                    data = compute_scores(data)
                    st.session_state["source_status"][
                        "FBref titolarità"
                    ] = f"OK ({len(fb_starts)})"
                except Exception as e:
                    st.session_state["source_status"][
                        "FBref titolarità"
                    ] = f"KO: {e}"

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
                ["Nome", "Ruolo", "Squadra", "Quotazione", "FVM"]
                if c in current.columns
            ]
            st.dataframe(
                current[preview_cols].head(8),
                hide_index=True,
                use_container_width=True,
            )
    else:
        st.warning("Nessun listone attivo.")



def refresh_current_dataset():
    """
    Aggiorna ogni minuto QA/FVM/statistiche Fantacalcio.
    Se il listone è online ricostruisce anche ruoli/squadre dalla fonte base.
    Se il listone è stato caricato dall'utente conserva i ruoli del file.
    """
    now = int(time.time())
    if now - int(st.session_state.get("last_sync_epoch", 0)) < 50:
        return

    try:
        if st.session_state.get("listone_source") == "Online":
            data, stats, status = load_online_data()
        else:
            current = st.session_state.get("giocatori")
            if current is None or current.empty:
                return

            base = current.copy()

            # Elimina i campi live esistenti prima del nuovo merge.
            live_cols = [
                "QI_FC", "QA_FC", "FVM", "Squadra_FC",
                "PV", "MV", "FM", "Gol", "Assist", "Amm", "Esp",
                "BonusScore", "TitolaritaProxy", "FormaScore",
                "BonusIndex", "RendimentoScore",
            ]
            base = base.drop(columns=[c for c in live_cols if c in base.columns])

            quotes = fetch_fantacalcio_quotes()
            stats = fetch_fantacalcio_stats()
            fb_starts = fetch_fbref_starts()
            base = merge_live_quotes(base, quotes)
            data = merge_listone_stats(base, stats)
            data = merge_fbref_starts(data, fb_starts)
            data = compute_scores(data)
            status = {
                "Fantacalcio quotazioni/FVM": f"OK ({len(quotes)})",
                "Fantacalcio statistiche": f"OK ({len(stats)})",
                "FBref titolarità": f"OK ({len(fb_starts)})",
            }

        st.session_state["giocatori"] = data
        st.session_state["online_stats"] = stats
        st.session_state["source_status"].update(status)
        st.session_state["last_update"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        st.session_state["last_sync_epoch"] = now

    except Exception as e:
        st.session_state["source_status"]["Sincronizzazione LIVE"] = f"KO: {e}"


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
                "Nome", "Ruolo", "Squadra", "Quotazione", "FVM",
                *STAT_COLS,
            ]
        )


if st.session_state.get("live_sync", True):
    refresh_current_dataset()

df = st.session_state["giocatori"].copy()

for c in ["Nome", "Ruolo", "Squadra", "Quotazione", "FVM", *STAT_COLS]:
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

budget_pct = (
    (b_left / st.session_state["budget_iniziale"]) * 100
    if st.session_state["budget_iniziale"] else 0
)

c1.metric(
    "Budget disponibile",
    f"{b_left} FM",
    f"{budget_pct:.0f}% residuo",
)
c2.metric(
    "Spesa effettuata",
    f"{st.session_state['speso']} FM",
)
c3.metric(
    "Rosa",
    f"{len(st.session_state['rosa'])}/{sum(st.session_state['slot'].values())}",
)
c4.metric(
    "Slot da completare",
    f"{slots_left}",
)

if not df.empty:
    fc_q = st.session_state["source_status"].get("Fantacalcio quotazioni/FVM", "—")
    fc_s = st.session_state["source_status"].get("Fantacalcio statistiche", "—")
    fb_s = st.session_state["source_status"].get("FBref titolarità", "—")
    st.markdown(
        f"""
        <div class="source-strip">
          <span class="source-pill"><strong>{len(df)}</strong> giocatori</span>
          <span class="source-pill">Listone: <strong>{st.session_state['listone_source']}</strong></span>
          <span class="source-pill">QA/FVM: <strong>{fc_q}</strong></span>
          <span class="source-pill">Stats: <strong>{fc_s}</strong></span>
          <span class="source-pill">Titolarità: <strong>{fb_s}</strong></span>
          <span class="source-pill">Sync: <strong>{st.session_state['last_update'] or '—'}</strong></span>
        </div>
        """,
        unsafe_allow_html=True,
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

tab_rosa, tab_asta, tab_consigli, tab_giocatori, tab_news = st.tabs([
    "La mia rosa",
    "Asta live",
    "Consigli",
    "Giocatori",
    "News",
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

            if result in {"AFFARE", "OTTIMO"}:
                klass = "good"
                detail = (
                    "Prezzo interessante per la tua situazione attuale."
                    if result == "OTTIMO"
                    else "Sei nettamente sotto il tetto calcolato."
                )
            elif result == "OK":
                klass = "ok"
                detail = "Sei vicino al limite: puoi chiudere, ma senza inseguire."
            else:
                klass = "bad"
                detail = (
                    "Stai pagando oltre il valore consigliato."
                    if result == "CARO"
                    else "Per budget e composizione rosa conviene fermarsi."
                )

            st.markdown(
                f"""
                <div class="decision {klass}">
                    {result} · {current_bid} FM
                    <div style="font-weight:500; font-size:13px; margin-top:4px;">
                        {detail}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            def fmt(value, digits=1):
                if pd.isna(value):
                    return "n.d."
                return f"{float(value):.{digits}f}"

            data_c1, data_c2, data_c3, data_c4 = st.columns(4)
            data_c1.metric("Presenze", fmt(row["PV"], 0))
            data_c2.metric(
                "Titolarità",
                (
                    f"{float(row['TitolaritaPct']):.0f}%"
                    if pd.notna(row.get("TitolaritaPct"))
                    else "n.d."
                ),
            )
            data_c3.metric("Gol", fmt(row["Gol"], 0))
            data_c4.metric("Assist", fmt(row["Assist"], 0))

            data_c5, data_c6, data_c7, data_c8 = st.columns(4)
            data_c5.metric("Media voto", fmt(row["MV"], 2))
            data_c6.metric("Fantamedia", fmt(row["FM"], 2))
            data_c7.metric(
                "QA",
                fmt(row["Quotazione"], 0),
            )
            data_c8.metric(
                "FVM",
                fmt(row.get("FVM"), 0),
            )

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
# TAB CONSIGLI ACQUISTI
# ------------------------------------------------------------

with tab_consigli:
    st.subheader("⭐ Consigli acquisti: Slot 1–8, Jolly e Scommesse")

    st.caption(
        "Le fasce sono calcolate usando quotazione attuale e FVM Fantacalcio, "
        "rendimento, bonus/titolarità disponibili e la necessità della tua rosa. "
        "Slot 1 è la prima fascia; Slot 8 è la fascia più profonda."
    )

    advice = build_buying_advice(df_disponibili)

    if advice.empty:
        st.info("Carica prima un listone con ruoli validi.")
    else:
        role_choice = st.radio(
            "Ruolo",
            ["P", "D", "C", "A"],
            horizontal=True,
            key="advice_role",
        )

        category_choice = st.selectbox(
            "Visualizza",
            [
                "Tutti gli slot",
                "Slot 1",
                "Slot 2",
                "Slot 3",
                "Slot 4",
                "Slot 5",
                "Slot 6",
                "Slot 7",
                "Slot 8",
                "Jolly",
                "Scommesse",
            ],
            key="advice_category",
        )

        view = advice[advice["Ruolo"] == role_choice].copy()

        if category_choice.startswith("Slot "):
            num_slot = int(category_choice.split()[-1])
            view = view[view["Slot"] == num_slot]
        elif category_choice == "Jolly":
            view = view[view["Jolly"]]
        elif category_choice == "Scommesse":
            view = view[view["Scommessa"]]

        view = view.sort_values(
            ["IndiceAcquisto", "FVM_num", "QA_num"],
            ascending=False,
        )

        # Quanti slot ti mancano proprio in questo reparto
        need_txt = (
            f"Ti mancano {slot_liberi(role_choice)} giocatori "
            f"su {st.session_state['slot'][role_choice]} in questo reparto. "
            f"Priorità rosa: {squad_need_score(role_choice):.1f}/10."
        )
        st.info(need_txt)

        if view.empty:
            st.info("Nessun giocatore rientra in questa categoria al momento.")
        else:
            cols = [
                "Nome", "Squadra", "Fascia", "Quotazione", "FVM",
                "PV", "Starts", "TitolaritaPct", "MV", "FM", "Gol", "Assist",
                "IndiceAcquisto", "Jolly", "Scommessa",
            ]
            cols = [c for c in cols if c in view.columns]

            st.dataframe(
                view[cols].head(40),
                hide_index=True,
                use_container_width=True,
            )

            st.markdown("**I migliori profili della fascia selezionata**")
            for _, r in view.head(8).iterrows():
                prezzo = recommended_price(r, df_disponibili)
                tags = []
                if bool(r.get("Jolly", False)):
                    tags.append("Jolly")
                if bool(r.get("Scommessa", False)):
                    tags.append("Scommessa")
                tag_txt = f" · {' / '.join(tags)}" if tags else ""

                st.write(
                    f"**{r['Nome']}** ({r.get('Squadra','')}) — "
                    f"{r['Fascia']}{tag_txt} · "
                    f"QA {int(r['Quotazione']) if pd.notna(r['Quotazione']) else 'n.d.'} · "
                    f"FVM {int(r['FVM']) if pd.notna(r.get('FVM')) else 'n.d.'} · "
                    f"tetto per la tua rosa ≈ **{prezzo} FM**"
                )


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
            "Nome", "Ruolo", "Squadra", "Quotazione", "FVM",
            "PV", "Starts", "TitolaritaPct", "MV", "FM", "Gol", "Assist",
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
