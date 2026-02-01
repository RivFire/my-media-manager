import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Comic Manager Pro Cloud", page_icon="📖", layout="wide")

# --- 2. FUNZIONI DI UTILITÀ ---
def format_it_comma(valore):
    try:
        return "{:,.2f}".format(float(valore)).replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "0,00"

def get_safe_options(df, column):
    """Estrae opzioni uniche, rimuove i vuoti e ordina senza errori di tipo"""
    if df.empty or column not in df.columns:
        return []
    options = df[column].astype(str).replace('nan', '').replace('None', '')
    options = [opt for opt in options.unique() if opt.strip() != '']
    return sorted(options)

# --- 3. COSTANTI ---
COLUMNS_ORDER = [
    "serie", "subserie", "numero", "variante", "titolo", "editore", 
    "formato", "frequenza", "colore", "pagine", "prezzo_copertina", "valuta",
    "giorno_uscita", "mese_uscita", "anno_uscita", 
    "codice", "isbn", "stato", "storage_box", "note"
]

LISTA_FORMATO = ["Brossurato", "Cartonato", "Spillato", "Pocket", "Graphic Novel", "Albo", "Altro"]
LISTA_STATO = ["stock", "wish list"]

# --- 4. CSS ---
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 14px !important; }
    h1 { font-size: 28px !important; color: #ff4b4b; font-weight: bold; }
    [data-testid="stMetricValue"] { font-size: 24px; color: #ff4b4b; }
    .stDataFrame { border: 1px solid #eee; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. CONNESSIONE (SOLO LETTURA) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carica_dati():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        data = conn.read(spreadsheet=url, ttl="0")
        if data.empty:
            return pd.DataFrame(columns=COLUMNS_ORDER)
        for col in COLUMNS_ORDER:
            if col not in data.columns:
                data[col] = ""
        return data
    except Exception as e:
        st.error(f"Errore Sincronizzazione: {e}")
        return pd.DataFrame(columns=COLUMNS_ORDER)

df = carica_dati()

# --- 6. SIDEBAR ---
st.sidebar.title("📖 Comic Manager")
# Menu limitato alla sola consultazione
menu = st.sidebar.radio("Vai a:", ["📚 Archivio", "📊 Statistiche", "⚙️ Configurazione"])

# --- SEZIONE 1: ARCHIVIO (SOLO LETTURA + 100 RIGHE) ---
if menu == "📚 Archivio":
    st.title("📚 La mia Collezione")
    
    if not df.empty:
        # --- CALCOLO METRICHE SICURO ---
        df_calc = df.copy()
        df_calc['prezzo_copertina'] = pd.to_numeric(df_calc['prezzo_copertina'], errors='coerce').fillna(0)
        
        # Filtro flessibile: Euro, euro, EURO sono tutti validi
        mask_euro = df_calc['valuta'].astype(str).str.contains('Euro', case=False, na=False)
        val_tot = df_calc[mask_euro]['prezzo_copertina'].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("Albi Totali", len(df))
        m2.metric("In Stock", len(df[df['stato'].astype(str).str.lower() == 'stock']))
        m3.metric("Valore (Euro)", f"€ {format_it_comma(val_tot)}")

        st.divider()
        
        # --- FILTRI AVANZATI ---
        with st.expander("🔍 Filtri Avanzati", expanded=True):
            f1, f2, f3 = st.columns(3)
            search_text = f1.text_input("Cerca testo (Serie, Titolo, ISBN...)")
            f_serie = f2.selectbox("Filtra Serie", ["Tutte"] + get_safe_options(df, 'serie'))
            f_editore = f3.selectbox("Filtra Editore", ["Tutti"] + get_safe_options(df, 'editore'))
            
            f4, f5, f6 = st.columns(3)
            f_box = f4.selectbox("Filtra Box", ["Tutti"] + get_safe_options(df, 'storage_box'))
            f_stato = f5.selectbox("Filtra Stato", ["Tutti"] + LISTA_STATO)
            f_formato = f6.selectbox("Filtra Formato", ["Tutti"] + LISTA_FORMATO)

        # Logica di filtraggio
        filt_df = df.copy()
        if search_text:
            filt_df = filt_df[filt_df.astype(str).apply(lambda r: search_text.lower() in r.str.lower().values, axis=1)]
        if f_serie != "Tutte": filt_df = filt_df[filt_df['serie'].astype(str) == f_serie]
        if f_editore != "Tutti": filt_df = filt_df[filt_df['editore'].astype(str) == f_editore]
        if f_box != "Tutti": filt_df = filt_df[filt_df['storage_box'].astype(str) == f_box]
        if f_stato != "Tutti": filt_df = filt_df[filt_df['stato'].astype(str) == f_stato]
        if f_formato != "Tutti": filt_df = filt_df[filt_df['formato'].astype(str) == f_formato]

        # Visualizzazione tabella estesa
        st.dataframe(
            filt_df[COLUMNS_ORDER], 
            use_container_width=True, 
            hide_index=True,
            height=3500  # Altezza per mostrare circa 100 righe
        )
    else:
        st.info("Database vuoto o non raggiungibile.")

# --- SEZIONE 2: STATISTICHE ---
elif menu == "📊 Statistiche":
    st.title("📊 Analisi Collezione")
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Top 10 Serie")
            st.bar_chart(df['serie'].value_counts().head(10))
        with c2:
            st.subheader("Stato Distribuzione")
            st.write(df['stato'].value_counts())
            
        st.divider()
        st.subheader("Riepilogo Editori")
        ed_stats = df.groupby('editore').size().reset_index(name='Albi')
        st.table(ed_stats.sort_values(by='Albi', ascending=False))
    else:
        st.warning("Nessun dato disponibile per generare statistiche.")

# --- SEZIONE 3: CONFIGURAZIONE ---
elif menu == "⚙️ Configurazione":
    st.title("⚙️ Gestione Sistema")
    st.info("App in modalità sola lettura sincronizzata con Google Sheets.")
    if st.button("🔄 Forza Aggiornamento Dati"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    csv = df.to_csv(index=False, sep=';').encode('utf-8')
    st.download_button("📥 Esporta Backup CSV", data=csv, file_name="collezione_fumetti.csv", mime="text/csv")
