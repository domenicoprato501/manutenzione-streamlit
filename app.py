import streamlit as st
import pandas as pd
import json
import os

# Configurazione Pagina
st.set_page_config(page_title="Gestione Manutenzione Veicoli", layout="wide", page_icon="🚗")

NOME_FILE_DATA = "veicoli_data.json"

# --- FUNZIONI DI SUPPORTO ---
def format_km(valore):
    try:
        return f"{int(valore):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"

def carica_dati():
    if os.path.exists(NOME_FILE_DATA):
        with open(NOME_FILE_DATA, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salva_dati(dati):
    with open(NOME_FILE_DATA, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=4)

# Caricamento dello stato
if "dati_veicoli" not in st.session_state:
    st.session_state.dati_veicoli = carica_dati()

dati = st.session_state.dati_veicoli

st.title("🚗 Gestione Parco Auto & Manutenzioni")

# Se non ci sono veicoli
if not dati:
    st.info("Nessun veicolo presente nel database. Aggiungi la prima targa per iniziare.")
    
    with st.form("nuovo_veicolo_form"):
        st.write("### ➕ Aggiungi Nuovo Veicolo")
        nuova_targa = st.text_input("Targa").upper().strip()
        nuovo_modello = st.text_input("Modello / Descrizione")
        km_iniziali = st.number_input("Chilometri Attuali", min_value=0, step=500)
        
        if st.form_submit_button("Salva Veicolo"):
            if nuova_targa:
                dati[nuova_targa] = {
                    "modello": nuovo_modello,
                    "km_attuali": km_iniziali,
                    "storico_interventi": []
                }
                salva_dati(dati)
                st.success(f"Veicolo {nuova_targa} aggiunto con successo!")
                st.rerun()
            else:
                st.error("Inserisci una targa valida.")
else:
    # SELEZIONE VEICOLO
    targhe = list(dati.keys())
    targa_selezionata = st.sidebar.selectbox("🚘 Seleziona Veicolo", targhe)
    v = dati[targa_selezionata]
    storico_lista = v.get("storico_interventi", [])

    # === BARRA LATERALE (SIDEBAR) ===
    with st.sidebar:
        st.divider()
        st.header(f"📌 {targa_selezionata}")
        st.caption(f"Modello: {v.get('modello', 'N/D')}")
        
        # Aggiornamento Km Veloci
        nuovi_km = st.number_input("Chilometri Attuali", min_value=0, value=int(v.get("km_attuali", 0)), step=100)
        if nuovi_km != v.get("km_attuali"):
            if st.button("💾 Aggiorna Km"):
                v["km_attuali"] = nuovi_km
                salva_dati(dati)
                st.success("Km aggiornati!")
                st.rerun()

        # === PULSANTE CSV NELLA SIDEBAR (Compare solo se c'è uno storico) ===
        if storico_lista:
            st.divider()
            st.subheader("📊 Esporta Dati")
            
            df_storico = pd.DataFrame(storico_lista)
            df_csv = df_storico.rename(columns={
                "data": "Data",
                "lavoro": "Intervento / Descrizione",
                "km": "Chilometri (Km)",
                "costo": "Costo (€)"
            })[["Data", "Chilometri (Km)", "Intervento / Descrizione", "Costo (€)"]]
            
            csv_data = df_csv.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Scarica Storico CSV",
                data=csv_data,
                file_name=f"storico_manutenzioni_{targa_selezionata}.csv",
                mime="text/csv",
                use_container_width=True
            )

    # === CONTENUTO PRINCIPALE ===
    
    # 1. INFO GENERALE VEICOLO
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Veicolo Selezionato", targa_selezionata)
    with col2:
        st.metric("Chilometraggio Attuale", f"{format_km(v.get('km_attuali', 0))} Km")

    st.divider()

    # 2. INSERIMENTO NUOVO INTERVENTO
    st.subheader("🛠️ Registra Nuovo Intervento")
    
    # Popover / Pulsante Rapido per Intervento Generico
    if hasattr(st, "popover"):
        with st.popover("🛠️ INTERVENTO GENERICO / RAPIDO"):
            with st.form("form_rapido"):
                st.write("**Inserimento Rapido Intervento**")
                data_r = st.date_input("Data", key="data_r").strftime("%d/%m/%Y")
                km_r = st.number_input("Km", min_value=0, value=int(v.get("km_attuali", 0)), key="km_r")
                lavoro_r = st.text_input("Descrizione lavoro", key="lavoro_r")
                costo_r = st.number_input("Costo (€)", min_value=0.0, format="%.2f", key="costo_r")
                
                if st.form_submit_button("SALVA RAPIDO"):
                    if lavoro_r.strip():
                        v.setdefault("storico_interventi", []).append({
                            "data": data_r, "km": km_r, "lavoro": lavoro_r, "costo": costo_r
                        })
                        if km_r > v.get("km_attuali", 0):
                            v["km_attuali"] = km_r
                        salva_dati(dati)
                        st.success("Intervento salvato!")
                        st.rerun()
                    else:
                        st.error("Inserisci una descrizione.")

    # Form Completo Espandibile
    with st.expander("➕ Form Completo Intervento"):
        with st.form("form_intervento"):
            c1, c2 = st.columns(2)
            with c1:
                data_int = st.date_input("Data Intervento").strftime("%d/%m/%Y")
                km_int = st.number_input("Chilometri all'intervento", min_value=0, value=int(v.get("km_attuali", 0)))
            with c2:
                costo_int = st.number_input("Costo (€)", min_value=0.0, format="%.2f")
                lavoro_int = st.text_input("Descrizione Intervento / Lavoro svolto")

            submit = st.form_submit_button("💾 SALVA INTERVENTO")
            
            if submit:
                if lavoro_int.strip():
                    nuovo_registro = {
                        "data": data_int,
                        "km": km_int,
                        "lavoro": lavoro_int,
                        "costo": costo_int
                    }
                    v.setdefault("storico_interventi", []).append(nuovo_registro)
                    
                    if km_int > v.get("km_attuali", 0):
                        v["km_attuali"] = km_int
                        
                    salva_dati(dati)
                    st.success("Intervento registrato con successo!")
                    st.rerun()
                else:
                    st.error("Inserisci la descrizione dell'intervento.")

    st.divider()

    # 3. SEZIONE STORICO INTERVENTI PER ANNO
    st.subheader("📜 STORICO MANUTENZIONI")

    if not storico_lista:
        st.caption("Nessun intervento registrato per questo veicolo.")
    else:
        # Raggruppamento per Anno
        interventi_per_anno = {}
        for intervento in storico_lista:
            data_str = intervento.get("data", "01/01/2026")
            try:
                anno = data_str.split("/")[-1]
            except Exception:
                anno = "Altro"
            
            interventi_per_anno.setdefault(anno, []).append(intervento)

        # Mostra dal più recente al meno recente
        for anno in sorted(interventi_per_anno.keys(), reverse=True):
            totale_anno = sum(item.get("costo", 0.0) for item in interventi_per_anno[anno])
            st.markdown(f"#### 📅 --- ANNO {anno} (Totale Spesa: {totale_anno:.2f}€) ---")
            
            for intervento in reversed(interventi_per_anno[anno]):
                d_int = intervento.get("data", "Sconosciuta")
                l_int = intervento.get("lavoro", "Intervento")
                k_int = intervento.get("km", 0)
                c_int = intervento.get("costo", 0.0)
                
                st.info(f"🔧 **{l_int}**\n\n🗓️ Data: {d_int} | 📍 Km: {format_km(k_int)} | 💶 Spesa: {c_int:.2f}€")
