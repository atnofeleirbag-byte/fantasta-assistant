
import io
import re
import urllib.parse
import time
import json
import hashlib
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="FantAsta Assistant",
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

FANTACALCIO_SEASON_FORMATIONS_URL = (
    "https://www.fantacalcio.it/amp/news/calcio-italia/06_08_2026/"
    "asta-fantacalcio-le-probabili-formazioni-della-serie-a-enilive-2026-27-495558"
)
FANTACALCIO_MATCHDAY_FORMATIONS_URL = (
    "https://www.fantacalcio.it/probabili-formazioni-serie-a"
)

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
    "PV", "Starts", "TitolaritaPct", "TitolaritaProxy", "TitolaritaFonte", "MV", "FM", "Gol", "Assist",
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

# Design system V9
st.markdown(
    """
    <style>
    /* ---------- FOUNDATION ---------- */
    :root{
        --fa-bg:#f7f8fb;
        --fa-surface:#ffffff;
        --fa-surface-2:#f2f4f7;
        --fa-text:#101828;
        --fa-muted:#667085;
        --fa-line:#e4e7ec;
        --fa-brand:#101828;
        --fa-green:#12b76a;
        --fa-green-soft:#ecfdf3;
        --fa-amber:#f79009;
        --fa-amber-soft:#fffaeb;
        --fa-red:#f04438;
        --fa-red-soft:#fef3f2;
        --fa-blue:#2e90fa;
        --fa-radius:18px;
        --fa-shadow:0 8px 28px rgba(16,24,40,.055);
    }

    html { scroll-behavior:smooth; }
    .stApp { background:var(--fa-bg); }

    .block-container{
        max-width:1320px;
        padding-top:.8rem;
        padding-bottom:4rem;
    }

    /* ---------- SIDEBAR ---------- */
    section[data-testid="stSidebar"]{
        min-width:292px !important;
        max-width:292px !important;
        border-right:1px solid var(--fa-line);
        box-shadow:none;
    }
    section[data-testid="stSidebar"] > div{
        background:#fff;
    }
    section[data-testid="stSidebar"] .stButton > button{
        width:100%;
    }

    /* ---------- HERO ---------- */
    .app-hero{
        background:
            radial-gradient(circle at 88% 20%, rgba(255,255,255,.10), transparent 24%),
            linear-gradient(135deg,#101828 0%,#1d2939 100%);
        border:1px solid rgba(255,255,255,.06);
        border-radius:24px;
        padding:26px 28px;
        box-shadow:0 14px 38px rgba(16,24,40,.12);
        margin-bottom:14px;
    }
    .hero-title{
        font-size:31px;
        line-height:1.08;
        letter-spacing:-.045em;
        font-weight:800;
    }
    .hero-sub{
        font-size:14px;
        max-width:650px;
        color:#d0d5dd;
        line-height:1.55;
    }
    .live-badge{
        background:rgba(255,255,255,.07);
        border:1px solid rgba(255,255,255,.13);
        backdrop-filter:blur(8px);
    }

    /* ---------- KPI ---------- */
    div[data-testid="stMetric"]{
        background:var(--fa-surface);
        border:1px solid var(--fa-line);
        border-radius:18px;
        box-shadow:none;
        padding:15px 17px 14px;
    }
    div[data-testid="stMetric"]:hover{
        border-color:#d0d5dd;
        box-shadow:var(--fa-shadow);
        transition:.18s ease;
    }
    div[data-testid="stMetricLabel"] p{
        font-size:12px;
        font-weight:650;
        color:var(--fa-muted);
    }
    div[data-testid="stMetricValue"]{
        font-weight:790;
        color:var(--fa-text);
    }
    div[data-testid="stMetricDelta"]{
        font-size:11px;
    }

    /* ---------- NAV ---------- */
    .stTabs [data-baseweb="tab-list"]{
        position:sticky;
        top:.4rem;
        z-index:20;
        gap:5px;
        padding:5px;
        border:1px solid var(--fa-line);
        border-radius:15px;
        background:rgba(255,255,255,.94);
        backdrop-filter:blur(12px);
        box-shadow:0 8px 24px rgba(16,24,40,.045);
        margin-bottom:16px;
        flex-wrap:nowrap;
        overflow-x:auto;
    }
    .stTabs [data-baseweb="tab"]{
        border:0;
        border-radius:10px;
        background:transparent;
        color:#475467;
        font-weight:650;
        height:39px;
        padding:0 13px;
        white-space:nowrap;
    }
    .stTabs [aria-selected="true"]{
        background:#101828 !important;
        color:#fff !important;
        border:0 !important;
        box-shadow:0 2px 8px rgba(16,24,40,.15);
    }

    /* ---------- FORMS ---------- */
    .stButton > button,
    .stFormSubmitButton > button{
        min-height:44px;
        border-radius:12px;
        font-weight:700;
        border:1px solid #d0d5dd;
        box-shadow:none;
    }
    .stButton > button[kind="primary"],
    .stFormSubmitButton > button[kind="primary"]{
        background:#101828;
        border-color:#101828;
        color:#fff;
    }
    .stButton > button[kind="primary"]:hover,
    .stFormSubmitButton > button[kind="primary"]:hover{
        background:#1d2939;
        border-color:#1d2939;
    }

    .stTextInput input,
    .stNumberInput input,
    div[data-baseweb="select"] > div{
        min-height:44px;
        border-radius:12px !important;
        border-color:#d0d5dd !important;
        background:#fff !important;
    }
    .stTextInput input:focus,
    .stNumberInput input:focus{
        border-color:#98a2b3 !important;
        box-shadow:0 0 0 3px rgba(152,162,179,.12) !important;
    }

    /* ---------- TABLE ---------- */
    div[data-testid="stDataFrame"]{
        border:1px solid var(--fa-line);
        border-radius:16px;
        overflow:hidden;
        box-shadow:none;
        background:#fff;
    }

    /* ---------- PRODUCT CARDS ---------- */
    .fa-grid{
        display:grid;
        grid-template-columns:repeat(4,minmax(0,1fr));
        gap:10px;
        margin:10px 0 17px;
    }
    .fa-role-card{
        background:#fff;
        border:1px solid var(--fa-line);
        border-radius:16px;
        padding:14px 15px;
        min-height:112px;
    }
    .fa-role-top{
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        margin-bottom:10px;
    }
    .fa-role-name{
        font-size:12px;
        font-weight:800;
        color:#344054;
        text-transform:uppercase;
        letter-spacing:.065em;
    }
    .fa-role-count{
        font-size:12px;
        color:#667085;
        font-weight:650;
    }
    .fa-role-value{
        font-size:22px;
        line-height:1;
        font-weight:800;
        color:#101828;
        letter-spacing:-.035em;
        margin-bottom:8px;
    }
    .fa-role-meta{
        font-size:11px;
        color:#667085;
        margin-top:7px;
    }
    .fa-progress{
        height:7px;
        border-radius:999px;
        background:#eaecf0;
        overflow:hidden;
    }
    .fa-progress > span{
        display:block;
        height:100%;
        border-radius:999px;
        background:#101828;
    }

    .fa-section-head{
        display:flex;
        justify-content:space-between;
        align-items:flex-end;
        gap:14px;
        margin:7px 0 12px;
    }
    .fa-section-title{
        font-size:21px;
        font-weight:800;
        letter-spacing:-.035em;
        color:#101828;
    }
    .fa-section-desc{
        color:#667085;
        font-size:13px;
        line-height:1.45;
        max-width:720px;
        margin-top:3px;
    }

    .fa-player-card{
        background:#fff;
        border:1px solid var(--fa-line);
        border-radius:20px;
        padding:19px 20px;
        margin:10px 0 12px;
        box-shadow:0 7px 20px rgba(16,24,40,.035);
    }
    .fa-player-head{
        display:flex;
        justify-content:space-between;
        align-items:flex-start;
        gap:16px;
    }
    .fa-player-name{
        font-size:24px;
        font-weight:820;
        color:#101828;
        letter-spacing:-.04em;
        line-height:1.08;
    }
    .fa-player-meta{
        color:#667085;
        font-size:12px;
        margin-top:5px;
    }
    .fa-price-badge{
        text-align:right;
        min-width:100px;
    }
    .fa-price-label{
        font-size:10px;
        color:#667085;
        text-transform:uppercase;
        font-weight:800;
        letter-spacing:.075em;
    }
    .fa-price-value{
        font-size:25px;
        font-weight:820;
        color:#101828;
        letter-spacing:-.04em;
    }

    .fa-mini-grid{
        display:grid;
        grid-template-columns:repeat(4,minmax(0,1fr));
        gap:8px;
        margin-top:14px;
    }
    .fa-mini{
        border:1px solid #eaecf0;
        background:#f9fafb;
        border-radius:12px;
        padding:10px 11px;
    }
    .fa-mini-label{
        font-size:10px;
        color:#667085;
        font-weight:700;
        text-transform:uppercase;
        letter-spacing:.055em;
    }
    .fa-mini-value{
        font-size:16px;
        color:#101828;
        font-weight:780;
        margin-top:2px;
    }

    .fa-note{
        background:#f9fafb;
        border:1px solid #eaecf0;
        border-radius:13px;
        padding:11px 13px;
        color:#475467;
        font-size:12px;
        line-height:1.5;
        margin:8px 0 12px;
    }

    .fa-empty{
        background:#fff;
        border:1px dashed #d0d5dd;
        border-radius:17px;
        padding:26px 20px;
        text-align:center;
        color:#667085;
    }
    .fa-empty strong{
        display:block;
        color:#344054;
        font-size:15px;
        margin-bottom:4px;
    }

    .decision{
        border-radius:14px;
        border:1px solid;
        box-shadow:none;
        padding:13px 15px;
    }
    .decision.good{background:var(--fa-green-soft);border-color:#abefc6;color:#067647;}
    .decision.ok{background:var(--fa-amber-soft);border-color:#fedf89;color:#b54708;}
    .decision.bad{background:var(--fa-red-soft);border-color:#fecdca;color:#b42318;}

    /* ---------- TEXT ---------- */
    h1,h2,h3,h4{color:#101828;}
    .stCaptionContainer{color:#667085;}

    /* ---------- MOBILE ---------- */
    @media(max-width:900px){
        .fa-grid{grid-template-columns:repeat(2,minmax(0,1fr));}
        .fa-mini-grid{grid-template-columns:repeat(2,minmax(0,1fr));}
    }
    @media(max-width:700px){
        .block-container{padding-left:.85rem;padding-right:.85rem;}
        .app-hero{padding:20px 18px;border-radius:20px;}
        .hero-title{font-size:25px;}
        .hero-row{flex-direction:column;align-items:flex-start;}
        .fa-grid{grid-template-columns:1fr 1fr;gap:8px;}
        .fa-role-card{min-height:102px;padding:12px;}
        .fa-player-head{flex-direction:column;}
        .fa-price-badge{text-align:left;}
        .stTabs [data-baseweb="tab-list"]{top:.2rem;}
        section[data-testid="stSidebar"]{
            min-width:260px !important;
            max-width:260px !important;
        }
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
# ACCOUNT + SALVATAGGIO CLOUD (Supabase REST/Auth API)
# ------------------------------------------------------------

def _secret_value(*names):
    """
    Legge una chiave dai Secrets Streamlit, rimuovendo spazi/newline accidentali.
    Supporta sia SUPABASE_KEY sia SUPABASE_PUBLISHABLE_KEY.
    """
    try:
        for name in names:
            value = st.secrets.get(name)
            if value:
                return str(value).strip().strip('"').strip("'")
    except Exception:
        pass
    return ""


def supabase_url():
    return _secret_value("SUPABASE_URL").rstrip("/")


def supabase_key():
    return _secret_value(
        "SUPABASE_PUBLISHABLE_KEY",
        "SUPABASE_KEY",
    )


def supabase_configured():
    return bool(supabase_url() and supabase_key())


def supabase_headers(access_token=None, prefer=None, include_publishable_bearer=False):
    key = supabase_key()
    headers = {
        "apikey": key,
        "Content-Type": "application/json",
    }

    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    elif include_publishable_bearer and key:
        # Comportamento compatibile con i client ufficiali Supabase:
        # prima del login la publishable key identifica il client.
        headers["Authorization"] = f"Bearer {key}"

    if prefer:
        headers["Prefer"] = prefer

    return headers


def auth_request(method, endpoint, payload=None, access_token=None):
    url = f"{supabase_url()}/auth/v1/{endpoint.lstrip('/')}"
    response = requests.request(
        method,
        url,
        headers=supabase_headers(
            access_token=access_token,
            include_publishable_bearer=(access_token is None),
        ),
        json=payload,
        timeout=20,
    )
    return response


def safe_key_diagnostics():
    key = supabase_key()
    url = supabase_url()
    return {
        "url": url,
        "key_length": len(key),
        "key_prefix": key[:18] + "…" if len(key) > 18 else key,
        "key_suffix": "…" + key[-8:] if len(key) >= 8 else key,
        "key_format_ok": key.startswith("sb_publishable_"),
        "project_ref": (
            url.replace("https://", "").split(".supabase.co")[0]
            if ".supabase.co" in url else "?"
        ),
    }


def validate_supabase_credentials():
    """
    Testa la chiave contro Supabase Auth.
    Prova prima apikey + Authorization (come i client ufficiali),
    poi solo apikey. Restituisce diagnostica non sensibile.
    """
    if not supabase_configured():
        return False, "Secrets Supabase mancanti."

    endpoint = f"{supabase_url()}/auth/v1/settings"
    key = supabase_key()

    attempts = [
        {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        {
            "apikey": key,
            "Content-Type": "application/json",
        },
    ]

    last_detail = None

    for headers in attempts:
        try:
            r = requests.get(endpoint, headers=headers, timeout=15)
            if r.ok:
                return True, None

            try:
                body = r.json() or {}
                detail = (
                    body.get("msg")
                    or body.get("message")
                    or body.get("error")
                    or r.text[:200]
                )
            except Exception:
                detail = r.text[:200]

            last_detail = f"{r.status_code}: {detail}"
        except Exception as e:
            last_detail = str(e)

    return False, last_detail or "Connessione non valida"


def set_auth_session(data):
    access = data.get("access_token")
    refresh = data.get("refresh_token")
    user = data.get("user") or {}

    if not access or not user.get("id"):
        return False

    st.session_state["auth_access_token"] = access
    st.session_state["auth_refresh_token"] = refresh
    st.session_state["auth_user_id"] = str(user["id"])
    st.session_state["auth_email"] = user.get("email") or ""
    return True


def refresh_auth_session():
    refresh = st.session_state.get("auth_refresh_token")
    if not refresh or not supabase_configured():
        return False

    try:
        r = auth_request(
            "POST",
            "token?grant_type=refresh_token",
            {"refresh_token": refresh},
        )
        if not r.ok:
            return False
        return set_auth_session(r.json())
    except Exception:
        return False


def valid_access_token():
    access = st.session_state.get("auth_access_token")
    if not access:
        return False

    try:
        r = auth_request("GET", "user", access_token=access)
        if r.ok:
            user = r.json() or {}
            if user.get("id"):
                st.session_state["auth_user_id"] = str(user["id"])
                st.session_state["auth_email"] = user.get("email") or ""
                return True

        # Token scaduto: prova refresh una volta.
        return refresh_auth_session()
    except Exception:
        return False


def compact_listone_for_save():
    source = str(st.session_state.get("listone_source", ""))
    df_state = st.session_state.get("giocatori")

    if not source.startswith("File:") or df_state is None or df_state.empty:
        return None

    cols = [
        c for c in
        ["Nome", "Ruolo", "Squadra", "Quotazione"]
        if c in df_state.columns
    ]
    if not cols:
        return None

    safe = df_state[cols].copy()
    safe = safe.where(pd.notna(safe), None)
    return safe.to_dict(orient="records")


def user_state_payload():
    return {
        "budget_iniziale": int(st.session_state.get("budget_iniziale", 500)),
        "num_partecipanti": int(st.session_state.get("num_partecipanti", 10)),
        "slot": {
            k: int(v)
            for k, v in st.session_state.get("slot", DEFAULT_SLOTS).items()
        },
        "perc_reparto": {
            k: float(v)
            for k, v in st.session_state.get("perc_reparto", DEFAULT_PERC).items()
        },
        "rosa": [
            {
                "Nome": str(x["Nome"]),
                "Ruolo": str(x["Ruolo"]),
                "Prezzo": int(x["Prezzo"]),
            }
            for x in st.session_state.get("rosa", [])
        ],
        "speso": int(st.session_state.get("speso", 0)),
        "custom_listone": compact_listone_for_save(),
        "listone_source": (
            st.session_state.get("listone_source")
            if str(st.session_state.get("listone_source", "")).startswith("File:")
            else "Online"
        ),
    }


def state_signature(payload):
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def db_request(method, query="", payload=None, prefer=None):
    access = st.session_state.get("auth_access_token")
    if not access:
        if not refresh_auth_session():
            raise RuntimeError("Sessione scaduta. Effettua nuovamente l'accesso.")
        access = st.session_state.get("auth_access_token")

    url = f"{supabase_url()}/rest/v1/user_app_state{query}"
    response = requests.request(
        method,
        url,
        headers=supabase_headers(
            access_token=access,
            prefer=prefer,
        ),
        json=payload,
        timeout=20,
    )

    # Se il JWT è scaduto, refresh e ritenta una sola volta.
    if response.status_code in (401, 403) and refresh_auth_session():
        access = st.session_state.get("auth_access_token")
        response = requests.request(
            method,
            url,
            headers=supabase_headers(
                access_token=access,
                prefer=prefer,
            ),
            json=payload,
            timeout=20,
        )

    return response


def save_user_state(force=False):
    if st.session_state.get("guest_mode"):
        return True

    user_id = st.session_state.get("auth_user_id")
    if not user_id or not valid_access_token():
        return False

    payload = user_state_payload()
    signature = state_signature(payload)

    if (
        not force
        and signature == st.session_state.get("last_saved_signature")
    ):
        return True

    try:
        record = {
            "user_id": user_id,
            "state": payload,
            "updated_at": datetime.utcnow().isoformat(),
        }
        r = db_request(
            "POST",
            "?on_conflict=user_id",
            payload=record,
            prefer="resolution=merge-duplicates,return=minimal",
        )

        if not r.ok:
            raise RuntimeError(
                f"{r.status_code}: {r.text[:300]}"
            )

        st.session_state["last_saved_signature"] = signature
        st.session_state["last_saved_at"] = datetime.now().strftime("%H:%M:%S")
        st.session_state["save_error"] = None
        return True

    except Exception as e:
        st.session_state["save_error"] = str(e)
        return False


def load_user_state():
    user_id = st.session_state.get("auth_user_id")
    if not user_id or not valid_access_token():
        return False

    try:
        r = db_request(
            "GET",
            f"?user_id=eq.{urllib.parse.quote(user_id)}&select=state&limit=1",
        )
        if not r.ok:
            raise RuntimeError(
                f"{r.status_code}: {r.text[:300]}"
            )

        rows = r.json() or []

        if not rows:
            st.session_state["cloud_state_loaded"] = True
            save_user_state(force=True)
            return True

        state = rows[0].get("state") or {}

        st.session_state["budget_iniziale"] = int(
            state.get("budget_iniziale", 500)
        )
        st.session_state["num_partecipanti"] = int(
            state.get("num_partecipanti", 10)
        )
        st.session_state["slot"] = {
            **DEFAULT_SLOTS,
            **{
                k: int(v)
                for k, v in (state.get("slot") or {}).items()
                if k in DEFAULT_SLOTS
            },
        }
        st.session_state["perc_reparto"] = {
            **DEFAULT_PERC,
            **{
                k: float(v)
                for k, v in (state.get("perc_reparto") or {}).items()
                if k in DEFAULT_PERC
            },
        }
        st.session_state["rosa"] = state.get("rosa") or []
        st.session_state["speso"] = int(
            state.get(
                "speso",
                sum(
                    int(x.get("Prezzo", 0))
                    for x in st.session_state["rosa"]
                ),
            )
        )

        saved_list = state.get("custom_listone")
        if saved_list:
            custom = pd.DataFrame(saved_list)
            if not custom.empty:
                custom = normalize_listone(custom)
                st.session_state["giocatori"] = custom
                st.session_state["listone_source"] = (
                    state.get("listone_source") or "File salvato"
                )
        else:
            st.session_state["giocatori"] = None
            st.session_state["listone_source"] = "Nessuno"

        st.session_state["last_saved_signature"] = state_signature(
            user_state_payload()
        )
        st.session_state["cloud_state_loaded"] = True
        st.session_state["save_error"] = None
        return True

    except Exception as e:
        st.session_state["save_error"] = str(e)
        return False


def logout_user():
    access = st.session_state.get("auth_access_token")
    if access:
        try:
            auth_request(
                "POST",
                "logout",
                access_token=access,
            )
        except Exception:
            pass

    for k in [
        "auth_access_token", "auth_refresh_token", "auth_user_id",
        "auth_email", "cloud_state_loaded", "last_saved_signature",
        "guest_mode",
    ]:
        st.session_state.pop(k, None)
    st.rerun()


def readable_auth_error(response):
    try:
        data = response.json() or {}
        return (
            data.get("msg")
            or data.get("message")
            or data.get("error_description")
            or data.get("error")
            or f"Errore {response.status_code}"
        )
    except Exception:
        return response.text[:300] or f"Errore {response.status_code}"


def render_setup_screen():
    st.markdown(
        """
        <div class="auth-shell">
            <div class="auth-brand">
                <div class="brand-mark">FA</div>
                <div>
                    <div class="auth-brand-name">FantAsta Assistant</div>
                    <div class="auth-brand-sub">Account e salvataggio cloud</div>
                </div>
            </div>
            <div class="auth-card">
                <div class="eyebrow">CONFIGURAZIONE INIZIALE</div>
                <h1>Collega il database</h1>
                <p>
                    Inserisci Project URL e Publishable key nei Secrets
                    di Streamlit Cloud.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.code(
        'SUPABASE_URL = "https://tuo-progetto.supabase.co"\n'
        'SUPABASE_PUBLISHABLE_KEY = "sb_publishable_..."',
        language="toml",
    )

    c1, c2 = st.columns([1, 1])
    if c1.button(
        "Continua in modalità prova",
        type="primary",
        use_container_width=True,
    ):
        st.session_state["guest_mode"] = True
        st.rerun()

    c2.caption(
        "La modalità prova non salva i dati dopo la chiusura della sessione."
    )
    st.stop()


def render_auth_screen():
    valid_key, key_error = validate_supabase_credentials()

    st.markdown(
        """
        <div class="auth-shell">
            <div class="auth-brand">
                <div class="brand-mark">FA</div>
                <div>
                    <div class="auth-brand-name">FantAsta Assistant</div>
                    <div class="auth-brand-sub">La tua asta, salvata nel cloud.</div>
                </div>
            </div>
            <div class="auth-card">
                <div class="eyebrow">BENTORNATO</div>
                <h1>Accedi alla tua asta</h1>
                <p>Rosa, budget e impostazioni vengono sincronizzati sul tuo account.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not valid_key:
        st.error(
            "Connessione Supabase non valida. "
            f"Dettaglio: {key_error}"
        )

        d = safe_key_diagnostics()

        st.markdown("**Diagnostica sicura**")
        st.code(
            f"Project ref: {d['project_ref']}\n"
            f"Key: {d['key_prefix']}{d['key_suffix']}\n"
            f"Lunghezza key: {d['key_length']}\n"
            f"Formato sb_publishable_: {'OK' if d['key_format_ok'] else 'NO'}"
        )

        st.info(
            "In Streamlit > Settings > Secrets lascia SOLO "
            "SUPABASE_URL e SUPABASE_PUBLISHABLE_KEY. "
            "Cancella eventuali vecchie righe SUPABASE_KEY, chiavi anon o duplicati."
        )
        st.stop()

    login_tab, signup_tab = st.tabs(["Accedi", "Crea account"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input(
                "Email",
                placeholder="nome@email.it",
            )
            password = st.text_input(
                "Password",
                type="password",
                placeholder="••••••••",
            )
            submitted = st.form_submit_button(
                "Accedi",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            if not email or not password:
                st.error("Inserisci email e password.")
            else:
                try:
                    r = auth_request(
                        "POST",
                        "token?grant_type=password",
                        {
                            "email": email.strip(),
                            "password": password,
                        },
                    )
                    if not r.ok:
                        st.error(readable_auth_error(r))
                    elif set_auth_session(r.json()):
                        st.session_state["cloud_state_loaded"] = False
                        load_user_state()
                        st.rerun()
                    else:
                        st.error("Accesso non completato.")
                except Exception as e:
                    st.error(f"Accesso non riuscito: {e}")

    with signup_tab:
        with st.form("signup_form"):
            new_email = st.text_input(
                "Email",
                placeholder="nome@email.it",
                key="signup_email",
            )
            new_password = st.text_input(
                "Password",
                type="password",
                placeholder="Minimo 8 caratteri",
                key="signup_password",
            )
            confirm_password = st.text_input(
                "Conferma password",
                type="password",
                placeholder="Ripeti la password",
                key="signup_password_confirm",
            )
            signup = st.form_submit_button(
                "Crea account",
                use_container_width=True,
            )

        if signup:
            if not new_email or not new_password:
                st.error("Compila email e password.")
            elif len(new_password) < 8:
                st.error("Usa una password di almeno 8 caratteri.")
            elif new_password != confirm_password:
                st.error("Le password non coincidono.")
            else:
                try:
                    r = auth_request(
                        "POST",
                        "signup",
                        {
                            "email": new_email.strip(),
                            "password": new_password,
                        },
                    )

                    if not r.ok:
                        st.error(readable_auth_error(r))
                    else:
                        data = r.json() or {}
                        if data.get("access_token") and set_auth_session(data):
                            st.session_state["cloud_state_loaded"] = False
                            save_user_state(force=True)
                            st.rerun()
                        else:
                            st.success(
                                "Account creato. Controlla l'email di conferma, "
                                "poi torna qui e accedi."
                            )
                except Exception as e:
                    st.error(f"Registrazione non riuscita: {e}")

    st.stop()


# Stile aggiuntivo per login e nuova UI.
st.markdown(
    """
    <style>
    .auth-shell {
        max-width: 720px;
        margin: 7vh auto 18px auto;
    }
    .auth-brand {
        display:flex;
        align-items:center;
        gap:12px;
        margin-bottom:18px;
    }
    .brand-mark {
        width:44px;
        height:44px;
        display:flex;
        align-items:center;
        justify-content:center;
        border-radius:13px;
        background:#111827;
        color:white;
        font-weight:800;
        letter-spacing:-.04em;
    }
    .auth-brand-name {
        font-weight:800;
        font-size:16px;
        letter-spacing:-.02em;
    }
    .auth-brand-sub {
        font-size:12px;
        color:#6b7280;
        margin-top:1px;
    }
    .auth-card {
        background:white;
        border:1px solid #e5e7eb;
        border-radius:24px;
        padding:30px 32px;
        box-shadow:0 16px 45px rgba(17,24,39,.07);
        margin-bottom:14px;
    }
    .auth-card h1 {
        font-size:30px;
        margin:5px 0 8px;
        letter-spacing:-.045em;
    }
    .auth-card p {
        color:#6b7280;
        margin:0;
        max-width:520px;
        line-height:1.55;
    }
    .eyebrow {
        color:#6b7280;
        font-size:10px;
        font-weight:800;
        letter-spacing:.12em;
    }
    .user-chip {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:10px;
        padding:10px 12px;
        border:1px solid #e5e7eb;
        border-radius:14px;
        background:#f9fafb;
        font-size:12px;
    }
    .save-ok {
        color:#166534;
        background:#ecfdf3;
        border:1px solid #bbf7d0;
        border-radius:999px;
        padding:5px 8px;
        font-size:11px;
        font-weight:700;
    }
    .save-error {
        color:#991b1b;
        background:#fef2f2;
        border:1px solid #fecaca;
        border-radius:999px;
        padding:5px 8px;
        font-size:11px;
        font-weight:700;
    }
    .roster-hero {
        display:grid;
        grid-template-columns: 1.4fr .8fr;
        gap:14px;
        margin:10px 0 16px;
    }
    .roster-panel {
        background:white;
        border:1px solid #e5e7eb;
        border-radius:20px;
        padding:20px;
        box-shadow:0 6px 20px rgba(17,24,39,.035);
    }
    .roster-title {
        font-size:20px;
        font-weight:800;
        letter-spacing:-.035em;
        margin:2px 0 4px;
    }
    .roster-desc {
        color:#6b7280;
        font-size:13px;
        line-height:1.5;
    }
    @media(max-width:800px) {
        .roster-hero {grid-template-columns:1fr;}
        .auth-card {padding:24px 22px;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Gate account.
if not supabase_configured():
    if not st.session_state.get("guest_mode"):
        render_setup_screen()
else:
    if not st.session_state.get("auth_user_id"):
        if not valid_access_token():
            render_auth_screen()

    if (
        st.session_state.get("auth_user_id")
        and not st.session_state.get("cloud_state_loaded")
    ):
        load_user_state()



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


@st.cache_data(ttl=120, show_spinner=False)
def reader_markdown(url):
    reader_url = "https://r.jina.ai/" + url
    r = requests.get(
        reader_url,
        headers={
            "User-Agent": HEADERS["User-Agent"],
            "Accept": "text/plain",
            "Cache-Control": "no-cache",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.text


def _pipe_fields(line):
    parts = [x.strip() for x in line.strip().split("|")]
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return parts


def parse_stats_markdown(md):
    rows = []
    for raw in md.splitlines():
        if "|" not in raw:
            continue

        fields = _pipe_fields(raw)
        if len(fields) < 10:
            continue

        team_idx = None
        for i, f in enumerate(fields):
            if re.fullmatch(r"[A-Z]{3}", f or ""):
                team_idx = i
                break

        if team_idx is None or team_idx < 1:
            continue

        name = ""
        for j in range(team_idx - 1, -1, -1):
            if fields[j]:
                name = fields[j]
                break

        if not name or name.lower() in {"calciatore", "nome"}:
            continue

        after = fields[team_idx + 1:]
        if len(after) < 10:
            continue

        def num(value):
            if value is None:
                return np.nan
            s = str(value).strip().replace(".", "").replace(",", ".")
            s = re.sub(r"[^\d\.-]", "", s)
            return pd.to_numeric(s, errors="coerce")

        pv = num(after[0])
        if pd.isna(pv):
            continue

        rows.append({
            "Nome": clean_name(name),
            "Squadra_STATS": fields[team_idx],
            "PV": pv,
            "MV": num(after[1]),
            "FM": num(after[2]),
            "Gol": num(after[3]),
            "Assist": num(after[7]) if len(after) > 7 else np.nan,
            "Amm": num(after[8]) if len(after) > 8 else np.nan,
            "Esp": num(after[9]) if len(after) > 9 else np.nan,
        })

    if not rows:
        raise ValueError("nessuna riga statistiche trovata nel reader")

    out = pd.DataFrame(rows)
    out["_key"] = out["Nome"].map(key_name)
    return out.drop_duplicates("_key").reset_index(drop=True)


def parse_quotes_markdown(md):
    rows = []

    for raw in md.splitlines():
        if "|" not in raw:
            continue

        fields = _pipe_fields(raw)
        if len(fields) < 7:
            continue

        team_idx = None
        for i, f in enumerate(fields):
            if re.fullmatch(r"[A-Z]{3}", f or ""):
                team_idx = i
                break

        if team_idx is None or team_idx < 1:
            continue

        name = ""
        for j in range(team_idx - 1, -1, -1):
            if fields[j]:
                name = fields[j]
                break

        if not name or name.lower() in {"calciatore", "nome"}:
            continue

        after = fields[team_idx + 1:]
        if len(after) < 3:
            continue

        def num(value):
            s = str(value).strip().replace(".", "").replace(",", ".")
            s = re.sub(r"[^\d\.-]", "", s)
            return pd.to_numeric(s, errors="coerce")

        qa = num(after[1])
        fvm = num(after[2])
        if pd.isna(qa):
            continue

        rows.append({
            "Nome": clean_name(name),
            "Squadra_FC": fields[team_idx],
            "QI_FC": num(after[0]),
            "QA_FC": qa,
            "FVM": fvm,
        })

    if not rows:
        raise ValueError("nessuna quotazione trovata nel reader")

    out = pd.DataFrame(rows)
    out["_key"] = out["Nome"].map(key_name)
    return out.drop_duplicates("_key").reset_index(drop=True)


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
    errors = []

    try:
        md = reader_markdown(FANTACALCIO_QUOTES_URL)
        out = parse_quotes_markdown(md)
        out.attrs["source"] = "Fantacalcio via Reader"
        return out
    except Exception as e:
        errors.append(f"reader: {e}")

    try:
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
            raise ValueError("tabella quotazioni non trovata")

        c_nome = pick_col(best, ["Calciatore", "Giocatore", "Nome"])
        c_sq = pick_col(best, ["Sq", "Squadra"])
        cols_norm = [(c, norm_header(c)) for c in best.columns]

        def first_matching(prefix):
            exact = [c for c, n in cols_norm if n == prefix]
            if exact:
                return exact[0]
            begins = [c for c, n in cols_norm if n.startswith(prefix)]
            return begins[0] if begins else None

        c_qi = first_matching("qi")
        c_qa = first_matching("qa")
        c_fvm = next((c for c, n in cols_norm if n.startswith("fvm")), None)

        if c_nome is None:
            object_cols = [c for c in best.columns if best[c].dtype == object]
            if object_cols:
                c_nome = max(
                    object_cols,
                    key=lambda c: best[c].astype(str).str.len().mean()
                )

        if c_nome is None or c_qa is None:
            raise ValueError("colonne quotazioni non riconosciute")

        out = pd.DataFrame({
            "Nome": best[c_nome].map(clean_name),
            "Squadra_FC": (
                best[c_sq].astype(str).str.strip()
                if c_sq is not None else ""
            ),
            "QI_FC": to_num(best[c_qi]) if c_qi is not None else np.nan,
            "QA_FC": to_num(best[c_qa]),
            "FVM": to_num(best[c_fvm]) if c_fvm is not None else np.nan,
        })

        out = out[out["Nome"].notna() & (out["Nome"].str.len() > 1)].copy()
        out["_key"] = out["Nome"].map(key_name)
        out = out.drop_duplicates("_key").reset_index(drop=True)
        out.attrs["source"] = "Fantacalcio HTML"
        return out

    except Exception as e:
        errors.append(f"html: {e}")

    raise ValueError(" | ".join(errors))


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
    errors = []

    try:
        md = reader_markdown(FANTACALCIO_STATS_URL)
        out = parse_stats_markdown(md)
        out.attrs["source"] = "Fantacalcio via Reader"
        return out
    except Exception as e:
        errors.append(f"reader: {e}")

    try:
        tables = read_html_tables(FANTACALCIO_STATS_URL)
        best = None
        best_score = -1

        for raw in tables:
            df = flatten_columns(raw)
            text = " ".join(map(str, df.columns)).lower()
            score = (
                int("pv" in text) * 2
                + int("mv" in text) * 2
                + int("fm" in text) * 2
                + int("gol" in text)
                + int("ass" in text)
            )
            if len(df) >= 20 and score > best_score:
                best = df.copy()
                best_score = score

        if best is None:
            raise ValueError("tabella HTML non trovata")

        df = best
        c_pv = pick_col(df, ["PV"])
        c_mv = pick_col(df, ["MV"])
        c_fm = pick_col(df, ["FM"])
        c_gol = pick_col(df, ["Gol"])
        c_ass = pick_col(df, ["Ass", "Assist"])
        c_amm = pick_col(df, ["Amm"])
        c_esp = pick_col(df, ["Esp"])
        c_sq = pick_col(df, ["Sq", "Squadra"])
        c_nome = pick_col(df, ["Calciatore", "Giocatore", "Nome"])

        if c_nome is None:
            candidates = []
            for c in df.columns:
                s = df[c].astype(str).str.strip()
                alpha = s.str.contains(r"[A-Za-zÀ-ÿ]", regex=True, na=False).mean()
                numeric = pd.to_numeric(
                    s.str.replace(",", ".", regex=False),
                    errors="coerce"
                ).notna().mean()
                teamish = s.str.fullmatch(r"[A-Z]{3}", na=False).mean()
                avg_len = s.str.len().mean()
                candidates.append(
                    (alpha * 4 - numeric * 3 - teamish * 3 + min(avg_len / 10, 2), c)
                )
            c_nome = max(candidates, key=lambda x: x[0])[1]

        if c_pv is None:
            raise ValueError("PV non riconosciuta")

        out = pd.DataFrame({
            "Nome": df[c_nome].map(clean_name),
            "Squadra_STATS": (
                df[c_sq].astype(str).str.strip()
                if c_sq is not None else ""
            ),
            "PV": to_num(df[c_pv]),
            "MV": to_num(df[c_mv]) if c_mv is not None else np.nan,
            "FM": to_num(df[c_fm]) if c_fm is not None else np.nan,
            "Gol": to_num(df[c_gol]) if c_gol is not None else np.nan,
            "Assist": to_num(df[c_ass]) if c_ass is not None else np.nan,
            "Amm": to_num(df[c_amm]) if c_amm is not None else np.nan,
            "Esp": to_num(df[c_esp]) if c_esp is not None else np.nan,
        })

        out = out[
            out["Nome"].notna()
            & (out["Nome"].str.len() > 1)
            & out["PV"].notna()
        ].copy()

        out["_key"] = out["Nome"].map(key_name)
        out = out.drop_duplicates("_key").reset_index(drop=True)

        if out.empty:
            raise ValueError("tabella HTML vuota")

        out.attrs["source"] = "Fantacalcio HTML"
        return out

    except Exception as e:
        errors.append(f"html: {e}")

    raise ValueError(" | ".join(errors))


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

    # Fallback più utile: presenze a voto / massimo presenze della squadra.
    # Non viene chiamato "titolarità reale", ma "stima titolarità" in UI.
    if "Squadra" in out.columns:
        team_max_pv = out.groupby("Squadra")["PV"].transform("max").replace(0, np.nan)
        pv_proxy = (pv / team_max_pv * 100).clip(0, 100)
    else:
        pv_proxy = np.clip(pv / max_pv * 100, 0, 100)

    out["TitolaritaProxy"] = tit_real.combine_first(pv_proxy).clip(0, 100)
    out["TitolaritaFonte"] = np.where(
        tit_real.notna(),
        "Starts",
        "Stima da presenze",
    )

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
        status["Fantacalcio quotazioni/FVM"] = (
            f"OK ({len(quotes)}) · {quotes.attrs.get('source', 'Fantacalcio')}"
        )
    except Exception as e:
        status["Fantacalcio quotazioni/FVM"] = f"KO: {e}"

    try:
        stats = fetch_fantacalcio_stats()
        status["Fantacalcio statistiche"] = (
            f"OK ({len(stats)}) · {stats.attrs.get('source', 'Fantacalcio')}"
        )
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
    save_user_state(force=True)

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
# FORMAZIONI STAGIONALI 2026/27
# ------------------------------------------------------------

@st.cache_data(ttl=900, show_spinner=False)
def fetch_season_formations():
    errors = []
    text = None
    source = None

    try:
        text = reader_markdown(FANTACALCIO_SEASON_FORMATIONS_URL)
        source = "Fantacalcio via Reader"
    except Exception as e:
        errors.append(f"reader: {e}")

    if not text:
        try:
            r = requests.get(
                FANTACALCIO_SEASON_FORMATIONS_URL,
                headers=HEADERS,
                timeout=20,
            )
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text("\n", strip=True)
            source = "Fantacalcio AMP"
        except Exception as e:
            errors.append(f"html: {e}")

    if not text:
        raise ValueError(" | ".join(errors))

    team_names = [
        "ATALANTA", "BOLOGNA", "CAGLIARI", "COMO", "FIORENTINA",
        "FROSINONE", "GENOA", "INTER", "JUVENTUS", "LAZIO",
        "LECCE", "MILAN", "MONZA", "NAPOLI", "PARMA",
        "ROMA", "SASSUOLO", "TORINO", "UDINESE", "VENEZIA",
    ]

    normalized = text.replace("\r", "\n")
    positions = []

    for team in team_names:
        matches = []
        for p in [
            rf"(?m)^##\s+{re.escape(team)}\s*$",
            rf"(?m)^\s*{re.escape(team)}\s*$",
        ]:
            m = re.search(p, normalized, flags=re.I)
            if m:
                matches.append(m)
        if matches:
            m = min(matches, key=lambda x: x.start())
            positions.append((m.start(), team, m.end()))

    positions.sort()
    rows = []

    for i, (start, team, content_start) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(normalized)
        block = normalized[content_start:end]

        def one_line(label):
            m = re.search(
                rf"(?im)^\s*{re.escape(label)}\s*:\s*(.+?)\s*$",
                block,
            )
            return re.sub(r"\s+", " ", m.group(1)).strip(" .") if m else ""

        allenatore = one_line("Allenatore")
        modulo = one_line("Modulo")
        ballottaggi = one_line("Ballottaggi")
        rigoristi = one_line("Rigoristi")
        piazzati = one_line("Calci da fermo")

        fm = re.search(
            r"(?is)Probabile formazione[^\n:]*\s*:\s*(.*?)"
            r"(?=\n\s*Ballottaggi\s*:|\n\s*Rigoristi\s*:|\n\s*Calci da fermo\s*:|\n##\s|\Z)",
            block,
        )
        formazione = (
            re.sub(r"\s+", " ", fm.group(1)).strip(" .")
            if fm else ""
        )

        rows.append({
            "Squadra": team.title(),
            "Allenatore": allenatore,
            "Modulo": modulo,
            "Formazione": formazione,
            "Ballottaggi": ballottaggi,
            "Rigoristi": rigoristi,
            "Piazzati": piazzati,
            "Fonte": source,
        })

    out = pd.DataFrame(rows)

    valid_xi = (
        (out["Formazione"].astype(str).str.len() >= 10).sum()
        if not out.empty else 0
    )
    if out.empty or valid_xi < 15:
        raise ValueError(
            f"formazioni incomplete: {valid_xi}/{len(out)} con XI valido"
        )

    return out


def split_starting_xi(formazione_text):
    """
    Converte la stringa Fantacalcio in una lista leggibile di 11 nomi.
    Mantiene l'ordine originale.
    """
    if not formazione_text:
        return []

    cleaned = (
        formazione_text
        .replace(";", ",")
        .replace("  ", " ")
        .strip(" .")
    )
    players = [p.strip() for p in cleaned.split(",") if p.strip()]
    return players[:11]



# ------------------------------------------------------------
# UI HELPERS V9
# ------------------------------------------------------------

ROLE_LABELS = {
    "P": "Portieri",
    "D": "Difensori",
    "C": "Centrocampisti",
    "A": "Attaccanti",
}


def ui_fmt(value, digits=0, suffix=""):
    if value is None or pd.isna(value):
        return "n.d."
    try:
        if digits == 0:
            txt = str(int(round(float(value))))
        else:
            txt = f"{float(value):.{digits}f}"
        return f"{txt}{suffix}"
    except Exception:
        return str(value)


def render_role_progress():
    cards = []
    for role in "PDCA":
        occupied = slot_occupati(role)
        total = int(st.session_state["slot"][role])
        pct = min(max((occupied / total * 100) if total else 0, 0), 100)
        spent = int(speso_reparto(role))
        target = int(round(target_reparto(role)))
        cards.append(
            f"""
            <div class="fa-role-card">
                <div class="fa-role-top">
                    <div class="fa-role-name">{ROLE_LABELS[role]}</div>
                    <div class="fa-role-count">{occupied}/{total}</div>
                </div>
                <div class="fa-role-value">{spent} FM</div>
                <div class="fa-progress"><span style="width:{pct:.1f}%"></span></div>
                <div class="fa-role-meta">Target reparto {target} FM · {slot_liberi(role)} slot liberi</div>
            </div>
            """
        )
    st.markdown(
        '<div class="fa-grid">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )


def render_section_header(title, description=None):
    desc = (
        f'<div class="fa-section-desc">{description}</div>'
        if description else ""
    )
    st.markdown(
        f"""
        <div class="fa-section-head">
            <div>
                <div class="fa-section-title">{title}</div>
                {desc}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty(title, text):
    st.markdown(
        f"""
        <div class="fa-empty">
            <strong>{title}</strong>
            {text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_player_summary(row, recommended=None):
    role = row.get("Ruolo", "")
    team = row.get("Squadra", "")
    name = row.get("Nome", "")
    price_html = ""
    if recommended is not None:
        price_html = f"""
        <div class="fa-price-badge">
            <div class="fa-price-label">Tetto consigliato</div>
            <div class="fa-price-value">{recommended} FM</div>
        </div>
        """

    tit = row.get("TitolaritaPct")
    if pd.isna(tit):
        tit = row.get("TitolaritaProxy")

    st.markdown(
        f"""
        <div class="fa-player-card">
            <div class="fa-player-head">
                <div>
                    <div class="fa-player-name">{name}</div>
                    <div class="fa-player-meta">{team} · {ROLE_LABELS.get(role, role)}</div>
                </div>
                {price_html}
            </div>
            <div class="fa-mini-grid">
                <div class="fa-mini">
                    <div class="fa-mini-label">Presenze</div>
                    <div class="fa-mini-value">{ui_fmt(row.get("PV"))}</div>
                </div>
                <div class="fa-mini">
                    <div class="fa-mini-label">Titolarità</div>
                    <div class="fa-mini-value">{ui_fmt(tit, 0, "%")}</div>
                </div>
                <div class="fa-mini">
                    <div class="fa-mini-label">Gol</div>
                    <div class="fa-mini-value">{ui_fmt(row.get("Gol"))}</div>
                </div>
                <div class="fa-mini">
                    <div class="fa-mini-label">Assist</div>
                    <div class="fa-mini-value">{ui_fmt(row.get("Assist"))}</div>
                </div>
                <div class="fa-mini">
                    <div class="fa-mini-label">Media voto</div>
                    <div class="fa-mini-value">{ui_fmt(row.get("MV"), 2)}</div>
                </div>
                <div class="fa-mini">
                    <div class="fa-mini-label">Fantamedia</div>
                    <div class="fa-mini-value">{ui_fmt(row.get("FM"), 2)}</div>
                </div>
                <div class="fa-mini">
                    <div class="fa-mini-label">QA</div>
                    <div class="fa-mini-value">{ui_fmt(row.get("Quotazione"))}</div>
                </div>
                <div class="fa-mini">
                    <div class="fa-mini-label">FVM</div>
                    <div class="fa-mini-value">{ui_fmt(row.get("FVM"))}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------

live_text = (
    st.session_state.get("last_update")
    or "sincronizzazione iniziale"
)

account_name = (
    "Modalità prova"
    if st.session_state.get("guest_mode")
    else st.session_state.get("auth_email", "Account")
)

st.markdown(
    f"""
    <div class="app-hero">
      <div class="hero-row">
        <div>
          <div class="micro-label" style="color:#94a3b8;">FANTACALCIO · ASTA LIVE</div>
          <div class="hero-title">Decidi in pochi secondi.</div>
          <div class="hero-sub">
            Chi prendere, quanto spendere e cosa manca alla tua rosa. Tutto nello stesso posto.
          </div>
        </div>
        <div style="display:flex; flex-direction:column; gap:8px; align-items:flex-end;">
          <div class="live-badge">
            <span class="live-dot"></span>
            LIVE · {live_text}
          </div>
          <div style="font-size:11px; color:#94a3b8;">{account_name}</div>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### FantAsta")
    st.caption("Assistant · V10")

    if st.session_state.get("guest_mode"):
        st.markdown(
            '<div class="user-chip"><span>Modalità prova</span>'
            '<span class="save-error">NON SALVA</span></div>',
            unsafe_allow_html=True,
        )
    else:
        user_email = st.session_state.get("auth_email", "Account")
        saved_at = st.session_state.get("last_saved_at", "—")
        save_error = st.session_state.get("save_error")
        save_badge = (
            '<span class="save-error">ERRORE SAVE</span>'
            if save_error
            else f'<span class="save-ok">SALVATO {saved_at}</span>'
        )
        st.markdown(
            f'<div class="user-chip"><span>{user_email}</span>{save_badge}</div>',
            unsafe_allow_html=True,
        )
        if st.button("Esci dall'account", use_container_width=True):
            logout_user()

    st.divider()

    st.markdown("#### Dati live")
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
    st.markdown("#### Lega")

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
        save_user_state(force=True)
        st.rerun()

    st.divider()
    st.markdown("#### Listone")

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

                save_user_state(force=True)
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

render_role_progress()

tab_rosa, tab_asta, tab_consigli, tab_giocatori, tab_formazioni, tab_news = st.tabs([
    "La mia rosa",
    "Asta live",
    "Consigli",
    "Giocatori",
    "Formazioni 26/27",
    "News",
])


# ------------------------------------------------------------
# TAB ROSA — aggiunta giocatori molto evidente
# ------------------------------------------------------------

with tab_rosa:
    render_section_header(
        "La mia rosa",
        "Registra gli acquisti appena si chiudono: budget, slot e priorità si aggiornano e vengono salvati automaticamente.",
    )

    st.subheader("Nuovo acquisto")

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
                save_user_state(force=True)
                st.rerun()

    else:
        render_empty(
            "Rosa ancora vuota",
            "Quando chiudi il primo acquisto, registralo dal modulo qui sopra.",
        )

    with st.expander("Reset completo asta"):
        if st.button(
            "🗑️ Azzera rosa e budget speso",
            key="reset_roster",
        ):
            st.session_state["rosa"] = []
            st.session_state["speso"] = 0
            save_user_state(force=True)
            st.rerun()


# ------------------------------------------------------------
# TAB ASSISTENTE
# ------------------------------------------------------------

with tab_asta:
    render_section_header(
        "Asta live",
        "Cerca il giocatore chiamato, inserisci l'offerta corrente e guarda subito il tetto coerente con il tuo budget.",
    )

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

            render_player_summary(row, recommended=rec)

            m1, m2, m3, m4 = st.columns(4)

            m1.metric(
                "Ruolo",
                role,
            )
            m2.metric(
                "Tetto consigliato",
                f"{rec} FM",
            )
            m3.metric(
                "Massimo possibile",
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

            st.markdown(
                '<div class="fa-note">Le statistiche qui sopra entrano nel punteggio d’acquisto insieme a budget residuo, slot mancanti e priorità del reparto.</div>',
                unsafe_allow_html=True,
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
    render_section_header(
        "Consigli acquisti",
        "Slot 1 è la fascia premium; Slot 8 è profondità. Jolly e Scommesse cercano valore rispetto a prezzo e rendimento.",
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
        st.markdown(
            f'<div class="fa-note">{need_txt}</div>',
            unsafe_allow_html=True,
        )

        if view.empty:
            st.info("Nessun giocatore rientra in questa categoria al momento.")
        else:
            cols = [
                "Nome", "Squadra", "Fascia", "Quotazione", "FVM",
                "PV", "Starts", "TitolaritaPct", "TitolaritaProxy", "TitolaritaFonte", "MV", "FM", "Gol", "Assist",
                "IndiceAcquisto", "Jolly", "Scommessa",
            ]
            cols = [c for c in cols if c in view.columns]

            st.dataframe(
                view[cols].head(40),
                hide_index=True,
                use_container_width=True,
            )

            st.markdown("#### Profili da guardare")
            for _, r in view.head(6).iterrows():
                prezzo = recommended_price(r, df_disponibili)
                tags = []
                if bool(r.get("Jolly", False)):
                    tags.append("Jolly")
                if bool(r.get("Scommessa", False)):
                    tags.append("Scommessa")
                tag_txt = " · ".join(tags) if tags else r["Fascia"]

                st.markdown(
                    f"""
                    <div class="fa-player-card" style="padding:14px 16px;margin:7px 0;">
                        <div class="fa-player-head">
                            <div>
                                <div style="font-size:17px;font-weight:800;color:#101828;">{r['Nome']}</div>
                                <div class="fa-player-meta">{r.get('Squadra','')} · {r['Fascia']} · {tag_txt}</div>
                            </div>
                            <div class="fa-price-badge">
                                <div class="fa-price-label">Tetto rosa</div>
                                <div class="fa-price-value" style="font-size:20px;">{prezzo} FM</div>
                            </div>
                        </div>
                        <div style="display:flex;gap:14px;flex-wrap:wrap;margin-top:9px;font-size:12px;color:#475467;">
                            <span>QA <strong>{ui_fmt(r.get('Quotazione'))}</strong></span>
                            <span>FVM <strong>{ui_fmt(r.get('FVM'))}</strong></span>
                            <span>FM <strong>{ui_fmt(r.get('FM'),2)}</strong></span>
                            <span>Gol <strong>{ui_fmt(r.get('Gol'))}</strong></span>
                            <span>Assist <strong>{ui_fmt(r.get('Assist'))}</strong></span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# ------------------------------------------------------------
# TAB GIOCATORI
# ------------------------------------------------------------

with tab_giocatori:
    render_section_header(
        "Giocatori",
        "Esplora il listone completo e ordina i profili in base al rendimento e alla priorità della tua rosa.",
    )

    stats_ok = (
        int(pd.to_numeric(df.get("PV"), errors="coerce").notna().sum())
        if not df.empty else 0
    )
    st.markdown(
        f'<div class="fa-note"><strong>Copertura statistiche:</strong> '
        f'{stats_ok}/{len(df)} giocatori con dati stagione. '
        f'Se il numero è basso, apri “Stato fonti online” in fondo.</div>',
        unsafe_allow_html=True,
    )

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
            "PV", "Starts", "TitolaritaPct", "TitolaritaProxy", "TitolaritaFonte", "MV", "FM", "Gol", "Assist",
            "RendimentoScore", "PrioritaRosa",
            "ScoreGuidato",
        ]

        st.dataframe(
            view[show_cols],
            hide_index=True,
            use_container_width=True,
        )



# ------------------------------------------------------------
# TAB FORMAZIONI 2026/27
# ------------------------------------------------------------

with tab_formazioni:
    render_section_header(
        "Formazioni 2026/27",
        "Undici base, modulo, ballottaggi, rigoristi e piazzati delle squadre di Serie A.",
    )

    try:
        formations_df = fetch_season_formations()
    except Exception as e:
        formations_df = pd.DataFrame()
        st.error(f"Non riesco a leggere le formazioni stagionali: {e}")

    if formations_df.empty:
        st.info("Formazioni stagionali non disponibili in questo momento.")
    else:
        team = st.selectbox(
            "Scegli squadra",
            formations_df["Squadra"].tolist(),
            key="season_team_select",
        )

        r = formations_df[
            formations_df["Squadra"] == team
        ].iloc[0]

        st.caption(
            f"Fonte: {r.get('Fonte', 'Fantacalcio')} · "
            f"{len(formations_df)} squadre lette"
        )

        st.markdown(
            f"""
            <div class="fa-player-card">
                <div class="fa-player-head">
                    <div>
                        <div class="fa-player-name">{team}</div>
                        <div class="fa-player-meta">Allenatore · {r["Allenatore"] or "n.d."}</div>
                    </div>
                    <div class="fa-price-badge">
                        <div class="fa-price-label">Modulo base</div>
                        <div class="fa-price-value">{r["Modulo"] or "n.d."}</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### Undici base")
        xi = split_starting_xi(r["Formazione"])

        if xi:
            xi_df = pd.DataFrame({
                "#": range(1, len(xi) + 1),
                "Giocatore": xi,
            })
            st.dataframe(
                xi_df,
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("Undici base non riconosciuto automaticamente.")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Ballottaggi")
            st.write(r["Ballottaggi"] or "Nessun dato")
            st.markdown("#### Rigoristi")
            st.write(r["Rigoristi"] or "Nessun dato")

        with c2:
            st.markdown("#### Calci da fermo")
            st.write(r["Piazzati"] or "Nessun dato")
            st.markdown("#### Formazioni giornata")
            st.markdown(
                f"[Apri le probabili formazioni live su Fantacalcio.it]"
                f"({FANTACALCIO_MATCHDAY_FORMATIONS_URL})"
            )

        with st.expander("Vedi tutte le 20 squadre"):
            st.dataframe(
                formations_df[
                    ["Squadra", "Allenatore", "Modulo", "Formazione"]
                ],
                hide_index=True,
                use_container_width=True,
            )


# ------------------------------------------------------------
# TAB NEWS
# ------------------------------------------------------------

with tab_news:
    render_section_header(
        "News giocatore",
        "Controlla rapidamente segnali su titolarità, recuperi, infortuni e gerarchie prima di rilanciare.",
    )

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

# Safety net: se qualcosa nello stato utente è cambiato senza passare
# da un pulsante esplicito, viene comunque salvato al termine del rerun.
if st.session_state.get("auth_user_id") and not st.session_state.get("guest_mode"):
    save_user_state(force=False)

