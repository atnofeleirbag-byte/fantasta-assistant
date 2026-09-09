# FantAsta Assistant Pro V2

App Streamlit per asta Fantacalcio con:
- gestione della propria rosa;
- budget residuo e budget per reparto;
- prezzo consigliato dinamico;
- rendimento giocatore;
- statistiche da Fantacalcio.it;
- dati/listone da Gazzetta;
- news e segnali da SOS Fanta;
- giudizi AFFARE / OTTIMO / OK / CARO / STOP.

## Pubblicazione su Streamlit Community Cloud

1. Crea un repository GitHub.
2. Carica tutti i file di questa cartella.
3. Vai su https://share.streamlit.io/
4. Accedi con GitHub.
5. Seleziona il repository.
6. Come file principale scegli `app.py`.
7. Premi Deploy.

Dopo il deploy otterrai un link simile a:

`https://nome-app.streamlit.app`

Quel link può essere aperto da Chrome, smartphone, tablet o qualsiasi altro browser.

## File principali

- `app.py` -> applicazione
- `requirements.txt` -> librerie necessarie
- `.streamlit/config.toml` -> configurazione Streamlit Cloud

## Nota

Le fonti online possono modificare la struttura delle proprie pagine. L'app mantiene il caricamento manuale del listone come fallback.
