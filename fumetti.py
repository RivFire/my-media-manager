import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Comic Manager Pro Cloud", 
    page_icon="📖", 
    layout="wide"
)

# --- 2. CSS PERSONALIZZATO (Stile Originale) ---
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 14px !important; }
    h1 { font-size: 26px !important; color: #ff4b4b; }
    .stForm { border-radius: 10px; padding: 20px; border: 1px solid #ddd; }
    [data-testid="stMetricValue"] { font-size: 24px; color: #ff4b4b; }
    .main .block-container { max-width: 98%; padding-top: 1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. COSTANTI E OPZIONI ---
MESI_OPZIONI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
OPZIONI_COLORE = ["B/N", "Colore", "Misto"]
OPZIONI_VALUTA = ["Euro", "Lira"]
OPZIONI_STATO = ["stock", "wish list"]
OPZIONI_FREQUENZA = ["Mensile", "Bimestrale", "Settimanale", "Quindicinale", "Trimestrale", "Aperta", "Unico"]
OPZIONI_FORMATO = ["Brossurato", "Cartonato", "Spillato", "Pocket", "Graphic Novel", "Altro"]

COLUMNS_ORDER = [
    "serie", "subserie", "numero", "variante", "titolo", "editore", 
    "formato", "frequenza", "colore", "pagine", "prezzo_copertina", "valuta",
    "giorno_uscita", "mese_uscita", "anno_uscita", 
    "codice", "isbn", "stato", "storage_box", "note"
]

# --- 4. CONNESSIONE GOOGLE SHEETS ---
# La connessione usa l'URL definito nei "Secrets" di Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

def carica_dati():
    try:
        # ttl=0 assicura che i dati siano sempre freschi ad ogni refresh
        return conn.read(ttl="0")
    except Exception:
        # Ritorna un DataFrame vuoto se il foglio è nuovo/non raggiungibile
        return pd.DataFrame(columns=COLUMNS_ORDER)

def format_it_comma(valore):
    try: return "{:,.2f}".format(float(valore)).replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "0,00"

# Caricamento dati iniziale
df = carica_dati()

# --- 5. SIDEBAR NAVIGAZIONE ---
st.sidebar.title("📖 Comic Manager")
scelta = st.sidebar.radio("Vai a:", ["📚 Archivio", "📊 Statistiche", "➕ Aggiungi", "⚙️ Configurazione"])

# --- SEZIONE 1: ARCHIVIO ---
if scelta == "📚 Archivio":
    st.title("📚 Archivio Fumetti")
    
    if not df.empty:
        # Metriche in alto
        df_calc = df.copy()
        df_calc['prezzo_copertina'] = pd.to_numeric(df_calc['prezzo_copertina'], errors='coerce').fillna(0)
        
        tot_albi = len(df)
        in_stock = len(df[df['stato'] == 'stock'])
        valore_euro = df_calc[df_calc['valuta'] == 'Euro']['prezzo_copertina'].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("Totale Albi", tot_albi)
        m2.metric("In Stock", in_stock)
        m3.metric("Valore Totale", f"€ {format_it_comma(valore_euro)}")
        
        st.markdown("---")
        
        # Filtri Avanzati
        with st.expander("🔍 Filtri e Ricerca", expanded=False):
            c_f1, c_f2, c_f3 = st.columns(3)
            f_search = c_f1.text_input("Cerca testo libero")
            f_serie = c_f2.selectbox("Filtra per Serie", ["Tutte"] + sorted(df['serie'].dropna().unique().tolist()))
            f_box = c_f3.selectbox("Storage Box", ["Tutte"] + sorted(df['storage_box'].dropna().unique().tolist()))

        # Applicazione Filtri
        filt_df = df.copy()
        if f_search:
            filt_df = filt_df[filt_df.apply(lambda r: f_search.lower() in str(r).lower(), axis=1)]
        if f_serie != "Tutte":
            filt_df = filt_df[filt_df['serie'] == f_serie]
        if f_box != "Tutte":
            filt_df = filt_df[filt_df['storage_box'] == f_box]

        st.dataframe(filt_df, use_container_width=True, hide_index=True)
    else:
        st.info("Il database su Google Sheets è attualmente vuoto.")

# --- SEZIONE 2: STATISTICHE ---
elif scelta == "📊 Statistiche":
    st.title("📊 Statistiche Collezione")
    if not df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Top 10 Serie")
            stats_serie = df.groupby('serie').size().reset_index(name='Albi').sort_values(by='Albi', ascending=False).head(10)
            st.bar_chart(stats_serie.set_index('serie'))
            
        with col2:
            st.subheader("Distribuzione Stato")
            stats_stato = df.groupby('stato').size()
            st.write(stats_stato)
            
        st.divider()
        st.subheader("Riepilogo Sottoserie")
        stats_sub = df.groupby(['serie', 'subserie']).size().reset_index(name='Totale')
        st.dataframe(stats_sub, use_container_width=True, hide_index=True)
    else:
        st.warning("Dati insufficienti per generare statistiche.")

# --- SEZIONE 3: AGGIUNGI (Con Menu Dinamici) ---
elif scelta == "➕ Aggiungi":
    st.title("➕ Nuovo Albo")
    
    # Liste dinamiche basate sui dati già inseriti
    serie_esistenti = sorted(df['serie'].dropna().unique().tolist()) if not df.empty else []
    box_esistenti = sorted(df['storage_box'].dropna().unique().tolist()) if not df.empty else []

    with st.form("form_aggiunta", clear_on_submit=True):
        st.subheader("1. Testata e Numerazione")
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        
        # Logica Serie: Selectbox + possibilità di nuovo inserimento
        serie_sel = r1c1.selectbox("Serie (Esistente)", ["-- NUOVA SERIE --"] + serie_esistenti)
        if serie_sel == "-- NUOVA SERIE --":
            serie_final = r1c1.text_input("Scrivi Nome Nuova Serie")
        else:
            serie_final = serie_sel
            
        sub_in = r1c2.text_input("Sub-serie")
        num_in = r1c3.text_input("Numero")
        var_in = r1c4.text_input("Variante")
        
        titolo_in = st.text_input("Titolo dell'albo")

        st.divider()
        st.subheader("2. Dettagli Pubblicazione")
        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        editore_in = r2c1.text_input("Editore")
        formato_in = r2c2.selectbox("Formato", OPZIONI_FORMATO)
        freq_in = r2c3.selectbox("Frequenza", OPZIONI_FREQUENZA)
        colore_in = r2c4.radio("Colore", OPZIONI_COLORE, horizontal=True)

        r3c1, r3c2, r3c3, r3c4 = st.columns(4)
        pag_in = r3c1.number_input("Pagine", min_value=0, value=96)
        prezzo_in = r3c2.number_input("Prezzo Copertina", min_value=0.0, step=0.01)
        valuta_in = r3c3.selectbox("Valuta", OPZIONI_VALUTA)
        stato_in = r3c4.selectbox("Stato", OPZIONI_STATO)

        st.divider()
        st.subheader("3. Logistica e Date")
        r4c1, r4c2, r4c3, r4c4 = st.columns(4)
        g_uscita = r4c1.number_input("Giorno", 0, 31, 0)
        m_uscita = r4c2.selectbox("Mese", MESI_OPZIONI)
        a_uscita = r4c3.number_input("Anno", 1900, 2100, 2026)
        
        box_sel = r4c4.selectbox("Storage Box (Esistente)", ["-- NUOVO BOX --"] + box_esistenti)
        if box_sel == "-- NUOVO BOX --":
            box_final = r4c4.text_input("Nome Nuovo Box")
        else:
            box_final = box_sel

        r5c1, r5c2 = st.columns(2)
        cod_in = r5c1.text_input("Codice Interno")
        isbn_in = r5c2.text_input("ISBN")
        
        note_in = st.text_area("Note aggiuntive")

        # Pulsante di Invio
        salva = st.form_submit_button("🚀 SALVA NEL DATABASE CLOUD")

        if salva:
            if serie_final and (num_in or titolo_in):
                nuovo_record = {
                    "serie": serie_final, "subserie": sub_in, "numero": num_in, "variante": var_in,
                    "titolo": titolo_in, "editore": editore_in, "formato": formato_in, "frequenza": freq_in,
                    "colore": colore_in, "pagine": int(pag_in), "prezzo_copertina": prezzo_in, "valuta": valuta_in,
                    "giorno_uscita": int(g_uscita), "mese_uscita": m_uscita, "anno_uscita": int(a_uscita),
                    "codice": cod_in, "isbn": isbn_in, "stato": stato_in, "storage_box": box_final, "note": note_in
                }
                
                # Aggiunta al DataFrame e invio al Cloud
                df_nuovo = pd.concat([df, pd.DataFrame([nuovo_record])], ignore_index=True)
                conn.update(data=df_nuovo)
                
                st.success(f"✅ '{serie_final}' salvato correttamente!")
                st.balloons()
                st.rerun()
            else:
                st.error("⚠️ Errore: Inserisci almeno la Serie e il Numero/Titolo.")

# --- SEZIONE 4: CONFIGURAZIONE ---
elif scelta == "⚙️ Configurazione":
    st.title("⚙️ Gestione e Backup")
    
    st.info("Il database è sincronizzato in tempo reale su Google Drive.")
    
    st.subheader("📥 Export Dati")
    csv = df.to_csv(index=False, sep=';').encode('utf-8')
    st.download_button(
        label="Scarica Collezione in CSV",
        data=csv,
        file_name=f"backup_fumetti_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
    
    st.divider()
    st.subheader("🚨 Pulizia")
    confirm = st.text_input("Per svuotare il database cloud, scrivi 'CANCELLA TUTTO'")
    if st.button("Elimina tutti i dati"):
        if confirm == "CANCELLA TUTTO":
            df_empty = pd.DataFrame(columns=COLUMNS_ORDER)
            conn.update(data=df_empty)
            st.success("Database svuotato correttamente.")
            st.rerun()
