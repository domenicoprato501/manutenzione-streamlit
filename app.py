import json
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

# -----------------------------------------------------------------------------
# 3. SISTEMA DI LOGIN
# -----------------------------------------------------------------------------
def check_password():
    def password_entered():
        user = st.session_state.get("username", "")
        pwd = st.session_state.get("password", "")
        
        passwords = st.secrets.get("passwords", {})
        if user in passwords and str(passwords[user]) == pwd:
            st.session_state["password_correct"] = True
            st.session_state["current_user"] = user
            if "password" in st.session_state:
                del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Accesso a Garage Manager Pro")
    st.text_input("Username", key="username")
    st.text_input("Password", type="password", key="password")
    st.button("Accedi", on_click=password_entered)

    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("❌ Username o password errati")

    return False

if not check_password():
    st.stop()

# -----------------------------------------------------------------------------
# 4. SIDEBAR & MENU DI NAVIGAZIONE
# -----------------------------------------------------------------------------
st.sidebar.write(f"👤 Utente collegato: **{st.session_state.get('current_user', 'Admin')}**")
if st.sidebar.button("Logout"):
    st.session_state["password_correct"] = False
    st.rerun()

st.sidebar.divider()
menu = st.sidebar.radio("Menu", ["📋 Registro Veicoli", "➕ Nuovo Intervento", "🔍 Ricerca Targa"])

# -----------------------------------------------------------------------------
# 5. SCHERMATA: REGISTRO VEICOLI (LAYOUT ORIGINALE)
# -----------------------------------------------------------------------------
if menu == "📋 Registro Veicoli":
    st.title("📋 Registro Veicoli & Interventi")
    
    docs = db.collection("veicoli").stream()
    veicoli_list = [doc.to_dict() for doc in docs]
    
    if not veicoli_list:
        st.info("Nessun veicolo presente nel database.")
    else:
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
        
        submitted = st.form_submit_button("Salva nel Database", type="primary")
        
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
