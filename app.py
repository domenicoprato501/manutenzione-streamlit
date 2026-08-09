import streamlit as st
import pandas as pd
import json
import os

# Configurazione Pagina
st.set_page_config(page_title="Gestione Manutenzione Veicoli", layout="wide", page_icon="🚗")

NOME_FILE_DATA = "veicoli_data.json"
NOME_FILE_UTENTI = "utenti.json"

# --- FUNZIONI DI SUPPORTO ---
def format_km(valore):
    try:
        return f"{int(valore):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"

def carica_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def salva_json(dati, file_path):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=4)

# Inizializzazione Session State
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False
if "utente_corrente" not in st.session_state:
    st.session_state.utente_corrente = None

utenti = carica_json(NOME_FILE_UTENTI)

# ==========================================
# 🔑 SCHERMATA LOGIN / REGISTRAZIONE
# ==========================================
if not st.session_state.autenticato:
    st.title("🚗 Gestione Parco Auto")
    
    tab_login, tab_registrazione = st.tabs(["🔑 Accedi", "📝 Registrati"])
    
    with tab_login:
        st.subheader("Accedi al tuo account")
        username_login = st.text_input("Username", key="login_user").strip().lower()
        password_login = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("ACCEDI", use_container_width=True):
            if username_login in utenti and utenti[username_login] == password_login:
                st.session_state.autenticato = True
                st.session_state.utente_corrente = username_login
                st.success("Accesso effettuato!")
                st.rerun()
            else:
                st.error("Username o Password errati.")
                
    with tab_registrazione:
        st.subheader("Crea un nuovo account")
        username_reg = st.text_input("Scegli Username", key="reg_user").strip().lower()
        password_reg = st.text_input("Scegli Password", type="password", key="reg_pass")
        
        if st.button("REGISTRATI", use_container_width=True):
            if username_reg and password_reg:
                if username_reg in utenti:
                    st.error("Questo Username è già esistente.")
                else:
                    utenti[username_reg] = password_reg
                    salva_json(utenti, NOME_FILE_UTENTI)
                    st.success("Registrazione completata! Ora puoi effettuare l'accesso.")
            else:
                st.error("Inserisci sia Username che Password.")

# ==========================================
# 🚗 APPLICAZIONE PRINCIPALE (Dopo il Login)
# ==========================================
else:
    dati = carica_json(NOME_FILE_DATA)
    
    # Intestazione e Logout
    col_t, col_out = st.columns([4, 1])
    with col_t:
        st.title("🚗 Gestione Parco Auto & Manutenzioni")
    with col_out:
        st.write(f"👤 Utente: **{st.session_state.utente_corrente}**")
        if st.button("🚪 Esci"):
            st.session_state.autenticato = False
            st.session_state.utente_corrente = None
            st.rerun()

    # Se non ci sono veicoli salvati
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
                    salva_json(dati, NOME_FILE_DATA)
                    st.success(f"Veicolo {nuova_targa} aggiunto con successo!")
                    st.rerun()
                else:
                    st.error("Inserisci una targa valida.")
    else:
        # SELEZIONE VEICOLO E SIDEBAR
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
                    salva_json(dati, NOME_FILE_DATA)
                    st.success("Km aggiornati!")
                    st.rerun()

            # === PULSANTE DOWNLOAD CSV (Compare solo se c'è uno storico) ===
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
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Veicolo Selezionato", targa_selezionata)
        with col2:
            st.metric("Chilometraggio Attuale", f"{format_km(v.get('km_attuali', 0))} Km")

        st.divider()

        # INSERIMENTO NUOVO INTERVENTO
        st.subheader("🛠️ Registra Nuovo Intervento")
        
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
                            salva_json(dati, NOME_FILE_DATA)
                            st.success("Intervento salvato!")
                            st.rerun()
                        else:
                            st.error("Inserisci una descrizione.")

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
                            
                        salva_json(dati, NOME_FILE_DATA)
                        st.success("Intervento registrato con successo!")
                        st.rerun()
                    else:
                        st.error("Inserisci la descrizione dell'intervento.")

        st.divider()

        # SEZIONE STORICO INTERVENTI
        st.subheader("📜 STORICO MANUTENZIONI")

        if not storico_lista:
            st.caption("Nessun intervento registrato per questo veicolo.")
        else:
            interventi_per_anno = {}
            for intervento in storico_lista:
                data_str = intervento.get("data", "01/01/2026")
                try:
                    anno = data_str.split("/")[-1]
                except Exception:
                    anno = "Altro"
                
                interventi_per_anno.setdefault(anno, []).append(intervento)

            for anno in sorted(interventi_per_anno.keys(), reverse=True):
                totale_anno = sum(item.get("costo", 0.0) for item in interventi_per_anno[anno])
                st.markdown(f"#### 📅 --- ANNO {anno} (Totale Spesa: {totale_anno:.2f}€) ---")
                
                for intervento in reversed(interventi_per_anno[anno]):
                    d_int = intervento.get("data", "Sconosciuta")
                    l_int = intervento.get("lavoro", "Intervento")
                    k_int = intervento.get("km", 0)
                    c_int = intervento.get("costo", 0.0)
                    
                    st.info(f"🔧 **{l_int}**\n\n🗓️ Data: {d_int} | 📍 Km: {format_km(k_int)} | 💶 Spesa: {c_int:.2f}€")
