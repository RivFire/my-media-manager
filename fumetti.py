import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Comic Manager Cloud", page_icon="📖", layout="wide")

# --- CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 14px !important; }
    h1 { font-size: 26px !important; color: #ff4b4b; }
    .stForm { border-radius: 10px; padding: 20px; border: 1px solid #ddd; }
    [data-testid="stMetricValue"] { font-size: 24px; color: #ff4b4b; }
    .main .block-container { max-width: 98%; padding-top: 1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- COSTANTI ---
MESI_OPZIONI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
OPZIONI_COLORE = ["B/N", "Colore"]
OPZIONI_VALUTA = ["Euro", "Lira"]
OPZIONI_STATO = ["stock", "wish list"]

COLUMNS_ORDER = [
    "serie", "subserie", "numero", "variante", "titolo", "editore", 
    "formato", "frequenza", "colore", "pagine", "prezzo_copertina", "valuta",
    "giorno_uscita", "mese_uscita", "anno_uscita", 
    "codice", "isbn", "stato", "storage_box", "note"
]

# --- CONNESSIONE GOOGLE SHEETS ---
# Sostituisci con il tuo URL reale tra le virgolette
URL_FOGLIO = "https://docs.google.com/spreadsheets/d/1bci2M_wzvtIyZrDUbioV5FI9RI8AU3vFuhuJ8wdJPgU/edit?gid=2016998487#gid=2016998487"

conn = st.connection("gsheets", type=GSheetsConnection)

def carica_dati():
    try:
        # Carica i dati forzando il refresh (ttl=0)
        return conn.read(spreadsheet=URL_FOGLIO, ttl="0")
    except:
        return pd.DataFrame(columns=COLUMNS_ORDER)

def format_it_comma(valore):
    try: return "{:,.2f}".format(float(valore)).replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "0,00"

# --- LOGICA APPLICATIVA ---
df = carica_dati()
scelta = st.sidebar.radio("Vai a:", ["📚 Archivio", "📊 Statistiche", "➕ Aggiungi", "⚙️ Configurazione"])

# --- 1. ARCHIVIO ---
if scelta == "📚 Archivio":
    st.title("📚 Archivio Fumetti")
    if not df.empty:
        # Conversione tipi per metriche
        df_met = df.copy()
        df_met['prezzo_copertina'] = pd.to_numeric(df_met['prezzo_copertina'], errors='coerce').fillna(0)
        
        tot_albi = len(df)
        in_stock = len(df[df['stato'] == 'stock'])
        percentuale_stock = (in_stock / tot_albi * 100) if tot_albi > 0 else 0
        valore_euro = df_met[df_met['valuta'] == 'Euro']['prezzo_copertina'].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Totale Albi", tot_albi)
        m2.metric("In Stock", in_stock)
        m3.metric("% Completamento", f"{percentuale_stock:.1f}%")
        m4.metric("Valore Totale", f"€ {format_it_comma(valore_euro)}")
        
        st.markdown("---")
        f_search = st.text_input("🔍 Cerca testo (Serie, Titolo, ISBN, Box...):")
        
        filt_df = df.copy()
        if f_search:
            filt_df = filt_df[filt_df.apply(lambda r: f_search.lower() in str(r).lower(), axis=1)]
        
        st.dataframe(filt_df, use_container_width=True, hide_index=True)
    else:
        st.info("Nessun dato trovato sul foglio Google.")

# --- 2. STATISTICHE ---
elif scelta == "📊 Statistiche":
    st.title("📊 Statistiche Collezione")
    if not df.empty:
        st.subheader("Riepilogo per Serie")
        stats_serie = df.groupby('serie').agg(
            Totale_Albi=('serie', 'count'),
            In_Stock=('stato', lambda x: (x == 'stock').sum())
        ).reset_index()
        stats_serie['%'] = (stats_serie['In_Stock'] / stats_serie['Totale_Albi'] * 100).round(1).astype(str) + '%'
        st.dataframe(stats_serie.sort_values(by='Totale_Albi', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("Aggiungi dati per vedere le statistiche.")

# --- 3. AGGIUNGI ---
elif scelta == "➕ Aggiungi":
    st.title("➕ Aggiungi Nuovo Albo")
    with st.form("add_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        serie_in = c1.text_input("Serie")
        sub_in = c2.text_input("Sub-serie")
        num_in = c3.text_input("Numero")
        var_in = c4.text_input("Variante")
        
        tit_in = st.text_input("Titolo")
        
        ca, cb, cc, cd = st.columns(4)
        ed_in = ca.text_input("Editore")
        form_in = cb.text_input("Formato")
        freq_in = cc.selectbox("Frequenza", ["Mensile", "Bimestrale", "Settimanale", "Quindicinale", "Unico"])
        col_in = cd.selectbox("Colore", OPZIONI_COLORE)
        
        cx, cy, cz, cw = st.columns(4)
        pag_in = cx.number_input("Pagine", step=1, value=96)
        val_in = cy.selectbox("Valuta", OPZIONI_VALUTA)
        pr_in = cz.number_input("Prezzo", step=0.01)
        st_in = cw.selectbox("Stato", OPZIONI_STATO)

        ce, cf, cg, ch = st.columns(4)
        g_in = ce.number_input("Giorno", 0, 31, 0)
        m_in = cf.selectbox("Mese", MESI_OPZIONI)
        a_in = cg.number_input("Anno", 1900, 2100, 2025)
        box_in = ch.text_input("Storage Box")
        
        ci, cl = st.columns(2)
        cod_in = ci.text_input("Codice")
        isbn_in = cl.text_input("ISBN")
        
        note_in = st.text_area("Note")
        
        if st.form_submit_button("🚀 Salva nel Cloud"):
            if serie_in:
                nuova_riga = pd.DataFrame([{
                    "serie": serie_in, "subserie": sub_in, "numero": num_in, "variante": var_in,
                    "titolo": tit_in, "editore": ed_in, "formato": form_in, "frequenza": freq_in,
                    "colore": col_in, "pagine": pag_in, "prezzo_copertina": pr_in, "valuta": val_in,
                    "giorno_uscita": g_in, "mese_uscita": m_in, "anno_uscita": a_in,
                    "codice": cod_in, "isbn": isbn_in, "stato": st_in, "storage_box": box_in, "note": note_in
                }])
                df_aggiornato = pd.concat([df, nuova_riga], ignore_index=True)
                conn.update(spreadsheet=URL_FOGLIO, data=df_aggiornato)
                st.success("✅ Salvato correttamente su Google Sheets!")
                st.rerun()
            else:
                st.error("Inserisci almeno la Serie!")

# --- 4. CONFIGURAZIONE ---
elif scelta == "⚙️ Configurazione":
    st.title("⚙️ Manutenzione")
    st.subheader("Esporta Dati")
    st.download_button("Scarica Collezione (CSV)", df.to_csv(index=False, sep=';').encode('utf-8'), "fumetti.csv", "text/csv")
    
    st.divider()
    st.subheader("Azioni Pericolose")
    del_confirm = st.text_input("Scrivi 'CANCELLA' per svuotare l'archivio")
    if st.button("Svuota tutto il foglio Google"):
        if del_confirm == "CANCELLA":
            df_empty = pd.DataFrame(columns=COLUMNS_ORDER)
            conn.update(spreadsheet=URL_FOGLIO, data=df_empty)
            st.success("Archivio svuotato con successo.")
            st.rerun()