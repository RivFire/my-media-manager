import sqlite3
import pandas as pd
import streamlit as st
import io
import os
from datetime import datetime

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Comic Manager Pro", page_icon="📖", layout="wide")

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

DB_NAME = 'comics_pro.db'

# --- COSTANTI ---
MESI_OPZIONI = [
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"
]

OPZIONI_COLORE = ["B/N", "Colore"]
OPZIONI_VALUTA = ["Euro", "Lira"]

COLUMNS_ORDER = [
    "id", "serie", "subserie", "numero", "variante", "titolo", "editore", 
    "formato", "frequenza", "colore", "pagine", "prezzo_copertina", "valuta",
    "giorno_uscita", "mese_uscita", "anno_uscita", 
    "codice", "isbn", "stato", "storage_box", "note"
]

# --- FUNZIONI DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS comics
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  serie TEXT, subserie TEXT, numero INTEGER, variante TEXT, titolo TEXT, editore TEXT, 
                  prezzo_copertina REAL, valuta TEXT, 
                  giorno_uscita INTEGER, mese_uscita TEXT, anno_uscita INTEGER,
                  codice TEXT, isbn TEXT, note TEXT, stato TEXT, formato TEXT, storage_box TEXT,
                  frequenza TEXT, colore TEXT, pagine INTEGER)''')
    
    c.execute("PRAGMA table_info(comics)")
    columns = [column[1] for column in c.fetchall()]
    cols_to_check = ['stato', 'codice', 'isbn', 'note', 'formato', 'editore', 'variante', 'storage_box', 
                     'giorno_uscita', 'mese_uscita', 'frequenza', 'colore', 'pagine', 'valuta']
    for col in cols_to_check:
        if col not in columns:
            c.execute(f"ALTER TABLE comics ADD COLUMN {col} TEXT")
            
    c.execute('''CREATE TABLE IF NOT EXISTS series (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_serie TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS subseries 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_subserie TEXT, serie_id INTEGER,
                  FOREIGN KEY(serie_id) REFERENCES series(id))''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS list_options (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, valore TEXT, UNIQUE(tipo, valore))''')
    defaults = [('frequenza', 'Mensile'), ('frequenza', 'Bimestrale'), ('frequenza', 'Settimanale')]
    c.executemany("INSERT OR IGNORE INTO list_options (tipo, valore) VALUES (?,?)", defaults)
    
    conn.commit()
    conn.close()

def get_list_options(tipo):
    conn = sqlite3.connect(DB_NAME)
    res = pd.read_sql_query("SELECT valore FROM list_options WHERE tipo = ? ORDER BY valore", conn, params=(tipo,))
    conn.close()
    return res['valore'].tolist()

def update_db_from_editor(df_original, edited_dict):
    if not edited_dict or "edited_rows" not in edited_dict:
        return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        for row_idx, updated_values in edited_dict["edited_rows"].items():
            row_idx = int(row_idx)
            record_id = int(df_original.iloc[row_idx]['id'])
            for column, value in updated_values.items():
                c.execute(f"UPDATE comics SET {column} = ? WHERE id = ?", (value, record_id))
        conn.commit()
    except Exception as e:
        st.error(f"Errore durante il salvataggio: {e}")
    finally:
        conn.close()

def format_it_comma(valore):
    try: return "{:,.2f}".format(float(valore)).replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return "0,00"

def get_subseries_list(serie_nome):
    conn = sqlite3.connect(DB_NAME)
    query = "SELECT nome_subserie FROM subseries JOIN series ON subseries.serie_id = series.id WHERE series.nome_serie = ? ORDER BY nome_subserie"
    df = pd.read_sql_query(query, conn, params=(serie_nome,))
    conn.close()
    return df['nome_subserie'].tolist()

def import_csv_logic(uploaded_file):
    logs = []
    summary = {"added": 0, "updated": 0, "skipped": 0}
    try:
        raw_data = uploaded_file.read()
        content = None
        for enc in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
            try:
                content = raw_data.decode(enc)
                break
            except: continue
        
        if content is None:
            return False, 0, 0, ["Impossibile leggere il file: errore di codifica."]
        
        first_line = content.splitlines()[0]
        sep = ';' if ';' in first_line else ','
        
        df_import = pd.read_csv(io.StringIO(content), sep=sep, dtype=str).fillna("")
        df_import.columns = [str(c).lower().strip().replace(' ', '_') for c in df_import.columns]
        
        if 'serie' not in df_import.columns:
            return False, 0, 0, [f"Errore: Colonna 'serie' mancante. Colonne trovate: {list(df_import.columns)}"]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        for index, row in df_import.iterrows():
            line_num = index + 2
            serie = str(row.get('serie', "")).strip()
            
            if not serie or serie.lower() == "nan": 
                logs.append(f"❌ Riga {line_num}: Saltata (Serie vuota).")
                summary["skipped"] += 1
                continue
                
            try:
                try: num_val = int(float(str(row.get('numero', '0')).replace(',', '.')))
                except: num_val = 0
                
                variante = str(row.get('variante', "")).strip()
                codice = str(row.get('codice', "")).strip()
                subserie = str(row.get('subserie', "Nessuna")).strip()
                titolo = str(row.get('titolo', "")).strip()
                
                c.execute("""SELECT id FROM comics WHERE LOWER(serie)=LOWER(?) AND numero=? AND LOWER(variante)=LOWER(?) AND LOWER(codice)=LOWER(?) AND LOWER(subserie)=LOWER(?) AND LOWER(titolo)=LOWER(?)""", 
                          (serie, num_val, variante, codice, subserie, titolo))
                existing = c.fetchone()
                
                editore = str(row.get('editore', "")).strip()
                formato = str(row.get('formato', "")).strip()
                frequenza = str(row.get('frequenza', "Mensile")).strip()
                colore = str(row.get('colore', "B/N")).strip()
                valuta = str(row.get('valuta', "Euro")).strip()
                
                try: pagine = int(float(str(row.get('pagine', '0')).replace(',', '.')))
                except: pagine = 0
                
                stato = str(row.get('stato', "stock")).strip().lower()
                box = str(row.get('storage_box', "")).strip()
                note = str(row.get('note', "")).strip()
                isbn = str(row.get('isbn', "")).strip()
                mese = str(row.get('mese_uscita', "gennaio")).strip().lower()
                
                try: prezzo = float(str(row.get('prezzo_copertina', '0')).replace(',', '.'))
                except: prezzo = 0.0
                try: giorno = int(float(str(row.get('giorno_uscita', '0'))))
                except: giorno = 0
                try: anno = int(float(str(row.get('anno_uscita', '2025'))))
                except: anno = 2025

                if existing:
                    c.execute("""UPDATE comics SET editore=?, formato=?, frequenza=?, colore=?, pagine=?, prezzo_copertina=?, valuta=?, giorno_uscita=?, mese_uscita=?, anno_uscita=?, isbn=?, note=?, stato=?, storage_box=? WHERE id=?""", 
                              (editore, formato, frequenza, colore, pagine, prezzo, valuta, giorno, mese, anno, isbn, note, stato, box, existing[0]))
                    summary["updated"] += 1
                    logs.append(f"🔄 Riga {line_num}: Aggiornato '{serie} n.{num_val}'")
                else:
                    c.execute("""INSERT INTO comics (serie, subserie, numero, variante, titolo, editore, formato, frequenza, colore, pagine, prezzo_copertina, valuta, giorno_uscita, mese_uscita, anno_uscita, codice, isbn, stato, storage_box, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
                              (serie, subserie, num_val, variante, titolo, editore, formato, frequenza, colore, pagine, prezzo, valuta, giorno, mese, anno, codice, isbn, stato, box, note))
                    summary["added"] += 1
                    logs.append(f"✅ Riga {line_num}: Aggiunto '{serie} n.{num_val}'")
            except Exception as e_row:
                logs.append(f"⚠️ Riga {line_num}: Errore -> {str(e_row)}")
        
        conn.commit()
        conn.close()
        return True, summary["added"], summary["updated"], logs
    except Exception as e: 
        return False, 0, 0, [f"Errore critico: {str(e)}"]

init_db()

scelta = st.sidebar.radio("Vai a:", ["📚 Archivio", "📊 Statistiche", "➕ Aggiungi", "✏️ Modifica", "⚙️ Configurazione"])

# --- 1. ARCHIVIO ---
if scelta == "📚 Archivio":
    st.title("📚 Archivio Fumetti")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(f"SELECT {', '.join(COLUMNS_ORDER)} FROM comics", conn)
    conn.close()

    if not df.empty:
        df['numero'] = pd.to_numeric(df['numero'], errors='coerce').fillna(0).astype('Int64')
        df['anno_uscita'] = pd.to_numeric(df['anno_uscita'], errors='coerce').fillna(2025).astype('Int64')
        df['pagine'] = pd.to_numeric(df['pagine'], errors='coerce').fillna(0).astype('Int64')
        df['giorno_uscita'] = pd.to_numeric(df['giorno_uscita'], errors='coerce').fillna(0).astype('Int64')
        
        df = df.sort_values(by=['serie', 'subserie', 'numero'], ascending=[True, True, True])

        tot_albi = len(df)
        in_stock = len(df[df['stato'] == 'stock'])
        percentuale_stock = (in_stock / tot_albi * 100) if tot_albi > 0 else 0
        valore_euro = df[df['valuta'] == 'Euro']['prezzo_copertina'].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Totale Albi", tot_albi)
        m2.metric("In Stock", in_stock)
        m3.metric("% Completamento", f"{percentuale_stock:.1f}%")
        m4.metric("Valore Totale", f"€ {format_it_comma(valore_euro)}")
        
        st.markdown("---")
        with st.expander("🔍 Filtri Avanzati", expanded=True):
            r1c1, r1c2, r1c3, r1c4 = st.columns(4)
            f_search = r1c1.text_input("Cerca testo...")
            f_serie = r1c2.selectbox("Serie", ["Tutte"] + sorted(df['serie'].unique().tolist()))
            sub_opts = ["Tutte"]
            if f_serie != "Tutte": sub_opts += sorted(df[df['serie'] == f_serie]['subserie'].unique().tolist())
            else: sub_opts += sorted(df['subserie'].unique().tolist())
            f_sub = r1c3.selectbox("Sub-serie", sub_opts)
            f_form = r1c4.selectbox("Formato", ["Tutti"] + sorted([f for f in df['formato'].unique() if f]))

            r2c1, r2c2, r2c3, r2c4 = st.columns(4)
            f_stat = r2c1.selectbox("Stato", ["Tutti", "stock", "wish list"])
            f_box = r2c2.selectbox("Storage Box", ["Tutti"] + sorted([b for b in df['storage_box'].unique() if b]))
            f_valuta = r2c3.selectbox("Valuta", ["Tutte"] + OPZIONI_VALUTA)
            f_mese = r2c4.selectbox("Mese", ["Tutti"] + MESI_OPZIONI)

            r3c1, r3c2, r3c3, r3c4 = st.columns(4)
            f_anno = r3c1.selectbox("Anno", ["Tutti"] + sorted([int(a) for a in df['anno_uscita'].dropna().unique()], reverse=True))
            f_freq = r3c2.selectbox("Frequenza", ["Tutte"] + sorted([x for x in df['frequenza'].unique() if x]))
            f_col = r3c3.selectbox("Colore", ["Tutti"] + OPZIONI_COLORE)
            pagine_presenti = sorted([int(p) for p in df['pagine'].dropna().unique()])
            f_pag = r3c4.selectbox("Pagine", ["Tutte"] + [str(p) for p in pagine_presenti])

        filt_df = df.copy().reset_index(drop=True)
        if f_search: filt_df = filt_df[filt_df.apply(lambda row: f_search.lower() in str(row).lower(), axis=1)]
        if f_serie != "Tutte": filt_df = filt_df[filt_df['serie'] == f_serie]
        if f_sub != "Tutte": filt_df = filt_df[filt_df['subserie'] == f_sub]
        if f_form != "Tutti": filt_df = filt_df[filt_df['formato'] == f_form]
        if f_stat != "Tutti": filt_df = filt_df[filt_df['stato'] == f_stat]
        if f_box != "Tutti": filt_df = filt_df[filt_df['storage_box'] == f_box]
        if f_valuta != "Tutte": filt_df = filt_df[filt_df['valuta'] == f_valuta]
        if f_mese != "Tutti": filt_df = filt_df[filt_df['mese_uscita'] == f_mese]
        if f_anno != "Tutti": filt_df = filt_df[filt_df['anno_uscita'] == int(f_anno)]
        if f_freq != "Tutte": filt_df = filt_df[filt_df['frequenza'] == f_freq]
        if f_col != "Tutti": filt_df = filt_df[filt_df['colore'] == f_col]
        if f_pag != "Tutte": filt_df = filt_df[filt_df['pagine'] == int(f_pag)]
        
        edited_data = st.data_editor(
            filt_df, use_container_width=True, hide_index=True, height=600, key="archivio_editor",
            column_config={
                "id": st.column_config.Column("ID", width="small", disabled=True),
                "numero": st.column_config.NumberColumn("N.", format="%d"),
                "anno_uscita": st.column_config.NumberColumn("Anno", format="%d"),
                "giorno_uscita": st.column_config.NumberColumn("Gg", format="%d"),
                "pagine": st.column_config.NumberColumn("Pagine", format="%d"),
                "prezzo_copertina": st.column_config.NumberColumn("Prezzo", format="%.2f"),
                "valuta": st.column_config.SelectboxColumn("Valuta", options=OPZIONI_VALUTA),
                "frequenza": st.column_config.SelectboxColumn("Frequenza", options=get_list_options('frequenza')),
                "colore": st.column_config.SelectboxColumn("Colore", options=OPZIONI_COLORE),
                "mese_uscita": st.column_config.SelectboxColumn("Mese", options=MESI_OPZIONI),
                "stato": st.column_config.SelectboxColumn("Stato", options=["stock", "wish list"]),
            }
        )

        if st.session_state["archivio_editor"]["edited_rows"]:
            update_db_from_editor(filt_df, st.session_state["archivio_editor"])
            st.toast("✅ Database aggiornato!")
            st.rerun()
    else: st.info("Archivio vuoto.")

# --- 2. STATISTICHE ---
elif scelta == "📊 Statistiche":
    st.title("📊 Statistiche Collezione")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT serie, subserie, stato FROM comics", conn)
    conn.close()

    if not df.empty:
        # --- TABELLA PER SERIE ---
        st.subheader("📚 Riepilogo per Serie")
        stats_serie = df.groupby('serie').agg(
            Totale_Albi=('serie', 'count'),
            In_Stock=('stato', lambda x: (x == 'stock').sum())
        ).reset_index()
        stats_serie['%_Completamento'] = (stats_serie['In_Stock'] / stats_serie['Totale_Albi'] * 100).round(1).astype(str) + '%'
        st.dataframe(stats_serie.sort_values(by='Totale_Albi', ascending=False), use_container_width=True, hide_index=True)

        st.markdown("---")

        # --- TABELLA PER SOTTOSERIE ---
        st.subheader("📑 Dettaglio per Sottoserie")
        stats_sub = df.groupby(['serie', 'subserie']).agg(
            Totale_Albi=('subserie', 'count'),
            In_Stock=('stato', lambda x: (x == 'stock').sum())
        ).reset_index()
        stats_sub['%_Completamento'] = (stats_sub['In_Stock'] / stats_sub['Totale_Albi'] * 100).round(1).astype(str) + '%'
        st.dataframe(stats_sub.sort_values(by=['serie', 'Totale_Albi'], ascending=[True, False]), use_container_width=True, hide_index=True)
    else:
        st.info("Nessun dato disponibile per le statistiche.")

# --- 3. AGGIUNGI ---
elif scelta == "➕ Aggiungi":
    st.title("➕ Aggiungi Nuovo Albo")
    conn = sqlite3.connect(DB_NAME); df_s = pd.read_sql_query("SELECT nome_serie FROM series ORDER BY nome_serie", conn); conn.close()
    if df_s.empty: st.warning("Crea prima una Serie in Configurazione!")
    else:
        with st.form("add_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            s_sel = c1.selectbox("Serie", df_s['nome_serie'].tolist())
            sub_sel = c2.selectbox("Sub-Serie", ["Nessuna"] + get_subseries_list(s_sel))
            box_in = c3.text_input("Storage Box")
            tit_in = st.text_input("Titolo")
            ca, cb, cc, cd = st.columns(4)
            n_in = ca.number_input("Numero", step=1, value=1); v_in = cb.text_input("Variante"); ed_in = cc.text_input("Editore"); form_in = cd.text_input("Formato")
            
            cx, cy, cz, cw = st.columns(4)
            freq_in = cx.selectbox("Frequenza", get_list_options('frequenza'))
            col_in = cy.selectbox("Colore", OPZIONI_COLORE)
            pag_in = cz.number_input("Pagine", min_value=0, step=1, value=96)
            val_in = cw.selectbox("Valuta", OPZIONI_VALUTA)

            ce, cf, cg, ch = st.columns(4)
            g_in = ce.number_input("Giorno", 0, 31, 0); m_in = cf.selectbox("Mese", MESI_OPZIONI); a_in = cg.number_input("Anno", 1900, 2100, 2025); pr_in = ch.number_input("Prezzo", step=0.01)
            ci, cl, cm = st.columns(3)
            cod_in = ci.text_input("Codice"); isbn_in = cl.text_input("ISBN"); st_in = cm.selectbox("Stato", ["stock", "wish list"])
            note_in = st.text_area("Note")
            if st.form_submit_button("🚀 Salva"):
                conn = sqlite3.connect(DB_NAME); c = conn.cursor()
                c.execute("""INSERT INTO comics (serie, subserie, numero, variante, titolo, editore, formato, frequenza, colore, pagine, prezzo_copertina, valuta, giorno_uscita, mese_uscita, anno_uscita, codice, isbn, stato, storage_box, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (s_sel, sub_sel, int(n_in), v_in, tit_in, ed_in, form_in, freq_in, col_in, int(pag_in), pr_in, val_in, int(g_in), m_in, int(a_in), cod_in, isbn_in, st_in, box_in, note_in))
                conn.commit(); conn.close(); st.success("Aggiunto!"); st.rerun()

# --- 4. MODIFICA ---
elif scelta == "✏️ Modifica":
    st.title("🗑️ Rimozione Record Singolo")
    id_del = st.number_input("Inserisci ID Record da eliminare", min_value=1, step=1)
    if st.button("🗑️ Elimina Definitivamente"):
        conn = sqlite3.connect(DB_NAME); c = conn.cursor()
        c.execute("DELETE FROM comics WHERE id=?", (id_del,))
        conn.commit(); conn.close(); st.success("Record rimosso."); st.rerun()

# --- 5. CONFIGURAZIONE ---
elif scelta == "⚙️ Configurazione":
    st.title("⚙️ Configurazione e Manutenzione")
    
    st.subheader("💾 Gestione Database (Backup e Ripristino)")
    c_bak1, c_bak2 = st.columns(2)
    with c_bak1:
        if os.path.exists(DB_NAME):
            with open(DB_NAME, "rb") as f:
                st.download_button(label="📥 Scarica Backup Database (.db)", data=f, file_name=f"comics_backup.db", mime="application/x-sqlite3")
    with c_bak2:
        restore_file = st.file_uploader("Carica un file .db per ripristinare", type=['db'])
        if restore_file is not None and st.button("🔄 Ripristina ora"):
            with open(DB_NAME, "wb") as f: f.write(restore_file.getbuffer())
            st.rerun()

    st.markdown("---")
    st.subheader("📦 Import/Export CSV")
    c_imp1, c_imp2 = st.columns(2)
    with c_imp1:
        df_mod = pd.DataFrame(columns=COLUMNS_ORDER[1:])
        st.download_button("📥 Scarica Modello CSV", df_mod.to_csv(index=False, sep=';').encode('utf-8'), "modello.csv", "text/csv")
    with c_imp2:
        f_up = st.file_uploader("Carica file CSV", type=['csv'])
        if f_up and st.button("🚀 Avvia Import"):
            ok, n_add, n_up, log_entries = import_csv_logic(f_up)
            if ok: 
                st.success(f"Fatto! Aggiunti: {n_add} | Aggiornati: {n_up}")
                with st.expander("📄 Log Operazioni (Verifica qui i tuoi record)", expanded=True):
                    for entry in log_entries:
                        if "✅" in entry: st.write(entry)
                        elif "🔄" in entry: st.info(entry)
                        else: st.error(entry)
            else:
                st.error("Errore fatale")
                for e in log_entries: st.error(e)

    st.markdown("---")
    st.subheader("🧹 Pulizia Dati")
    conn = sqlite3.connect(DB_NAME); df_data = pd.read_sql_query("SELECT DISTINCT serie, subserie FROM comics", conn); conn.close()
    if not df_data.empty:
        col_del1, col_del2 = st.columns(2)
        with col_del1:
            s_to_clean = st.selectbox("Svuota Serie (tutti i fumetti):", ["-"] + sorted(df_data['serie'].unique().tolist()))
            confirm_s = st.text_input("Scrivi 'ELIMINA' per confermare (Serie):", key="conf_s")
            if s_to_clean != "-" and confirm_s == "ELIMINA" and st.button(f"🚨 ELIMINA RECORD SERIE: {s_to_clean}"):
                conn = sqlite3.connect(DB_NAME); c = conn.cursor(); c.execute("DELETE FROM comics WHERE serie=?", (s_to_clean,)); conn.commit(); conn.close(); st.rerun()
        with col_del2:
            s_ref = st.selectbox("Scegli Serie per vedere sottoserie:", ["-"] + sorted(df_data['serie'].unique().tolist()), key="ref_sub_clean")
            if s_ref != "-":
                sub_available = sorted(df_data[df_data['serie'] == s_ref]['subserie'].unique().tolist())
                sub_to_clean = st.selectbox("Svuota Sottoserie:", ["-"] + sub_available)
                confirm_sub = st.text_input("Scrivi 'ELIMINA' per confermare (Sottoserie):", key="conf_sub")
                if sub_to_clean != "-" and confirm_sub == "ELIMINA" and st.button(f"🚨 ELIMINA RECORD SOTTOSERIE: {sub_to_clean}"):
                    conn = sqlite3.connect(DB_NAME); c = conn.cursor(); c.execute("DELETE FROM comics WHERE serie=? AND subserie=?", (s_ref, sub_to_clean)); conn.commit(); conn.close(); st.rerun()

    st.markdown("---")
    st.subheader("🛠️ Gestione Liste e Menu")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 📚 Serie e Sottoserie")
        conn = sqlite3.connect(DB_NAME); df_series = pd.read_sql_query("SELECT id, nome_serie FROM series ORDER BY nome_serie", conn); conn.close()
        ns = st.text_input("Aggiungi Serie")
        if st.button("Aggiungi Serie"):
            conn = sqlite3.connect(DB_NAME); c = conn.cursor()
            try: c.execute("INSERT INTO series (nome_serie) VALUES (?)", (ns,)); conn.commit()
            except: st.error("Esiste già")
            conn.close(); st.rerun()
        s_target = st.selectbox("Seleziona Serie per Sottoserie:", ["-"] + df_series['nome_serie'].tolist())
        if s_target != "-":
            nss = st.text_input("Aggiungi Sottoserie")
            if st.button("Aggiungi Sottoserie"):
                conn = sqlite3.connect(DB_NAME); c = conn.cursor()
                s_id = df_series[df_series['nome_serie'] == s_target]['id'].values[0]
                c.execute("INSERT INTO subseries (nome_subserie, serie_id) VALUES (?,?)", (nss, s_id)); conn.commit(); conn.close(); st.rerun()
    
    with c2:
        st.markdown("#### ⏳ Frequenza")
        f_add = st.text_input("Nuova Frequenza")
        if st.button("Salva Frequenza"):
            conn = sqlite3.connect(DB_NAME); c = conn.cursor(); c.execute("INSERT OR IGNORE INTO list_options (tipo, valore) VALUES ('frequenza', ?)", (f_add,)); conn.commit(); conn.close(); st.rerun()

    st.markdown("---")
    if st.button("🚨 RESET TOTALE DATABASE"):
        if os.path.exists(DB_NAME): os.remove(DB_NAME); st.rerun()