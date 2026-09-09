
import math
import re
import urllib.parse
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(page_title="FantAsta Assistant Pro V2", page_icon="⚡", layout="wide")

SEASON = "2026-27"
FANTACALCIO_STATS_URL = f"https://www.fantacalcio.it/statistiche-serie-a/{SEASON}/fantacalcio/riepilogo"
GAZZETTA_LIST_URL = f"https://www.gazzetta.it/calcio/fantanews/lista-giocatori-fantacalcio-serie-a-{SEASON}/"
SOS_SEARCH_URL = "https://www.sosfanta.com/?s={query}"
FANTACALCIO_SEARCH_URL = "https://www.fantacalcio.it/cerca?q={query}"
GAZZETTA_SEARCH_URL = "https://www.gazzetta.it/ricerca/?q={query}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
}

DEFAULT_SLOTS = {"P": 3, "D": 8, "C": 8, "A": 6}
DEFAULT_PERC = {"P": 0.08, "D": 0.12, "C": 0.25, "A": 0.55}

st.markdown("""
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 3rem;}
div[data-testid="stMetric"] {border:1px solid rgba(128,128,128,.20); padding:12px; border-radius:12px;}
.small-note {opacity:.72; font-size:.9rem}
</style>
""", unsafe_allow_html=True)

def init_state():
    defaults = {
        "budget_iniziale": 500,
        "num_partecipanti": 10,
        "slot": DEFAULT_SLOTS.copy(),
        "perc_reparto": DEFAULT_PERC.copy(),
        "rosa": [],
        "speso": 0,
        "giocatori": None,
        "source_status": {},
        "last_update": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

def clean_name(s):
    return re.sub(r"\s+", " ", str(s).strip())

def key_name(s):
    s = str(s).lower().strip()
    s = re.sub(r"[^a-z0-9àèéìòù' ]", " ", s)
    return re.sub(r"\s+", " ", s)

def to_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
        .str.replace(r"[^\d\.-]", "", regex=True),
        errors="coerce",
    )

def flatten_columns(df):
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [" ".join(str(x) for x in tup if str(x) != "nan").strip() for tup in out.columns]
    else:
        out.columns = [str(c).strip() for c in out.columns]
    return out

def pick_col(df, candidates):
    low = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in low:
            return low[cand.lower()]
    for cand in candidates:
        for k, original in low.items():
            if cand.lower() in k:
                return original
    return None

def normalize_role(x):
    s = str(x).strip().upper()
    return s[0] if s and s[0] in "PDCA" else None

@st.cache_data(ttl=1800, show_spinner=False)
def read_html_tables(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return pd.read_html(r.text)

def parse_fantacalcio_stats():
    tables = read_html_tables(FANTACALCIO_STATS_URL)
    best, best_score = None, -1
    for raw in tables:
        df = flatten_columns(raw)
        text = " ".join(df.columns).lower()
        score = sum(k in text for k in ["pv", "mv", "fm", "gol", "ass"])
        if len(df) > 20 and score > best_score:
            best, best_score = df, score
    if best is None:
        raise ValueError("tabella statistiche non trovata")

    df = best
    c_nome = pick_col(df, ["calciatore", "giocatore", "nome"])
    if c_nome is None:
        # Fantacalcio spesso mette il nome in una colonna senza intestazione
        candidates = [c for c in df.columns if df[c].dtype == object]
        c_nome = max(candidates, key=lambda c: df[c].astype(str).str.len().mean()) if candidates else None
    if c_nome is None:
        raise ValueError("colonna nome non riconosciuta")

    cols = {
        "Squadra_FC": pick_col(df, ["sq", "squadra"]),
        "PV": pick_col(df, ["pv"]),
        "MV": pick_col(df, ["mv"]),
        "FM": pick_col(df, ["fm"]),
        "Gol": pick_col(df, ["gol"]),
        "Assist": pick_col(df, ["ass"]),
        "Amm": pick_col(df, ["amm"]),
        "Esp": pick_col(df, ["esp"]),
    }
    out = pd.DataFrame({"Nome": df[c_nome].map(clean_name)})
    for name, col in cols.items():
        if col is None:
            out[name] = "" if name == "Squadra_FC" else np.nan
        elif name == "Squadra_FC":
            out[name] = df[col].astype(str).str.strip()
        else:
            out[name] = to_num(df[col])
    out = out[out["Nome"].str.len() > 1].drop_duplicates("Nome")
    out["_key"] = out["Nome"].map(key_name)
    return out

def parse_gazzetta():
    tables = read_html_tables(GAZZETTA_LIST_URL)
    best, best_score = None, -1
    for raw in tables:
        df = flatten_columns(raw)
        text = " ".join(df.columns).lower()
        score = sum(k in text for k in ["giocatore", "ruolo", "quot"])
        if len(df) > 20 and score > best_score:
            best, best_score = df, score
    if best is None:
        raise ValueError("tabella listone non trovata")

    df = best
    c_nome = pick_col(df, ["giocatore", "nome"])
    c_ruolo = pick_col(df, ["ruolo"])
    c_sq = pick_col(df, ["sqd", "squadra"])
    c_q = pick_col(df, ["quotazioni", "quotazione"])
    if c_nome is None:
        raise ValueError("colonna giocatore non riconosciuta")

    out = pd.DataFrame({
        "Nome": df[c_nome].map(clean_name),
        "Ruolo": df[c_ruolo].map(normalize_role) if c_ruolo is not None else None,
        "Squadra": df[c_sq].astype(str).str.strip() if c_sq is not None else "",
        "Quotazione": to_num(df[c_q]) if c_q is not None else np.nan,
    })
    # Se la tabella espone anche dati di rendimento li importiamo
    extra_map = {
        "PG_GAZ": ["pg", "partite giocate"],
        "Gol_GAZ": ["g", "gol"],
        "Assist_GAZ": ["a", "assist"],
        "MV_GAZ": ["mv"],
        "MM_GAZ": ["mm", "media magic"],
        "MP_GAZ": ["mp", "magic punti"],
    }
    for new_col, aliases in extra_map.items():
        c = pick_col(df, aliases)
        out[new_col] = to_num(df[c]) if c is not None else np.nan

    out = out[out["Nome"].str.len() > 1].drop_duplicates("Nome")
    out["_key"] = out["Nome"].map(key_name)
    return out

@st.cache_data(ttl=900, show_spinner=False)
def fetch_sos_news(player_name, max_items=6):
    q = urllib.parse.quote(player_name)
    url = SOS_SEARCH_URL.format(query=q)
    items = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        seen = set()
        surname = player_name.split()[-1].lower()
        for a in soup.find_all("a", href=True):
            title = " ".join(a.get_text(" ", strip=True).split())
            href = a.get("href", "")
            if len(title) >= 22 and surname in title.lower() and href.startswith("http") and href not in seen:
                seen.add(href)
                items.append({"Fonte": "SOS Fanta", "Titolo": title[:180], "Link": href})
                if len(items) >= max_items:
                    break
    except Exception:
        pass
    return items

def news_signal(items):
    text = " ".join(i["Titolo"].lower() for i in items)
    pos = ["titolare", "recuper", "rientra", "convoc", "rigor", "bonus", "gol", "assist", "ok"]
    neg = ["infortun", "stop", "out", "panchina", "dubbio", "problema", "salta", "rischio"]
    return float(np.clip(sum(text.count(x) for x in pos) - sum(text.count(x) for x in neg), -4, 4))

def build_dataset():
    status = {}
    fc = gaz = None
    try:
        fc = parse_fantacalcio_stats()
        status["Fantacalcio"] = "OK"
    except Exception as e:
        status["Fantacalcio"] = f"KO - {e}"
    try:
        gaz = parse_gazzetta()
        status["Gazzetta"] = "OK"
    except Exception as e:
        status["Gazzetta"] = f"KO - {e}"

    if gaz is None or gaz.empty:
        if fc is None or fc.empty:
            raise RuntimeError("Nessuna fonte online disponibile. Usa il caricamento manuale del listone.")
        base = fc.copy()
        base["Ruolo"] = None
        base["Squadra"] = base["Squadra_FC"]
        base["Quotazione"] = np.nan
    else:
        base = gaz.copy()
        if fc is not None and not fc.empty:
            keep = ["_key", "PV", "MV", "FM", "Gol", "Assist", "Amm", "Esp"]
            base = base.merge(fc[keep], on="_key", how="left")
        else:
            base["PV"] = base.get("PG_GAZ", np.nan)
            base["MV"] = base.get("MV_GAZ", np.nan)
            base["FM"] = base.get("MM_GAZ", np.nan)
            base["Gol"] = base.get("Gol_GAZ", np.nan)
            base["Assist"] = base.get("Assist_GAZ", np.nan)
            base["Amm"] = np.nan
            base["Esp"] = np.nan

    for c in ["PV", "MV", "FM", "Gol", "Assist", "Amm", "Esp", "Quotazione"]:
        if c not in base:
            base[c] = np.nan

    # Indicatori numerici: rendimento, bonus e continuità.
    pv = base["PV"].fillna(0).clip(lower=0)
    mv = base["MV"].fillna(6.0)
    fm = base["FM"].fillna(mv)
    bonus = base["Gol"].fillna(0) * 3 + base["Assist"].fillna(0)
    base["BonusScore"] = bonus
    base["TitolaritaProxy"] = np.clip(pv / max(float(pv.max()), 1.0) * 100, 0, 100)
    base["FormaScore"] = np.clip((fm - 5.5) / 4.0 * 10, 0, 10)
    base["BonusIndex"] = np.clip(bonus / max(float(bonus.max()), 1.0) * 10, 0, 10)
    base["RendimentoScore"] = (
        base["FormaScore"] * 0.45
        + base["BonusIndex"] * 0.35
        + (base["TitolaritaProxy"] / 10) * 0.20
    )
    return base.reset_index(drop=True), status

def normalize_uploaded(df):
    aliases = {
        "nome": "Nome", "calciatore": "Nome", "giocatore": "Nome",
        "ruolo": "Ruolo", "r": "Ruolo", "rm": "Ruolo",
        "squadra": "Squadra", "sq": "Squadra",
        "quotazione": "Quotazione", "qt.a": "Quotazione", "qta": "Quotazione", "fvm": "Quotazione",
    }
    ren = {}
    for c in df.columns:
        k = str(c).strip().lower()
        if k in aliases:
            ren[c] = aliases[k]
    df = df.rename(columns=ren)
    needed = {"Nome", "Ruolo", "Squadra"}
    if not needed.issubset(df.columns):
        raise ValueError("Servono almeno le colonne Nome, Ruolo e Squadra.")
    if "Quotazione" not in df.columns:
        df["Quotazione"] = np.nan
    df["Nome"] = df["Nome"].map(clean_name)
    df["Ruolo"] = df["Ruolo"].map(normalize_role)
    df["_key"] = df["Nome"].map(key_name)
    return df

def merge_uploaded_with_online(uploaded, online):
    keep_online = ["_key","PV","MV","FM","Gol","Assist","Amm","Esp","BonusScore","TitolaritaProxy","FormaScore","BonusIndex","RendimentoScore"]
    out = uploaded.merge(online[[c for c in keep_online if c in online.columns]], on="_key", how="left")
    for c in ["PV","MV","FM","Gol","Assist","Amm","Esp","BonusScore","TitolaritaProxy","FormaScore","BonusIndex","RendimentoScore"]:
        if c not in out:
            out[c] = np.nan
    return out

def slot_occupati(role):
    return sum(1 for x in st.session_state["rosa"] if x["Ruolo"] == role)

def slot_liberi(role):
    return max(int(st.session_state["slot"][role]) - slot_occupati(role), 0)

def speso_reparto(role):
    return sum(float(x["Prezzo"]) for x in st.session_state["rosa"] if x["Ruolo"] == role)

def target_reparto(role):
    return st.session_state["budget_iniziale"] * st.session_state["perc_reparto"][role]

def budget_rimasto():
    return st.session_state["budget_iniziale"] - st.session_state["speso"]

def crediti_minimi_da_salvare():
    # almeno 1 FM per ogni slot ancora vuoto
    return sum(slot_liberi(r) for r in "PDCA")

def reserve_for_other_roles(current_role):
    b = budget_rimasto()
    reserve = 0
    for r in "PDCA":
        if r == current_role or slot_liberi(r) == 0:
            continue
        gap = max(target_reparto(r) - speso_reparto(r), slot_liberi(r))
        reserve += min(gap, b)
    reserve = min(reserve, max(b - slot_liberi(current_role), 0))
    return reserve

def max_theoretical_bid(role):
    return max(int(budget_rimasto() - (crediti_minimi_da_salvare() - 1)), 1)

def squad_need_score(role):
    if slot_liberi(role) <= 0:
        return 0.0
    free_ratio = slot_liberi(role) / max(st.session_state["slot"][role], 1)
    target_gap = max(target_reparto(role) - speso_reparto(role), 0) / max(target_reparto(role), 1)
    return float(np.clip((free_ratio * 0.55 + target_gap * 0.45) * 10, 0, 10))

def recommended_price(row):
    role = row["Ruolo"]
    if role not in "PDCA":
        return 1
    free = max(slot_liberi(role), 1)
    role_budget = max(budget_rimasto() - reserve_for_other_roles(role), free)
    avg = role_budget / free
    quality = float(row.get("RendimentoScore", 5) if pd.notna(row.get("RendimentoScore", np.nan)) else 5)
    quote = float(row.get("Quotazione", 1) if pd.notna(row.get("Quotazione", np.nan)) else 1)
    role_max_quote = max(float(df_disponibili[df_disponibili["Ruolo"] == role]["Quotazione"].max() or 1), 1)
    quote_factor = np.clip(quote / role_max_quote, 0.15, 1.0)
    multiplier = 0.55 + 0.55 * (quality / 10) + 0.35 * quote_factor
    price = round(avg * multiplier)
    return int(np.clip(price, 1, max_theoretical_bid(role)))

def verdict(current_price, rec):
    if current_price <= max(1, round(rec * .70)):
        return "AFFARE"
    if current_price <= round(rec * .90):
        return "OTTIMO"
    if current_price <= rec:
        return "OK"
    if current_price <= round(rec * 1.12):
        return "CARO"
    return "STOP"

st.title("⚡ FantAsta Assistant Pro V2")
st.caption("Gestione della tua rosa, budget dinamico e consigli basati su rendimento + fonti online.")

with st.sidebar:
    st.header("⚙️ Lega")
    budget = st.number_input("Budget iniziale", 100, 2000, int(st.session_state["budget_iniziale"]), 50)
    partecipanti = st.number_input("Partecipanti", 4, 20, int(st.session_state["num_partecipanti"]))
    st.subheader("Slot")
    slot_new = {
        "P": st.number_input("Portieri", 1, 5, int(st.session_state["slot"]["P"])),
        "D": st.number_input("Difensori", 1, 12, int(st.session_state["slot"]["D"])),
        "C": st.number_input("Centrocampisti", 1, 12, int(st.session_state["slot"]["C"])),
        "A": st.number_input("Attaccanti", 1, 10, int(st.session_state["slot"]["A"])),
    }
    if st.button("Salva impostazioni", use_container_width=True):
        st.session_state["budget_iniziale"] = int(budget)
        st.session_state["num_partecipanti"] = int(partecipanti)
        st.session_state["slot"] = {k:int(v) for k,v in slot_new.items()}
        st.rerun()

    st.divider()
    st.header("🌐 Dati")
    if st.button("Aggiorna fonti online", use_container_width=True):
        try:
            online, status = build_dataset()
            st.session_state["giocatori"] = online
            st.session_state["source_status"] = status
            st.session_state["last_update"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            st.success("Aggiornamento completato")
        except Exception as e:
            st.error(str(e))

    up = st.file_uploader("Listone personale (CSV/XLSX)", type=["csv","xlsx"])
    if up is not None:
        try:
            raw = pd.read_csv(up) if up.name.lower().endswith(".csv") else pd.read_excel(up)
            uploaded = normalize_uploaded(raw)
            online = st.session_state["giocatori"]
            if online is None:
                try:
                    online, status = build_dataset()
                    st.session_state["source_status"] = status
                except Exception:
                    online = pd.DataFrame({"_key":[]})
            st.session_state["giocatori"] = merge_uploaded_with_online(uploaded, online)
            st.success(f"Caricati {len(uploaded)} giocatori")
        except Exception as e:
            st.error(f"Errore listone: {e}")

if st.session_state["giocatori"] is None:
    with st.spinner("Carico Fantacalcio e Gazzetta..."):
        try:
            data, status = build_dataset()
            st.session_state["giocatori"] = data
            st.session_state["source_status"] = status
            st.session_state["last_update"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        except Exception as e:
            st.warning(f"Fonti online non disponibili: {e}. Carica il listone dalla sidebar.")
            st.session_state["giocatori"] = pd.DataFrame(columns=["Nome","Ruolo","Squadra","Quotazione"])

df = st.session_state["giocatori"].copy()
if "_key" not in df.columns and "Nome" in df.columns:
    df["_key"] = df["Nome"].map(key_name)

for col in ["PV","MV","FM","Gol","Assist","Amm","Esp","BonusScore","TitolaritaProxy","FormaScore","BonusIndex","RendimentoScore"]:
    if col not in df.columns:
        df[col] = np.nan

names_taken = {x["Nome"] for x in st.session_state["rosa"]}
df_disponibili = df[~df["Nome"].isin(names_taken)].copy() if "Nome" in df.columns else df.copy()

b_left = budget_rimasto()
slots_left = sum(slot_liberi(r) for r in "PDCA")
c1,c2,c3,c4 = st.columns(4)
c1.metric("Budget residuo", f"{b_left} FM")
c2.metric("Budget speso", f"{st.session_state['speso']} FM")
c3.metric("Slot liberi", slots_left)
c4.metric("Media FM / slot", f"{b_left/slots_left:.1f}" if slots_left else "0")

status_txt = " · ".join(f"{k}: {v}" for k,v in st.session_state["source_status"].items())
if status_txt:
    st.caption(f"Fonti: {status_txt} | ultimo aggiornamento: {st.session_state['last_update'] or '-'}")

tabs = st.tabs(["🎯 Assistente asta","📋 La mia rosa","📊 Giocatori","📰 News giocatore"])

with tabs[0]:
    st.subheader("Giocatore in asta")
    valid = df_disponibili.dropna(subset=["Nome"]).copy()
    if valid.empty:
        st.info("Nessun giocatore disponibile.")
    else:
        selected = st.selectbox("Seleziona il giocatore chiamato", valid["Nome"].tolist())
        row = valid[valid["Nome"] == selected].iloc[0]
        role = row.get("Ruolo")
        if role not in "PDCA":
            st.warning("Ruolo non disponibile dalla fonte online. Carica il listone ufficiale/personale per avere consigli di budget corretti.")
        else:
            rec = recommended_price(row)
            theoretical = max_theoretical_bid(role)
            current = st.number_input("Offerta attuale (FM)", 1, max(theoretical,1), min(max(1,rec),max(theoretical,1)))
            v = verdict(current, rec)
            need = squad_need_score(role)
            render = row.get("RendimentoScore", np.nan)
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Prezzo consigliato", f"{rec} FM")
            c2.metric("Massimo teorico", f"{theoretical} FM")
            c3.metric("Necessità reparto", f"{need:.1f}/10")
            c4.metric("Rendimento", f"{render:.1f}/10" if pd.notna(render) else "n.d.")

            if v == "AFFARE":
                st.success(f"🟢 AFFARE — a {current} FM sei nettamente sotto il prezzo obiettivo.")
            elif v == "OTTIMO":
                st.success(f"🟢 OTTIMO — a {current} FM l'acquisto è ancora molto conveniente.")
            elif v == "OK":
                st.info(f"🟡 OK — {current} FM è in linea con il massimo consigliato.")
            elif v == "CARO":
                st.warning(f"🟠 CARO — stai superando il prezzo consigliato ({rec} FM).")
            else:
                st.error(f"🔴 STOP — per la tua rosa e il budget attuale io lo lascerei andare.")

            st.write(
                f"**Dati:** PV {row.get('PV', np.nan):.0f} · MV {row.get('MV', np.nan):.2f} · "
                f"FM {row.get('FM', np.nan):.2f} · Gol {row.get('Gol', np.nan):.0f} · "
                f"Assist {row.get('Assist', np.nan):.0f}"
            )

            if st.button("➕ Aggiungi alla mia rosa", use_container_width=True):
                if slot_liberi(role) <= 0:
                    st.error(f"Reparto {role} completo.")
                elif current > b_left:
                    st.error("Budget insufficiente.")
                else:
                    st.session_state["rosa"].append({"Nome": selected, "Ruolo": role, "Prezzo": int(current)})
                    st.session_state["speso"] += int(current)
                    st.rerun()

with tabs[1]:
    st.subheader("La mia rosa")
    rows = []
    for r in "PDCA":
        rows.append({
            "Ruolo": r,
            "Slot": f"{slot_occupati(r)}/{st.session_state['slot'][r]}",
            "Speso": int(speso_reparto(r)),
            "Target teorico": round(target_reparto(r)),
            "Priorità attuale": round(squad_need_score(r),1),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if st.session_state["rosa"]:
        rosa = pd.DataFrame(st.session_state["rosa"])
        st.dataframe(rosa, use_container_width=True, hide_index=True)
        remove = st.selectbox("Rimuovi acquisto", ["—"] + rosa["Nome"].tolist())
        if remove != "—" and st.button("Rimuovi giocatore"):
            item = next(x for x in st.session_state["rosa"] if x["Nome"] == remove)
            st.session_state["rosa"].remove(item)
            st.session_state["speso"] -= item["Prezzo"]
            st.rerun()
    else:
        st.info("Rosa ancora vuota.")

    if st.button("🗑️ Reset asta"):
        st.session_state["rosa"] = []
        st.session_state["speso"] = 0
        st.rerun()

with tabs[2]:
    st.subheader("Classifica guidata giocatori")
    filt = st.selectbox("Ruolo", ["Tutti","P","D","C","A"], key="filter_table")
    view = df_disponibili.copy()
    if filt != "Tutti":
        view = view[view["Ruolo"] == filt]
    if not view.empty:
        view["NecessitàRosa"] = view["Ruolo"].map(lambda r: squad_need_score(r) if r in "PDCA" else 0)
        view["ScoreGuidato"] = view["RendimentoScore"].fillna(5)*0.75 + view["NecessitàRosa"]*0.25
        view = view.sort_values("ScoreGuidato", ascending=False)
        cols = [c for c in ["Nome","Ruolo","Squadra","Quotazione","PV","MV","FM","Gol","Assist","RendimentoScore","NecessitàRosa","ScoreGuidato"] if c in view.columns]
        st.dataframe(view[cols], use_container_width=True, hide_index=True)
    else:
        st.info("Nessun giocatore con questo filtro.")

with tabs[3]:
    st.subheader("News e contesto")
    if df.empty:
        st.info("Nessun giocatore disponibile.")
    else:
        player = st.selectbox("Giocatore", df["Nome"].tolist(), key="news_player")
        news = fetch_sos_news(player)
        signal = news_signal(news)
        st.metric("Segnale news SOS Fanta", f"{signal:+.0f}", help="Indicatore euristico basato sui titoli trovati: positivo = segnali favorevoli, negativo = rischi/dubbi.")
        if news:
            for item in news:
                st.markdown(f"- **{item['Fonte']}** — [{item['Titolo']}]({item['Link']})")
        else:
            st.info("Nessun titolo SOS Fanta trovato automaticamente.")
        q = urllib.parse.quote(player)
        st.markdown(
            f"[Fantacalcio.it]({FANTACALCIO_SEARCH_URL.format(query=q)}) · "
            f"[Gazzetta]({GAZZETTA_SEARCH_URL.format(query=q)}) · "
            f"[SOS Fanta]({SOS_SEARCH_URL.format(query=q)})"
        )

st.divider()
st.caption(
    "Nota: i dati editoriali vengono usati come segnali sintetici e link alle fonti. "
    "La struttura dei siti può cambiare; per questo l'app mantiene il caricamento manuale del listone come fallback."
)
