import streamlit as st
from datetime import date

# ==========================================
# 1. CONFIGURAZIONE PAGINA E CATALOGO
# ==========================================
st.set_page_config(page_title="Gestione Manutenzioni & Revisioni", layout="wide")

# Catalogo con Codice Articolo e Prezzo Unitario
CATALOGO_RICAMBI = {
    "-- Seleziona o scrivi a mano --": {"codice": "", "prezzo": 0.0},
    "Filtro Olio": {"codice": "FO-102", "prezzo": 15.00},
    "Olio Motore 5W30 (Litri)": {"codice": "OM-5W30", "prezzo": 12.50},
    "Filtro Aria": {"codice": "FA-204", "prezzo": 22.00},
    "Pastiglie Freno": {"codice": "PF-301", "prezzo": 45.00}
}

opzioni_catalogo = list(CATALOGO_RICAMBI.keys())

# ==========================================
# 2. INIZIALIZZAZIONE DELLO STATO (Session State)
# ==========================================
if "ricambi_manutenzione" not in st.session_state:
    st.session_state.ricambi_manutenzione = [
        {
            "ricambio_scelto": "-- Seleziona o scrivi a mano --",
            "codice_articolo": "",
            "nome_custom": "",
            "quantita": 1.0,
            "prezzo": 0.0
        }
    ]

def aggiungi_riga():
    st.session_state.ricambi_manutenzione.append(
        {
            "ricambio_scelto": "-- Seleziona o scrivi a mano --",
            "codice_articolo": "",
            "nome_custom": "",
            "quantita": 1.0,
            "prezzo": 0.0
        }
    )

def rimuovi_riga(index):
    if len(st.session_state.ricambi_manutenzione) > 1:
        st.session_state.ricambi_manutenzione.pop(index)

# ==========================================
# 3. INTERFACCIA UTENTE
# ==========================================
st.title("🛠️ Inserimento Manutenzione & Revisione")

with st.form("form_manutenzione"):
    # --- SEZIONE MANUTENZIONE & REVISIONE ---
    st.subheader("Dettagli Intervento & Revisione")
    col_desc, col_data, col_rev = st.columns([2, 1, 1])
    
    descrizione = col_desc.text_input("Descrizione Manutenzione *", placeholder="Es. Tagliando e revisione periodica")
    data_intervento = col_data.date_input("Data Intervento", value=date.today())
    stato_revisione = col_rev.selectbox(
        "Stato Revisione",
        ["Non richiesta", "In Corso", "Superata", "Da Ripetere"]
    )

    st.markdown("---")
    st.subheader("📦 Ricambi Utilizzati")

    totale_manutenzione = 0.0

    # --- CICLO SULLE RIGHE DEI RICAMBI ---
    for i, item in enumerate(st.session_state.ricambi_manutenzione):
        cols = st.columns([2.5, 2, 2, 1.2, 1.5, 1.5, 0.8])

        # 1. Selezione da Catalogo
        scelta = cols[0].selectbox(
            "Ricambio Catalogo",
            options=opzioni_catalogo,
            index=opzioni_catalogo.index(item["ricambio_scelto"]) if item["ricambio_scelto"] in opzioni_catalogo else 0,
            key=f"scelta_{i}"
        )
        item["ricambio_scelto"] = scelta

        is_custom = (scelta == "-- Seleziona o scrivi a mano --")

        # Valori di default da catalogo o manuali
        codice_default = CATALOGO_RICAMBI[scelta]["codice"] if not is_custom else item["codice_articolo"]
        prezzo_default = CATALOGO_RICAMBI[scelta]["prezzo"] if not is_custom else item["prezzo"]

        # 2. Nome Custom (se non in catalogo)
        item["nome_custom"] = cols[1].text_input(
            "Nome (se manuale)",
            value=item["nome_custom"],
            disabled=not is_custom,
            placeholder="Nome ricambio...",
            key=f"custom_{i}"
        )

        # 3. Codice Articolo
        item["codice_articolo"] = cols[2].text_input(
            "Codice Articolo",
            value=codice_default,
            disabled=not is_custom,
            placeholder="Es. ART-12345",
            key=f"cod_{i}"
        )

        # 4. Quantità
        item["quantita"] = cols[3].number_input(
            "Quantità",
            min_value=0.1,
            value=float(item["quantita"]),
            step=0.5,
            key=f"qta_{i}"
        )

        # 5. Prezzo Unitario
        item["prezzo"] = cols[4].number_input(
            "Prezzo Unit. (€)",
            min_value=0.0,
            value=float(prezzo_default),
            step=0.5,
            key=f"prezzo_{i}"
        )

        # 6. Totale Riga (calcolo automatico)
        totale_riga = round(item["quantita"] * item["prezzo"], 2)
        cols[5].metric("Totale Riga", f"{totale_riga:.2f} €")
        totale_manutenzione += totale_riga

        # 7. Pulsante Elimina con chiave univoca
        cols[6].write("")
        cols[6].write("")
        cols[6].form_submit_button("🗑️", on_click=rimuovi_riga, args=(i,), key=f"del_{i}")

    # --- PULSANTE (+) PER AGGIUNGERE RIGHE ---
    st.form_submit_button("➕ Aggiungi altro ricambio", on_click=aggiungi_riga, key="btn_add_part")

    st.markdown("---")

    # --- TOTALE E CONFERMA ---
    col_tot, col_btn = st.columns([2, 1])
    col_tot.markdown(f"### 💰 **Totale Manutenzione: {totale_manutenzione:.2f} €**")
    
    invia = col_btn.form_submit_button("💾 Salva Manutenzione e Revisione", type="primary", key="btn_save")

# ==========================================
# 4. GESTIONE SALVATAGGIO
# ==========================================
if invia:
    if not descrizione.strip():
        st.error("Inserisci la descrizione della manutenzione.")
    else:
        ricambi_finali = []
        for r in st.session_state.ricambi_manutenzione:
            is_cat = (r["ricambio_scelto"] != "-- Seleziona o scrivi a mano --")
            nome = r["ricambio_scelto"] if is_cat else r["nome_custom"]
            codice = CATALOGO_RICAMBI[r["ricambio_scelto"]]["codice"] if is_cat else r["codice_articolo"]

            if nome.strip():
                ricambi_finali.append({
                    "codice_articolo": codice,
                    "ricambio": nome,
                    "quantita": r["quantita"],
                    "prezzo_unitario": r["prezzo"],
                    "totale_riga": round(r["quantita"] * r["prezzo"], 2)
                })

        dati_salvataggio = {
            "descrizione": descrizione,
            "data": str(data_intervento),
            "stato_revisione": stato_revisione,
            "totale_intervento": round(totale_manutenzione, 2),
            "ricambi": ricambi_finali
        }

        st.success("✅ Manutenzione e Revisione salvate con successo!")
        st.json(dati_salvataggio)
