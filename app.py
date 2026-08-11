import streamlit as st
from datetime import date

# ==========================================
# 1. CONFIGURAZIONE PAGINA
# ==========================================
st.set_page_config(page_title="Gestione Manutenzione", layout="wide")

# Cataloghi di esempio (sostituisci o popola con i tuoi dati reali)
CATALOGO_RICAMBI = {
    "-- Seleziona o scrivi a mano --": 0.0,
    "Filtro Olio": 15.00,
    "Olio Motore 5W30 (Litri)": 12.50,
    "Filtro Aria": 22.00,
    "Pastiglie Freno": 45.00
}

opzioni_catalogo = list(CATALOGO_RICAMBI.keys())

# ==========================================
# 2. INIZIALIZZAZIONE DELLO STATO (Session State)
# ==========================================
# Inizializza la lista dei ricambi con una riga vuota di default
if "ricambi_manutenzione" not in st.session_state:
    st.session_state.ricambi_manutenzione = [
        {"ricambio_scelto": "-- Seleziona o scrivi a mano --", "nome_custom": "", "quantita": 1.0, "prezzo": 0.0}
    ]

# Funzione per aggiungere una nuova riga quando si clicca sul tasto "+"
def aggiungi_riga():
    st.session_state.ricambi_manutenzione.append(
        {"ricambio_scelto": "-- Seleziona o scrivi a mano --", "nome_custom": "", "quantita": 1.0, "prezzo": 0.0}
    )

# Funzione per rimuovere una riga specificata
def rimuovi_riga(index):
    if len(st.session_state.ricambi_manutenzione) > 1:
        st.session_state.ricambi_manutenzione.pop(index)

# ==========================================
# 3. INTERFACCIA UTENTE (FORM MANUTENZIONE)
# ==========================================
st.title("🛠️ Inserimento Manutenzione")

with st.form("form_manutenzione"):
    # --- DATI MANUTENZIONE ---
    st.subheader("Dettagli Intervento")
    col_desc, col_data = st.columns([3, 1])
    descrizione = col_desc.text_input("Descrizione Manutenzione *", placeholder="Es. Tagliando completo")
    data_intervento = col_data.date_input("Data Intervento", value=date.today())

    st.markdown("---")
    st.subheader("📦 Ricambi Utilizzati")

    totale_manutenzione = 0.0

    # --- CICLO SULLE RIGHE DEI RICAMBI ---
    for i, item in enumerate(st.session_state.ricambi_manutenzione):
        cols = st.columns([3, 3, 2, 2, 2, 1])

        # 1. Menu a tendina per catalogo
        scelta = cols[0].selectbox(
            "Ricambio da Catalogo",
            options=opzioni_catalogo,
            index=opzioni_catalogo.index(item["ricambio_scelto"]) if item["ricambio_scelto"] in opzioni_catalogo else 0,
            key=f"scelta_{i}"
        )
        item["ricambio_scelto"] = scelta

        # Prezzo predefinito dal catalogo (se selezionato)
        prezzo_default = CATALOGO_RICAMBI[scelta] if scelta != "-- Seleziona o scrivi a mano --" else item["prezzo"]

        # 2. Testo libero per ricambio manuale
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

        # 5. Calcolo automatico del totale di riga
        totale_riga = round(item["quantita"] * item["prezzo"], 2)
        cols[4].metric("Totale Riga", f"{totale_riga:.2f} €")
        totale_manutenzione += totale_riga

        # 6. Pulsante Elimina riga
        cols[5].write("")
        cols[5].write("")
        cols[5].form_submit_button("🗑️", on_click=rimuovi_riga, args=(i,))

    # --- PULSANTE PER AGGIUNGERE UN ALTRO RICAMBIO ---
    st.form_submit_button("➕ Aggiungi altro ricambio", on_click=aggiungi_riga)

    st.markdown("---")

    # --- TOTALE GENERALE E CONFERMA ---
    col_tot, col_btn = st.columns([2, 1])
    col_tot.markdown(f"### 💰 **Totale Manutenzione: {totale_manutenzione:.2f} €**")
    
    invia = col_btn.form_submit_button("💾 Salva Manutenzione", type="primary")

# ==========================================
# 4. GESTIONE INVIO DATI
# ==========================================
if invia:
    if not descrizione.strip():
        st.error("Inserisci la descrizione della manutenzione.")
    else:
        # Prepara la lista pulita dei ricambi inseriti
        ricambi_finali = []
        for r in st.session_state.ricambi_manutenzione:
            nome = r["nome_custom"] if r["ricambio_scelto"] == "-- Seleziona o scrivi a mano --" else r["ricambio_scelto"]
            if nome.strip():
                ricambi_finali.append({
                    "ricambio": nome,
                    "quantita": r["quantita"],
                    "prezzo_unitario": r["prezzo"],
                    "totale_riga": round(r["quantita"] * r["prezzo"], 2)
                })

        dati_salvataggio = {
            "descrizione": descrizione,
            "data": str(data_intervento),
            "totale_intervento": round(totale_manutenzione, 2),
            "ricambi": ricambi_finali
        }

        # Sostituisci questo blocco con la tua funzione di salvataggio su Database
        st.success("✅ Manutenzione salvata con successo!")
        st.json(dati_salvataggio)
