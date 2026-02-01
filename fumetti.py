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
    # Prendiamo i valori unici, convertiamoli in stringa e rimuoviamo i nulli/vuoti
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

LISTA_MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
LISTA_FORMATO = ["Brossurato", "Cartonato", "Spillato", "Pocket", "Graphic Novel", "Albo", "Altro"]
LISTA_FREQUENZA = ["Mensile", "Bimestrale", "Settimanale", "Quindicinale", "Trimestrale", "Semestrale", "Annuale", "Aperta", "Unico"]
LISTA_COLORE = ["B/N", "Colore", "Misto"]
LISTA_VALUTA = ["Euro", "Lira"]
LISTA_STATO = ["stock", "wish list"]

# --- 4. CSS ---
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 14px !important; }
    h1 { font-size: 28px !important; color: #ff4b4b; font-weight: bold; }
    .stForm { border-radius: 12px; padding: 25px; border: 1px solid #eee; background-color: #fcfcfc; }
    [data-testid="stMetricValue"] { font-size: 24px; color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- 5. CONNESSIONE ---
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
menu = st.sidebar.radio("Vai a:", ["📚 Archivio", "📊 Statistiche", "⚙️ Configurazione"])

# --- SEZIONE 1: ARCHIVIO ---
if menu == "📚 Archivio":
    st.title("📚 La mia Collezione")
    
    if not df.empty:
        df_calc = df.copy()
        df_calc['prezzo_copertina'] = pd.to_numeric(df_calc['prezzo_copertina'], errors='coerce').fillna(0)
        val_tot = df_calc[df_calc['valuta'] == 'Euro']['prezzo_copertina'].sum()

        m1, m2, m3 = st.columns(3)
        m1.metric("Albi Totali", len(df))
        m2.metric("In Stock", len(df[df['stato'].astype(str).str.lower() == 'stock']))
        m3.metric("Valore (Euro)", f"€ {format_it_comma(val_tot)}")

        st.divider()
        
        with st.expander("🔍 Filtri Avanzati", expanded=True):
            f1, f2, f3 = st.columns(3)
            search_text = f1.text_input("Cerca testo")
            f_serie = f2.selectbox("Filtra Serie", ["Tutte"] + get_safe_options(df, 'serie'))
            f_editore = f3.selectbox("Filtra Editore", ["Tutti"] + get_safe_options(df, 'editore'))
            
            f4, f5, f6 = st.columns(3)
            f_box = f4.selectbox("Filtra Box", ["Tutti"] + get_safe_options(df, 'storage_box'))
            f_stato = f5.selectbox("Filtra Stato", ["Tutti"] + LISTA_STATO)
            f_formato = f6.selectbox("Filtra Formato", ["Tutti"] + LISTA_FORMATO)

        filt_df = df.copy()
        if search_text:
            filt_df = filt_df[filt_df.astype(str).apply(lambda r: search_text.lower() in r.str.lower().values, axis=1)]
        if f_serie != "Tutte": filt_df = filt_df[filt_df['serie'].astype(str) == f_serie]
        if f_editore != "Tutti": filt_df = filt_df[filt_df['editore'].astype(str) == f_editore]
        if f_box != "Tutti": filt_df = filt_df[filt_df['storage_box'].astype(str) == f_box]
        if f_stato != "Tutti": filt_df = filt_df[filt_df['stato'].astype(str) == f_stato]
        if f_formato != "Tutti": filt_df = filt_df[filt_df['formato'].astype(str) == f_formato]

        st.dataframe(
            filt_df[COLUMNS_ORDER], 
            use_container_width=True, 
            hide_index=True,
            height=3500  # Altezza in pixel sufficiente per circa 100 righe
        )

# --- SEZIONE 2: STATISTICHE ---
elif menu == "📊 Statistiche":
    st.title("📊 Analisi")
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Top 10 Serie")
            st.bar_chart(df['serie'].value_counts().head(10))
        with c2:
            st.subheader("Stato")
            st.write(df['stato'].value_counts())
    else:
        st.warning("Dati insufficienti.")

# --- SEZIONE 3: AGGIUNGI ---
elif menu == "➕ Aggiungi":
    st.title("➕ Inserimento")
    
    with st.form("form_full", clear_on_submit=True):
        st.subheader("1. Testata")
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        
        s_o = get_safe_options(df, 'serie')
        s_s = r1c1.selectbox("Serie", ["-- NUOVA --"] + s_o)
        s_f = r1c1.text_input("Nome Serie") if s_s == "-- NUOVA --" else s_s
        
        ss_o = get_safe_options(df, 'subserie')
        ss_s = r1c2.selectbox("Sub-serie", ["-- NESSUNA --"] + ss_o)
        ss_f = r1c2.text_input("Nome Sub-serie") if ss_s == "-- NESSUNA --" else ss_s
        
        n_o = get_safe_options(df, 'numero')
        n_s = r1c3.selectbox("Numero", ["-- NUOVO --"] + n_o)
        n_f = r1c3.text_input("Inserisci N.") if n_s == "-- NUOVO --" else n_s
        
        v_o = get_safe_options(df, 'variante')
        v_s = r1c4.selectbox("Variante", ["-- NESSUNA --"] + v_o)
        v_f = r1c4.text_input("Specifica Var.") if v_s == "-- NESSUNA --" else v_s

        st.subheader("2. Dati Albo")
        r2c1, r2c2 = st.columns([2, 1])
        t_o = get_safe_options(df, 'titolo')
        t_s = r2c1.selectbox("Titolo", ["-- NUOVO --"] + t_o)
        t_f = r2c1.text_input("Titolo") if t_s == "-- NUOVO --" else t_s
        
        e_o = get_safe_options(df, 'editore')
        e_s = r2c2.selectbox("Editore", ["-- NUOVO --"] + e_o)
        e_f = r2c2.text_input("Editore") if e_s == "-- NUOVO --" else e_s

        st.divider()
        r3c1, r3c2, r3c3, r3c4 = st.columns(4)
        form_f = r3c1.selectbox("Formato", LISTA_FORMATO)
        freq_f = r3c2.selectbox("Frequenza", LISTA_FREQUENZA)
        col_f = r3c3.selectbox("Colore", LISTA_COLORE)
        p_o = get_safe_options(df, 'pagine')
        p_s = r3c4.selectbox("Pagine", ["-- NUOVO --"] + p_o)
        p_f = r3c4.text_input("Pagine", value="96") if p_s == "-- NUOVO --" else p_s

        r4c1, r4c2, r4c3, r4c4 = st.columns(4)
        prez_f = r4c1.number_input("Prezzo", step=0.01)
        val_f = r4c2.selectbox("Valuta", LISTA_VALUTA)
        stat_f = r4c3.selectbox("Stato", LISTA_STATO)
        b_o = get_safe_options(df, 'storage_box')
        b_s = r4c4.selectbox("Box", ["-- NUOVO --"] + b_o)
        b_f = r4c4.text_input("Nome Box") if b_s == "-- NUOVO --" else b_s

        st.subheader("3. Extra")
        r5c1, r5c2, r5c3 = st.columns(3)
        gg_f = r5c1.selectbox("Giorno", [str(x) for x in range(32)])
        mm_f = r5c2.selectbox("Mese", LISTA_MESI)
        aa_f = r5c3.selectbox("Anno", [str(x) for x in range(1940, 2027)][::-1])

        c_int = st.text_input("Codice Interno")
        isbn_f = st.text_input("ISBN")
        note_f = st.text_area("Note")

        if st.form_submit_button("🚀 SALVA"):
            if s_f:
                nuovo = {
                    "serie": s_f, "subserie": ss_f, "numero": n_f, "variante": v_f,
                    "titolo": t_f, "editore": e_f, "formato": form_f, "frequenza": freq_f,
                    "colore": col_f, "pagine": p_f, "prezzo_copertina": prez_f, "valuta": val_f,
                    "giorno_uscita": gg_f, "mese_uscita": mm_f, "anno_uscita": aa_f,
                    "codice": c_int, "isbn": isbn_f, "stato": stat_f, "storage_box": b_f, "note": note_f
                }
                up_df = pd.concat([df, pd.DataFrame([nuovo])], ignore_index=True)
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=up_df)
                st.success("Salvato!")
                st.rerun()

# --- SEZIONE 4: CONFIGURAZIONE ---
elif menu == "⚙️ Configurazione":
    st.title("⚙️ Sistema")
    if st.button("🔄 Sincronizza ora"):
        st.cache_data.clear()
        st.rerun()
    csv = df.to_csv(index=False, sep=';').encode('utf-8')
    st.download_button("📥 Esporta CSV", data=csv, file_name="collezione.csv")
