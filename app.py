import io
import json
import hashlib
import pandas as pd
import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

# -----------------------------------------------------------------------------
# 1. CONFIGURAZIONE PAGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Garage Manager Pro",
    page_icon="🚗",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. CONNESSIONE A FIRESTORE
# -----------------------------------------------------------------------------
@st.cache_resource
def get_db():
    try:
        key_dict = json.loads(st.secrets["firestore"]["text_key"])
        creds = service_account.Credentials.from_service_account_info(key_dict)
        return firestore.Client(credentials=creds)
    except Exception as e:
        st.error(f"❌ Errore di connessione al database: {e}")
        st.stop()

db = get_db()

# --- FUNZIONE PER CIFRARE LE PASSWORD ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# -----------------------------------------------------------------------------
# 3. SISTEMA DI AUTENTICAZIONE (ACCEDI / REGISTRATI)
# -----------------------------------------------------------------------------
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔒 Garage Manager Pro")
        
        tab_login, tab_register = st.tabs(["🔑 Accedi", "📝 Registrati"])
        
        # --- SCHEDA ACCEDI ---
        with tab_login:
            with st.form("form_login"):
                user = st.text_input("Username").strip().lower()
                pwd = st.text_input("Password", type="password").strip()
                submit_login = st.form_submit_button("Accedi", type="primary", use_container_width=True)
                
                if submit_login:
                    if not user or not pwd:
                        st.error("⚠️ Inserisci sia Username che Password.")
                    else:
                        user_doc = db.collection("utenti").document(user).get()
                        if user_doc.exists:
                            user_data = user_doc.to_dict()
                            if user_data.get("password_hash") == make_hash(pwd):
                                st.session_state["password_correct"] = True
                                st.session_state["current_user"] = user_data.get("nome", user)
                                st.rerun()
                            else:
                                st.error("❌ Password errata.")
                        else:
                            st.error("❌ Username non trovato.")

        # --- SCHEDA REGISTRATI ---
        with tab_register:
            with st.form("form_register"):
                new_user = st.text_input("Scegli un Username *").strip().lower()
                new_name = st.text_input("Nome e Cognome *").strip()
                new_pwd = st.text_input("Password *", type="password").strip()
                confirm_pwd = st.text_input("Conferma Password *", type="password").strip()
                
                submit_reg = st.form_submit_button("Crea Account", use_container_width=True)
                
                if submit_reg:
                    if not new_user or not new_name or not new_pwd:
                        st.error("⚠️ Compila tutti i campi obbligatori.")
                    elif new_pwd != confirm_pwd:
                        st.error("❌ Le password non coincidono.")
                    elif len(new_pwd) < 6:
                        st.error("⚠️ La password deve contenere almeno 6 caratteri.")
                    else:
                        user_ref = db.collection("utenti").document(new_user)
                        if user_ref.get().exists:
                            st.error("❌ Questo Username è già utilizzato.")
                        else:
                            user_ref.set({
                                "username": new_user,
                                "nome": new_name,
                                "password_hash": make_hash(new_pwd),
                                "ruolo": "Meccanico"
                            })
                            st.success("✅ Account creato con successo! Ora puoi accedere dalla scheda 'Accedi'.")

    return False

if not check_password():
    st.stop()

# -----------------------------------------------------------------------------
# 4. SIDEBAR & NAVIGAZIONE
# -----------------------------------------------------------------------------
st.sidebar.title("🛠️ Garage Manager")
st.sidebar.write(f"Utente connesso: **{st.session_state.get('current_user', 'User')}**")

if st.sidebar.button("Logout", use_container_width=True):
    st.session_state["password_correct"] = False
    st.rerun()

st.sidebar.divider()
menu = st.sidebar.radio("Menu", ["📋 Registro Veicoli", "➕ Nuovo Intervento", "🔍 Ricerca Targa"])

# -----------------------------------------------------------------------------
# 5. SCHERMATA: REGISTRO VEICOLI & ESPORTAZIONE DATI
# -----------------------------------------------------------------------------
if menu == "📋 Registro Veicoli":
    st.title("📋 Registro Veicoli & Interventi")
    
    docs = db.collection("veicoli").stream()
    veicoli_list = [doc.to_dict() for doc in docs]
    
    if not veicoli_list:
        st.info("Nessun veicolo presente nel database. Aggiungi il primo intervento dal menu a sinistra.")
    else:
        # --- PREPARAZIONE DATI PER ESPORTAZIONE ---
        rows = []
        for v in veicoli_list:
            interventi = v.get("interventi", [])
            if interventi:
                for i in interventi:
                    rows.append({
                        "Targa": v.get("targa", ""),
                        "Marca": v.get("marca", ""),
                        "Modello": v.get("modello", ""),
                        "Cliente": v.get("cliente", ""),
                        "Telefono": v.get("telefono", ""),
                        "Km Attuali": v.get("km", 0),
                        "Data Intervento": i.get("data", ""),
                        "Descrizione Lavori": i.get("descrizione", ""),
                        "Costo (€)": i.get("costo", 0.0),
                        "Operatore": i.get("operatore", "")
                    })
            else:
                rows.append({
                    "Targa": v.get("targa", ""),
                    "Marca": v.get("marca", ""),
                    "Modello": v.get("modello", ""),
                    "Cliente": v.get("cliente", ""),
                    "Telefono": v.get("telefono", ""),
                    "Km Attuali": v.get("km", 0),
                    "Data Intervento": "Nessun intervento",
                    "Descrizione Lavori": "-",
                    "Costo (€)": 0.0,
                    "Operatore": "-"
                })

        df = pd.DataFrame(rows)

        # --- SEZIONE PULSANTI DOWNLOAD ---
        st.subheader("📥 Esporta Registro")
        col_dl1, col_dl2, _ = st.columns([1, 1, 2])

        # 1. Download CSV
        csv_data = df.to_csv(index=False).encode('utf-8')
        col_dl1.download_button(
            label="📄 Scarica in CSV",
            data=csv_data,
            file_name="registro_veicoli.csv",
            mime="text/csv",
            use_container_width=True
        )

        # 2. Download Excel (.xlsx)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Registro Veicoli")
        
        col_dl2.download_button(
            label="📊 Scarica in Excel",
            data=buffer.getvalue(),
            file_name="registro_veicoli.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        st.divider()

        # --- VISUALIZZAZIONE SCHEDE VEICOLI ---
        st.subheader("🚘 Schede Veicoli")
        for v in veicoli_list:
            with st.expander(f"🚘 {v.get('targa', 'N/A')} - {v.get('marca', '')} {v.get('modello', '')} ({v.get('cliente', 'Cliente sconosciuto')})"):
                col1, col2, col3 = st.columns(3)
                col1.write(f"**Cliente:** {v.get('cliente', '-')}")
                col2.write(f"**Telefono:** {v.get('telefono', '-')}")
                col3.write(f"**Km Attuali:** {v.get('km', '-')}")
                
                st.markdown("##### 🛠️ Cronologia Interventi")
                interventi = v.get("interventi", [])
                if interventi:
                    for i in reversed(interventi):
                        st.caption(f"📅 **Data:** {i.get('data')} | **Operatore:** {i.get('operatore')}")
                        st.write(f"**Descrizione:** {i.get('descrizione')}")
                        st.write(f"**Costo:** {i.get('costo')} €")
                        st.divider()
                else:
                    st.write("Nessun intervento registrato.")

# -----------------------------------------------------------------------------
# 6. SCHERMATA: NUOVO INTERVENTO / NUOVO VEICOLO
# -----------------------------------------------------------------------------
elif menu == "➕ Nuovo Intervento":
    st.title("➕ Registra Veicolo o Intervento")
    
    with st.form("form_intervento", clear_on_submit=True):
        col1, col2 = st.columns(2)
        targa = col1.text_input("Targa *").upper().strip()
        cliente = col2.text_input("Nome e Cognome Cliente *")
        
        col3, col4, col5 = st.columns(3)
        marca = col3.text_input("Marca")
        modello = col4.text_input("Modello")
        telefono = col5.text_input("Telefono")
        
        st.divider()
        st.subheader("Dettagli Lavoro")
        col6, col7, col8 = st.columns(3)
        data_intervento = col6.date_input("Data Intervento")
        km = col7.number_input("Chilometraggio Auto", min_value=0, step=1000)
        costo = col8.number_input("Costo Totale (€)", min_value=0.0, step=10.0)
        
        descrizione = st.text_area("Descrizione Lavori Eseguiti (Tagliando, Freni, Olio...)")
        
        submitted = st.form_submit_button("Salva nel Database", type="primary", use_container_width=True)
        
        if submitted:
            if not targa or not cliente:
                st.error("⚠️ I campi Targa e Cliente sono obbligatori.")
            else:
                doc_ref = db.collection("veicoli").document(targa)
                doc = doc_ref.get()
                
                nuovo_intervento = {
                    "data": str(data_intervento),
                    "descrizione": descrizione,
                    "costo": costo,
                    "operatore": st.session_state.get("current_user", "Admin")
                }
                
                if doc.exists:
                    doc_ref.update({
                        "km": km,
                        "telefono": telefono,
                        "interventi": firestore.ArrayUnion([nuovo_intervento])
                    })
                    st.success(f"✅ Nuovo intervento aggiunto al veicolo con targa {targa}!")
                else:
                    doc_ref.set({
                        "targa": targa,
                        "cliente": cliente,
                        "marca": marca,
                        "modello": modello,
                        "telefono": telefono,
                        "km": km,
                        "interventi": [nuovo_intervento]
                    })
                    st.success(f"✅ Veicolo {targa} e relativo intervento salvati con successo!")

# -----------------------------------------------------------------------------
# 7. SCHERMATA: RICERCA TARGA
# -----------------------------------------------------------------------------
elif menu == "🔍 Ricerca Targa":
    st.title("🔍 Ricerca Veicolo per Targa")
    
    search_targa = st.text_input("Inserisci la Targa da cercare").upper().strip()
    
    if search_targa:
        doc_ref = db.collection("veicoli").document(search_targa)
        doc = doc_ref.get()
        
        if doc.exists:
            v = doc.to_dict()
            st.success(f"Veicolo Trovato: {v.get('marca')} {v.get('modello')}")
            
            col1, col2 = st.columns(2)
            col1.metric("Cliente", v.get("cliente"))
            col1.metric("Telefono", v.get("telefono"))
            col2.metric("Ultimi Km Registrati", f"{v.get('km')} km")
            
            st.subheader("Interventi Effettuati")
            for i in reversed(v.get("interventi", [])):
                st.info(f"📅 **{i.get('data')}** — Costo: **{i.get('costo')} €**\n\n{i.get('descrizione')}")
        else:
            st.warning(f"Nessun veicolo trovato con la targa **{search_targa}**.")
