import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Comic Manager Full Dropdown", page_icon="📖", layout="wide")

# --- 2. FUNZIONI DI UTILITÀ ---
def format_it_comma(valore):
    try:
        return "{:,.2f}".format(float(valore)).replace(',', 'X').replace('.', ',').replace('X', '.')
    except:
        return "0,00"

# --- 3. COSTANTI E OPZIONI FISSE ---
COLUMNS_ORDER = [
    "serie", "subserie", "numero", "variante", "titolo", "editore", 
    "formato", "frequenza", "colore", "pagine", "prezzo_copertina", "valuta",
    "giorno_uscita", "mese_uscita", "anno_uscita", 
    "codice", "isbn", "stato", "storage_box", "note"
]

LISTA_MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
LISTA_FORMATO = ["Brossurato", "Cartonato", "Spillato", "Pocket", "Graphic Novel", "Altro"]
LISTA_FREQUENZA = ["Mensile", "Bimestrale", "Settimanale", "Quindicinale", "Trimestrale", "Semestrale", "Annuale", "Aperta", "Unico"]
LISTA_COLORE = ["B/N", "Colore", "Misto"]
LISTA_VALUTA = ["Euro", "Lira"]
LISTA_STATO = ["stock", "wish list"]

# --- 4. CONNESSIONE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def carica_dati():
    try:
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        data = conn.read(spreadsheet=url, ttl="0")
        if data.empty:
            return pd.DataFrame(columns=COLUMNS_ORDER)
        return data
    except Exception as e:
        st.error(f"Errore: {e}")
        return pd.DataFrame(columns=COLUMNS_ORDER)

df = carica_dati()

# --- 5. INTERFACCIA ---
st.sidebar.title("📖 Gestione Fumetti")
menu = st.sidebar.radio("Naviga:", ["📚 Archivio", "📊 Statistiche", "➕ Aggiungi"])

# --- SEZIONE AGGIUNGI (TUTTI MENU A TENDINA) ---
if menu == "➕ Aggiungi":
    st.title("➕ Nuovo Inserimento")
    st.info("Usa i menu a tendina. Se un valore non esiste, seleziona '-- NUOVO --'.")

    # Estrazione liste dinamiche dai dati esistenti
    def get_options(column):
        return sorted(df[column].dropna().unique().tolist()) if not df.empty else []

    with st.form("form_completo", clear_on_submit=True):
        # --- RIGA 1: TESTATA ---
        st.subheader("1. Identificazione")
        c1, c2, c3, c4 = st.columns(4)
        
        # 1. SERIE
        s_opt = get_options("serie")
        s_sel = c1.selectbox("Serie", ["-- NUOVO --"] + s_opt)
        serie_f = c1.text_input("Scrivi nuova Serie") if s_sel == "-- NUOVO --" else s_sel

        # 2. SUBSERIE
        ss_opt = get_options("subserie")
        ss_sel = c2.selectbox("Sub-serie", ["-- NESSUNA/NUOVA --"] + ss_opt)
        sub_f = c2.text_input("Scrivi nuova Sub-serie") if ss_sel == "-- NESSUNA/NUOVA --" else ss_sel

        # 3. NUMERO
        n_opt = get_options("numero")
        n_sel = c3.selectbox("Numero", ["-- NUOVO --"] + n_opt)
        num_f = c3.text_input("Inserisci Numero") if n_sel == "-- NUOVO --" else n_sel

        # 4. VARIANTE
        v_opt = get_options("variante")
        v_sel = c4.selectbox("Variante", ["-- NESSUNA/NUOVA --"] + v_opt)
        var_f = c4.text_input("Specifica Variante") if v_sel == "-- NESSUNA/NUOVA --" else v_sel

        # --- RIGA 2: TITOLO ED EDITORE ---
        c5, c6 = st.columns([2, 1])
        t_opt = get_options("titolo")
        t_sel = c5.selectbox("Titolo Albo (Cerca esistente)", ["-- NUOVO --"] + t_opt)
        tit_f = c5.text_input("Inserisci Titolo") if t_sel == "-- NUOVO --" else t_sel

        e_opt = get_options("editore")
        e_sel = c6.selectbox("Editore", ["-- NUOVO --"] + e_opt)
        ed_f = c6.text_input("Scrivi Editore") if e_sel == "-- NUOVO --" else e_sel

        st.divider()

        # --- RIGA 3: TECNICA ---
        st.subheader("2. Caratteristiche Tecniche")
        c7, c8, c9, c10 = st.columns(4)
        form_f = c7.selectbox("Formato", LISTA_FORMATO)
        freq_f = c8.selectbox("Frequenza", LISTA_FREQUENZA)
        col_f = c9.selectbox("Colore", LISTA_COLORE)
        
        p_opt = [str(x) for x in sorted(pd.to_numeric(df['pagine'], errors='coerce').dropna().unique().astype(int).tolist())]
        p_sel = c10.selectbox("Pagine", ["-- NUOVO --"] + p_opt)
        pag_f = c10.text_input("Num. Pagine", value="96") if p_sel == "-- NUOVO --" else p_sel

        # --- RIGA 4: ECONOMIA ---
        c11, c12, c13, c14 = st.columns(4)
        prez_f = c11.number_input("Prezzo Copertina", step=0.01, format="%.2f")
        val_f = c12.selectbox("Valuta", LISTA_VALUTA)
        stat_f = c13.selectbox("Stato", LISTA_STATO)
        
        box_opt = get_options("storage_box")
        box_sel = c14.selectbox("Storage Box", ["-- NUOVO --"] + box_opt)
        box_f = c14.text_input("ID Box") if box_sel == "-- NUOVO --" else box_sel

        st.divider()

        # --- RIGA 5: DATE E CODICI ---
        st.subheader("3. Pubblicazione e Codici")
        c15, c16, c17 = st.columns(3)
        gg_f = c15.selectbox("Giorno Uscita", [str(x) for x in range(32)])
        mm_f = c16.selectbox("Mese Uscita", LISTA_MESI)
        aa_f = c17.selectbox("Anno Uscita", [str(x) for x in range(1940, 2027)][::-1])

        c18, c19 = st.columns(2)
        cod_f = c18.text_input("Codice Interno")
        isbn_f = c19.text_input("ISBN")

        note_f = st.text_area("Note")

        # BOTTONE SALVATAGGIO
        if st.form_submit_button("💾 SALVA NEL DATABASE"):
            if serie_f and num_f:
                nuovo_albo = {
                    "serie": serie_f, "subserie": sub_f, "numero": num_f, "variante": var_f,
                    "titolo": tit_f, "editore": ed_f, "formato": form_f, "frequenza": freq_f,
                    "colore": col_f, "pagine": pag_f, "prezzo_copertina": prez_f, "valuta": val_f,
                    "giorno_uscita": gg_f, "mese_uscita": mm_f, "anno_uscita": aa_f,
                    "codice": cod_f, "isbn": isbn_f, "stato": stat_f, "storage_box": box_f, "note": note_f
                }
                
                new_df = pd.concat([df, pd.DataFrame([nuovo_albo])], ignore_index=True)
                conn.update(spreadsheet=st.secrets["connections"]["gsheets"]["spreadsheet"], data=new_df)
                st.success("✅ Salvato!")
                st.rerun()
            else:
                st.error("⚠️ Serie e Numero sono obbligatori!")

# --- SEZIONE ARCHIVIO ---
elif menu == "📚 Archivio":
    st.title("📚 Archivio")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Database vuoto.")

# --- SEZIONE STATISTICHE ---
elif menu == "📊 Statistiche":
    st.title("📊 Statistiche")
    if not df.empty:
        st.bar_chart(df['serie'].value_counts())
        st.divider()
        st.write("Distribuzione per Stato:")
        st.pie_chart(df['stato'].value_counts())
