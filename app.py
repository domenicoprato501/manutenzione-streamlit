import sqlite3
from datetime import date
import streamlit as st

# ==========================================
# 1. CONFIGURAZIONE PAGINA
# ==========================================
st.set_page_config(
    page_title="Gestione Manutenzioni & Ricambi",
    page_icon="🛠️",
    layout="wide"
)

DB_FILE = "gestione_manutenzioni.db"

# ==========================================
# 2. INIZIALIZZAZIONE DATABASE (SQLite)
# ==========================================
def init_db():
    """Inizializza le tabelle SQLite se non esistono già"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Tabella Catalogo Ricambi
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ricambi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            prezzo_default REAL DEFAULT 0.0
        )
    """)

    # Tabella Manutenzioni principali
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS manutenzioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descrizione TEXT NOT NULL,
            data_intervento TEXT NOT NULL,
            totale_costo REAL DEFAULT 0.0
        )
    """)

    # Tabella Relazione Manutenzione <-> Ricambi (Molti a Molti)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS manutenzione_ricambi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manutenzione_id INTEGER NOT NULL,
            ricambio_id INTEGER,
            nome_custom TEXT,
            quantita REAL NOT NULL,
            prezzo_unitario REAL NOT NULL,
            totale_riga REAL NOT NULL,
            FOREIGN KEY (manutenzione_id) REFERENCES manutenzioni(id) ON DELETE CASCADE,
            FOREIGN KEY (ricambio_id) REFERENCES ricambi(id)
        )
    """)

    # Inserimento dati di esempio nel catalogo ricambi (se vuoto)
    cursor.execute("SELECT COUNT(*) FROM ricambi")
    if cursor.fetchone()[0] == 0:
        ricambi_iniziali = [
            ("Filtro Olio", 15.00),
            ("Olio Motore 5W30 (Litri)", 12.50),
            ("Filtro Aria", 22.00),
            ("Pastiglie Freno Anteriori", 45.00),
            ("Liquido Refrigerante (Litri)", 8.00)
        ]
        cursor.executemany("INSERT INTO ricambi (nome, prezzo_default) VALUES (?, ?)", ricambi_iniziali)

    conn.commit()
    conn.close()

init_db()

# ==========================================
# 3. FUNZIONI HELPER DATABASE
# ==========================================
def get_catalogo_ricambi():
    """Recupera il catalogo dei ricambi dal database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, prezzo_default FROM ricambi ORDER BY nome ASC")
    rows = cursor.fetchall()
    conn.close()

    catalogo = {"-- Seleziona o scrivi a mano --": {"id": None, "prezzo": 0.0}}
    for row in rows:
        catalogo[row[1]] = {"id": row[0], "prezzo": row[2]}
    return catalogo

def salva_manutenzione_db(descrizione, data_str, totale_costo, lista_ricambi):
    """Salva la manutenzione e tutti i relativi ricambi nel database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Inserisce l'intervento principale
    cursor.execute(
        "INSERT INTO manutenzioni (descrizione, data_intervento, totale_costo) VALUES (?, ?, ?)",
        (descrizione, data_str, totale_costo)
    )
    manutenzione_id = cursor.lastrowid

    # Inserisce tutti i ricambi associati a questa manutenzione
    for r in lista_ricambi:
        cursor.execute("""
            INSERT INTO manutenzione_ricambi 
            (manutenzione_id, ricambio_id, nome_custom, quantita, prezzo_unitario, totale_riga)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            manutenzione_id,
            r["ricambio_id"],
            r["nome_custom"],
            r["quantita"],
            r["prezzo_unitario"],
            r["totale_riga"]
        ))

    conn.commit()
    conn.close()

def get_storico_manutenzioni():
    """Recupera la lista di tutte le manutenzioni salvate con i relativi ricambi"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, descrizione, data_intervento, totale_costo FROM manutenzioni ORDER BY id DESC")
    manutenzioni = cursor.fetchall()

    risultato = []
    for m in manutenzioni:
        m_id, desc, dt, tot = m
        cursor.execute("""
            SELECT mr.nome_custom, r.nome, mr.quantita, mr.prezzo_unitario, mr.totale_riga
            FROM manutenzione_ricambi mr
            LEFT JOIN ricambi r ON mr.ricambio_id = r.id
            WHERE mr.manutenzione_id = ?
        """, (m_id,))
        ricambi_rows = cursor.fetchall()
        
        dettaglio_ricambi = []
        for r_row in ricambi_rows:
            nome_effettivo = r_row[1] if r_row[1] else r_row[0]
            dettaglio_ricambi.append({
                "nome": nome_effettivo,
                "quantita": r_row[2],
                "prezzo_unitario": r_row[3],
                "totale_riga": r_row[4]
            })

        risultato.append({
            "id": m_id,
            "descrizione": desc,
            "data": dt,
            "totale": tot,
            "ricambi": dettaglio_ricambi
        })

    conn.close()
    return risultato

# ==========================================
# 4. GESTIONE STATO STREAMLIT (Session State)
# ==========================================
if "ricambi_manutenzione" not in st.session_state:
    st.session_state.ricambi_manutenzione = [
        {"ricambio_scelto": "-- Seleziona o scrivi a mano --", "nome_custom": "", "quantita": 1.0, "prezzo": 0.0}
    ]

def aggiungi_riga():
    st.session_state.ricambi_manutenzione.append(
        {"ricambio_scelto": "-- Seleziona o scrivi a mano --", "nome_custom": "", "quantita": 1.0, "prezzo": 0.0}
    )

def rimuovi_riga(index):
    if len(st.session_state.ricambi_manutenzione) > 1:
        st.session_state.ricambi_manutenzione.pop(index)
    else:
        st.warning("Devi inserire almeno un ricambio.")

def reset_form():
    st.session_state.ricambi_manutenzione = [
        {"ricambio_scelto": "-- Seleziona o scrivi a mano --", "nome_custom": "", "quantita": 1.0, "prezzo": 0.0}
    ]

# ==========================================
# 5. INTERFACCIA UTENTE (UI)
# ==========================================
st.title("🛠️ Gestione Manutenzioni e Ricambi")

tab1, tab2 = st.tabs(["➕ Nuova Manutenzione", "📜 Cronologia Interventi"])

# --- TAB 1: FORM NUOVA MANUTENZIONE ---
with tab1:
    CATALOGO_RICAMBI = get_catalogo_ricambi()
    opzioni_catalogo = list(CATALOGO_RICAMBI.keys())

    with st.form("form_manutenzione", clear_on_submit=False):
        st.subheader("Dettagli Intervento")
        col_desc, col_data = st.columns([3, 1])
        descrizione = col_desc.text_input("Descrizione Manutenzione *", placeholder="Es. Tagliando dei 100.000 km")
        data_intervento = col_data.date_input("Data Intervento", value=date.today())

        st.markdown("---")
        st.subheader("📦 Ricambi Utilizzati")

        totale_manutenzione = 0.0

        # Rendering dinamico delle righe dei ricambi
        for i, item in enumerate(st.session_state.ricambi_manutenzione):
            cols = st.columns([3, 3, 2, 2, 2, 1])

            # 1. Selezione da catalogo
            scelta = cols[0].selectbox(
                "Ricambio da Catalogo",
                options=opzioni_catalogo,
                index=opzioni_catalogo.index(item["ricambio_scelto"]) if item["ricambio_scelto"] in opzioni_catalogo else 0,
                key=f"scelta_{i}"
            )
            item["ricambio_scelto"] = scelta

            # Imposta prezzo di default dal catalogo se è stato selezionato un ricambio
            prezzo_default = CATALOGO_RICAMBI[scelta]["prezzo"] if scelta != "-- Seleziona o scrivi a mano --" else item["prezzo"]

            # 2. Inserimento manuale se non in catalogo
            is_custom = (scelta == "-- Seleziona o scrivi a mano --")
            item["nome_custom"] = cols[1].text_input(
                "O scrivi manualmente",
                value=item["nome_custom"],
                disabled=not is_custom,
                placeholder="Nome ricambio...",
                key=f"custom_{i}"
            )

            # 3. Quantità
            item["quantita"] = cols[2].number_input(
                "Quantità",
                min_value=0.1,
                value=float(item["quantita"]),
                step=0.5,
                key=f"qta_{i}"
            )

            # 4. Prezzo Unitario
            item["prezzo"] = cols[3].number_input(
                "Prezzo Unit. (€)",
                min_value=0.0,
                value=float(prezzo_default),
                step=0.5,
                key=f"prezzo_{i}"
            )

            # 5. Totale Riga (calcolo automatico)
            totale_riga = round(item["quantita"] * item["prezzo"], 2)
            cols[4].metric("Totale Riga", f"{totale_riga:.2f} €")
            totale_manutenzione += totale_riga

            # 6. Pulsante Elimina Riga
            cols[5].write("")
            cols[5].write("")
            cols[5].form_submit_button("🗑️", on_click=rimuovi_riga, args=(i,))

        # Pulsante (+) per aggiungere una nuova riga ricambio
        st.form_submit_button("➕ Aggiungi altro ricambio", on_click=aggiungi_riga)

        st.markdown("---")

        # Totale Generale e Invio
        col_totale, col_salva = st.columns([2, 1])
        col_totale.markdown(f"### 💰 **Totale Manutenzione: {totale_manutenzione:.2f} €**")

        invia = col_salva.form_submit_button("💾 Salva Manutenzione", type="primary")

    # Gestione dell'invio del form
    if invia:
        if not descrizione.strip():
            st.error("⚠️ La descrizione della manutenzione è obbligatoria.")
        else:
            ricambi_validi = []
            for r in st.session_state.ricambi_manutenzione:
                scelta = r["ricambio_scelto"]
                nome_custom = r["nome_custom"].strip()

                if scelta != "-- Seleziona o scrivi a mano --":
                    ricambi_validi.append({
                        "ricambio_id": CATALOGO_RICAMBI[scelta]["id"],
                        "nome_custom": None,
                        "quantita": r["quantita"],
                        "prezzo_unitario": r["prezzo"],
                        "totale_riga": round(r["quantita"] * r["prezzo"], 2)
                    })
                elif nome_custom:
                    ricambi_validi.append({
                        "ricambio_id": None,
                        "nome_custom": nome_custom,
                        "quantita": r["quantita"],
                        "prezzo_unitario": r["prezzo"],
                        "totale_riga": round(r["quantita"] * r["prezzo"], 2)
                    })

            if not ricambi_validi:
                st.error("⚠️ Inserisci almeno un ricambio valido (selezionato da catalogo o con nome inserito a mano).")
            else:
                salva_manutenzione_db(
                    descrizione=descrizione,
                    data_str=str(data_intervento),
                    totale_costo=round(totale_manutenzione, 2),
                    lista_ricambi=ricambi_validi
                )
                st.success("✅ Manutenzione salvata con successo nel database!")
                reset_form()
                st.rerun()

# --- TAB 2: CRONOLOGIA MANUTENZIONI SALVATE ---
with tab2:
    st.subheader("📜 Storico Manutenzioni Effettuate")
    storico = get_storico_manutenzioni()

    if not storico:
        st.info("Nessuna manutenzione registrata al momento.")
    else:
        for m in storico:
            with st.expander(f"🛠️ **{m['descrizione']}** — {m['data']} | **Totale: {m['totale']:.2f} €**"):
                st.write("**Ricambi utilizzati:**")
                
                # Tabella riassuntiva dei ricambi per questa manutenzione
                dati_tabella = []
                for r in m["ricambi"]:
                    dati_tabella.append({
                        "Ricambio": r["nome"],
                        "Quantità": r["quantita"],
                        "Prezzo Unitario (€)": f"{r['prezzo_unitario']:.2f} €",
                        "Totale Riga (€)": f"{r['totale_riga']:.2f} €"
                    })
                st.table(dati_tabella)
