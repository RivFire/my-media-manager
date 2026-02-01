import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Comic Manager Pro", page_icon="📖", layout="wide")

# --- 2. FUNZIONI DI UTILITÀ (Definite all'inizio per evitare NameError) ---
def format_it_comma(valore):
    """Formatta i numeri con la virgola italiana"""
    try:
        return "{:,.2f}".format(float(valore)).replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "0,00"

# --- 3. CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 14px !important; }
    h1 { font-size: 26px !important; color: #ff4b4b; }
    .stForm { border-radius: 10px; padding: 20px; border: 1px solid #ddd; }
    [data-testid="stMetricValue"] { font-size: 24px; color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. COSTANTI ---
COLUMNS_ORDER = [
    "serie", "subserie", "numero", "variante", "titolo", "editore", 
    "formato", "frequenza", "colore", "pagine", "prezzo_copertina", "valuta",
    "giorno_uscita", "mese_uscita", "anno_uscita", 
    "codice", "isbn", "stato", "storage_box", "note"
]
MESI_OPZIONI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]

# --- 5. CONNESSIONE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carica_dati():
    try:
        # Legge l'URL dai Secrets
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        data = conn.read(spreadsheet=url, ttl="0")
        # Se il foglio ha dati, assicuriamoci che le colonne siano quelle giuste
        if data.empty:
            return pd.DataFrame(columns=COLUMNS_ORDER)
        return data
    except Exception as e:
        st.error(f"Errore di connessione: {e}")
        return pd.DataFrame(columns=COLUMNS_ORDER)

df = carica_dati()

# --- 6. INTERFACCIA ---
st.sidebar.title("📖 Menu")
scelta = st.sidebar.radio("Vai a:", ["📚 Archivio", "➕ Aggiungi", "⚙️ Configurazione"])

if scelta == "📚 Archivio":
    st.title("📚 La mia Collezione")
    
    if not df.empty:
        # Calcolo Metriche
        temp_df = df.copy()
        temp_df['prezzo_copertina'] = pd.to_numeric(temp_df['prezzo_copertina'], errors='coerce').fillna(0)
        
        valore_tot = temp_df[temp_df['valuta'] == 'Euro']['prezzo_copertina'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Albi Totali", len(df))
        c2.metric("In Stock", len(df[df['stato'] == 'stock']))
        c3.metric("Valore stimato", f"€ {format_it_comma(valore_tot)}")
        
        st.divider()
        search = st.text_input("🔍 Cerca nel database...")
        if search:
            df = df[df.apply(lambda r: search.lower() in str(r).lower(), axis=1)]
        
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("Il database è vuoto. Vai su 'Aggiungi' per inserire il primo fumetto!")

elif scelta == "➕ Aggiungi":
    st.title("➕ Aggiungi Albo")
    
    with st.form("nuovo_albo"):
        # Sezione Serie dinamica
        serie_esistenti = sorted(df['serie'].dropna().unique().tolist()) if not df.empty else []
        
        col1, col2 = st.columns(2)
        s_sel = col1.selectbox("Serie esistente", ["-- NUOVA --"] + serie_esistenti)
        if s_sel == "-- NUOVA --":
            serie_final = col1.text_input("Inserisci nome nuova serie")
        else:
            serie_final = s_sel
            
        numero = col2.text_input("Numero")
        titolo = st.text_input("Titolo")
        
        # Campi minimi per test
        ca, cb, cc = st.columns(3)
        prezzo = ca.number_input("Prezzo", min_value=0.0, step=0.05)
        valuta = cb.selectbox("Valuta", ["Euro", "Lira"])
        stato = cc.selectbox("Stato", ["stock", "wish list"])
        
        note = st.text_area("Note")
        
        if st.form_submit_button("Salva nel Cloud"):
            if serie_final:
                # Creiamo un dizionario con TUTTE le colonne per evitare errori di formato
                nuovo_dato = {col: "" for col in COLUMNS_ORDER}
                nuovo_dato.update({
                    "serie": serie_final,
                    "numero": numero,
                    "titolo": titolo,
                    "prezzo_copertina": prezzo,
                    "valuta": valuta,
                    "stato": stato,
                    "note": note
                })
                
                new_df = pd.concat([df, pd.DataFrame([nuovo_dato])], ignore_index=True)
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=new_df)
                st.success("Salvato!")
                st.rerun()
            else:
                st.error("Manca il nome della serie!")

elif scelta == "⚙️ Configurazione":
    st.title("⚙️ Impostazioni")
    if st.button("Forza ricaricamento dati"):
        st.rerun()
