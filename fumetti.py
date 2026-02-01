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

# --- 3. COSTANTI E OPZIONI MENU ---
COLUMNS_ORDER = [
    "serie", "subserie", "numero", "variante", "titolo", "editore", 
    "formato", "frequenza", "colore", "pagine", "prezzo_copertina", "valuta",
    "giorno_uscita", "mese_uscita", "anno_uscita", 
    "codice", "isbn", "stato", "storage_box", "note"
]

LISTA_MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
LISTA_FORMATO = ["Brossurato", "Cartonato", "Spillato", "Pocket", "Graphic Novel", "Altro"]
LISTA_FREQUENZA = ["Mensile", "Bimestrale", "Settimanale", "Quindicinale", "Trimestrale", "Aperta", "Unico"]
LISTA_COLORE = ["B/N", "Colore", "Misto"]
LISTA_VALUTA = ["Euro", "Lira"]
LISTA_STATO = ["stock", "wish list"]

# --- 4. CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 14px !important; }
    h1 { font-size: 28px !important; color: #ff4b4b; font-weight: bold; }
    .stForm { border-radius: 12px; padding: 25px; border: 1px solid #eee; background-color: #fcfcfc; }
    [data-testid="stMetricValue"] { font-size: 26px; color: #ff4b4b; }
    .stDataFrame { border: 1px solid #eee; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. CONNESSIONE E CARICAMENTO ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carica_dati():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        data = conn.read(spreadsheet=url, ttl="0")
        if data.empty:
            return pd.DataFrame(columns=COLUMNS_ORDER)
        # Assicuriamoci che tutte le colonne esistano
        for col in COLUMNS_ORDER:
            if col not in data.columns:
                data[col] = ""
        return data
    except Exception as e:
        st.error(f"Errore di sincronizzazione: {e}")
        return pd.DataFrame(columns=COLUMNS_ORDER)

df = carica_dati()

# --- 6. SIDEBAR ---
st.sidebar.header("📖 Navigation")
menu = st.sidebar.radio("Scegli sezione:", ["📚 Archivio", "📊 Statistiche", "➕ Aggiungi", "⚙️ Configurazione"])

# --- SEZIONE 1: ARCHIVIO ---
if menu == "📚 Archivio":
    st.title("📚 La mia Collezione")
    
    if not df.empty:
        # Metriche veloci
        df_c = df.copy()
        df_c['prezzo_copertina'] = pd.to_numeric(df_c['prezzo_copertina'], errors='coerce').fillna(0)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Albi in totale", len(df))
        m2.metric("Disponibili (Stock)", len(df[df['stato'] == 'stock']))
        val_euro = df_c[df_c['valuta'] == 'Euro']['prezzo_copertina'].sum()
        m3.metric("Valore Collezione", f"€ {format_it_comma(val_euro)}")

        st.divider()
        
        # Ricerca e Filtri
        c_search, c_box = st.columns([2, 1])
        f_search = c_search.text_input("🔍 Cerca per Serie, Titolo o ISBN...")
        boxes = ["Tutti"] + sorted(df['storage_box'].dropna().unique().tolist())
        f_box = c_box.selectbox("📦 Filtra per Box", boxes)

        filt_df = df.copy()
        if f_search:
            filt_df = filt_df[filt_df.apply(lambda r: f_search.lower() in str(r).lower(), axis=1)]
        if f_box != "Tutti":
            filt_df = filt_df[filt_df['storage_box'] == f_box]

        st.dataframe(filt_df[COLUMNS_ORDER], use_container_width=True, hide_index=True)
    else:
        st.info("L'archivio è vuoto. Inizia aggiungendo un fumetto!")

# --- SEZIONE 2: STATISTICHE ---
elif menu == "📊 Statistiche":
    st.title("📊 Analisi Dati")
    if not df.empty:
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("Top 10 Serie per numero albi")
            top_series = df['serie'].value_counts().head(10)
            st.bar_chart(top_series)

        with col_right:
            st.subheader("Distribuzione Stato")
            stato_count = df['stato'].value_counts()
            st.write(stato_count)
            
        st.divider()
        st.subheader("Dettaglio per Editore")
        editore_stats = df.groupby('editore').size().reset_index(name='Conteggio')
        st.table(editore_stats.sort_values(by='Conteggio', ascending=False))
    else:
        st.warning("Nessun dato disponibile per le statistiche.")

# --- SEZIONE 3: AGGIUNGI (IL CUORE DELL'APP) ---
elif menu == "➕ Aggiungi":
    st.title("➕ Inserimento Nuovo Albo")
    
    # Liste dinamiche
    serie_list = sorted(df['serie'].dropna().unique().tolist()) if not df.empty else []
    box_list = sorted(df['storage_box'].dropna().unique().tolist()) if not df.empty else []
    editore_list = sorted(df['editore'].dropna().unique().tolist()) if not df.empty else []

    with st.form("form_aggiunta", clear_on_submit=True):
        st.subheader("📌 Informazioni Base")
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        
        # Serie Dinamica
        s_sel = r1c1.selectbox("Serie esistente", ["-- NUOVA SERIE --"] + serie_list)
        if s_sel == "-- NUOVA SERIE --":
            s_fin = r1c1.text_input("Nome Nuova Serie")
        else:
            s_fin = s_sel
            
        sub_in = r1c2.text_input("Sub-serie")
        num_in = r1c3.text_input("Numero")
        var_in = r1c4.text_input("Variante")
        
        tit_in = st.text_input("Titolo Albo")

        st.divider()
        st.subheader("📄 Dettagli Tecnici")
        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        
        # Editore Dinamico
        e_sel = r2c1.selectbox("Editore esistente", ["-- NUOVO --"] + editore_list)
        if e_sel == "-- NUOVO --":
            e_fin = r2c1.text_input("Nome Editore")
        else:
            e_fin = e_sel
            
        form_in = r2c2.selectbox("Formato", LISTA_FORMATO)
        freq_in = r2c3.selectbox("Frequenza", LISTA_FREQUENZA)
        col_in = r2c4.radio("Colore", LISTA_COLORE, horizontal=True)

        r3c1, r3c2, r3c3, r3c4 = st.columns(4)
        pag_in = r3c1.number_input("Pagine", min_value=0, value=96)
        prez_in = r3c2.number_input("Prezzo", min_value=0.0, step=0.01)
        val_in = r3c3.selectbox("Valuta", LISTA_VALUTA)
        stat_in = r3c4.selectbox("Stato", LISTA_STATO)

        st.divider()
        st.subheader("📅 Uscita e Logistica")
        r4c1, r4c2, r4c3, r4c4 = st.columns(4)
        gg_in = r4c1.number_input("Giorno", 0, 31, 0)
        mm_in = r4c2.selectbox("Mese", LISTA_MESI)
        aa_in = r4c3.number_input("Anno", 1900, 2100, 2026)
        
        # Box Dinamico
        b_sel = r4c4.selectbox("Storage Box", ["-- NUOVO BOX --"] + box_list)
        if b_sel == "-- NUOVO BOX --":
            b_fin = r4c4.text_input("ID Box")
        else:
            b_fin = b_sel

        r5c1, r5c2 = st.columns(2)
        cod_in = r5c1.text_input("Codice Interno")
        isbn_in = r5c2.text_input("ISBN")
        
        note_in = st.text_area("Note e Condizioni")

        submit = st.form_submit_button("🚀 SALVA NEL CLOUD")

        if submit:
            if s_fin:
                nuovo_row = {
                    "serie": s_fin, "subserie": sub_in, "numero": num_in, "variante": var_in,
                    "titolo": tit_in, "editore": e_fin, "formato": form_in, "frequenza": freq_in,
                    "colore": col_in, "pagine": int(pag_in), "prezzo_copertina": prez_in, "valuta": val_in,
                    "giorno_uscita": int(gg_in), "mese_uscita": mm_in, "anno_uscita": int(aa_in),
                    "codice": cod_in, "isbn": isbn_in, "stato": stat_in, "storage_box": b_fin, "note": note_in
                }
                
                updated_df = pd.concat([df, pd.DataFrame([nuovo_row])], ignore_index=True)
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=updated_df)
                st.success(f"Albo di {s_fin} salvato con successo!")
                st.balloons()
                st.rerun()
            else:
                st.error("Il campo 'Serie' è obbligatorio!")

# --- SEZIONE 4: CONFIGURAZIONE ---
elif menu == "⚙️ Configurazione":
    st.title("⚙️ Gestione Sistema")
    st.write("Versione Cloud 2.0 - Sincronizzato con Google Sheets")
    
    if st.button("🔄 Forza Refresh Dati"):
        st.cache_data.clear()
        st.rerun()
        
    st.divider()
    csv = df.to_csv(index=False, sep=';').encode('utf-8')
    st.download_button("📥 Scarica Backup CSV", data=csv, file_name="backup_fumetti.csv", mime="text/csv")
