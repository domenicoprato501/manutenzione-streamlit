import streamlit as st
import pandas as pd
import requests
import json
import firebase_admin
from firebase_admin import credentials, firestore, auth as admin_auth

# Configurazione della Pagina
st.set_page_config(page_title="Gestione Parco Auto", layout="wide", page_icon="🚗")

# ==========================================
# 1. INIZIALIZZAZIONE FIREBASE ADMIN
# ==========================================
if not firebase_admin._apps:
    try:
        firebase_secrets = st.secrets["firebase"]
        
        # Gestisce il caso in cui il JSON sia racchiuso in 'text_key'
        if "text_key" in firebase_secrets:
            key_dict = json.loads(firebase_secrets["text_key"])
        else:
            key_dict = dict(firebase_secrets)
            
        # Pulisce i caratteri newline della private_key per il Cloud
        if "private_key" in key_dict:
            key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
            
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"Errore durante l'inizializzazione di Firebase Admin: {e}")
        st.stop()

db = firestore.client()

# Recupera l'API Key dal dizionario decodificato o dai secrets standard
try:
    if "text_key" in st.secrets["firebase"]:
        key_dict_temp = json.loads(st.secrets["firebase"]["text_key"])
        FIREBASE_API_KEY = key_dict_temp.get("api_key") or st.secrets["firebase"].get("api_key")
    else:
        FIREBASE_API_KEY = st.secrets["firebase"].get("api_key")
except Exception:
    FIREBASE_API_KEY = None

# ==========================================
# 2. FUNZIONI DI SUPPORTO
# ==========================================
def login_con_firebase_rest(email, password):
    """Verifica le credenziali dell'utente tramite la REST API di Firebase Auth."""
    if not FIREBASE_API_KEY:
        raise Exception("Chiave 'api_key' non trovata nella configurazione di Firebase.")
        
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    response = requests.post(url, json=payload)
    data = response.json()
    
    if "error" in data:
        msg = data["error"]["message"]
        if msg in ["EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS"]:
            raise Exception("Credenziali non valide. Verifica email/username e password.")
        elif msg == "USER_DISABLED":
            raise Exception("Account disabilitato.")
        else:
            raise Exception(msg)
            
    return data

def ottieni_email_da_identificatore(identificatore):
    """
    Se l'identificatore contiene '@' viene restituito direttamente come email.
    Altrimenti cerca il documento dello username nella collezione 'utenti' su Firestore.
    """
    identificatore = identificatore.strip().lower()
    
    if "@" in identificatore:
        return identificatore
        
    doc_ref = db.collection("utenti").document(identificatore).get()
    if doc_ref.exists:
        return doc_ref.to_dict().get("email")
    return None

def format_km(valore):
    try:
        return f"{int(valore):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"

# Inizializzazione Stato Sessione
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False
if "utente_corrente" not in st.session_state:
    st.session_state.utente_corrente = None
if "username_corrente" not in st.session_state:
    st.session_state.username_corrente = None

# ==========================================
# 3. SCHERMATA ACCESSO / REGISTRAZIONE
# ==========================================
if not st.session_state.autenticato:
    st.title("🚗 Gestione Parco Auto")
    
    tab_login, tab_registrazione = st.tabs(["🔑 Accedi", "📝 Registrati"])
    
    # --- SCHEDA ACCESSO ---
    with tab_login:
        st.subheader("Accedi al tuo account")
        input_login = st.text_input("Email o Username", key="login_input").strip().lower()
        password_login = st.text_input("Password", type="password", key="login_pass").strip()
        
        if st.button("ACCEDI", use_container_width=True):
            if not input_login or not password_login:
                st.error("Inserisci sia l'email/username che la password.")
            else:
                try:
                    email_target = ottieni_email_da_identificatore(input_login)
                    
                    if not email_target:
                        st.error("Username non trovato nel database.")
                    else:
                        login_con_firebase_rest(email_target, password_login)
                        
                        # Recupera lo username corrispondente per l'interfaccia
                        username_trovato = None
                        utenti_query = db.collection("utenti").where("email", "==", email_target).limit(1).get()
                        for doc in utenti_query:
                            username_trovato = doc.id
                            
                        st.session_state.autenticato = True
                        st.session_state.utente_corrente = email_target
                        st.session_state.username_corrente = username_trovato or email_target
                        
                        st.success("Accesso eseguito!")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Errore di accesso: {e}")

    # --- SCHEDA REGISTRAZIONE ---
    with tab_registrazione:
        st.subheader("Crea un nuovo account")
        username_reg = st.text_input("Scegli Username", key="reg_user").strip().lower()
        email_reg = st.text_input("La tua Email", key="reg_email").strip().lower()
        password_reg = st.text_input("Scegli Password (min. 6 caratteri)", type="password", key="reg_pass").strip()
        
        if st.button("REGISTRATI", use_container_width=True):
            if not username_reg or not email_reg or not password_reg:
                st.error("Compila tutti i campi richiesti.")
            elif "@" in username_reg:
                st.error("Lo username non può contenere la '@'.")
            elif len(password_reg) < 6:
                st.error("La password deve contenere almeno 6 caratteri.")
            else:
                try:
                    # Check esistenza username
                    doc_username = db.collection("utenti").document(username_reg).get()
                    if doc_username.exists:
                        st.error("Questo Username è già in uso. Scegline un altro.")
                    else:
                        # Crea utente in Firebase Auth
                        user_record = admin_auth.create_user(
                            email=email_reg,
                            password=password_reg,
                            display_name=username_reg
                        )
                        
                        # Mappa Username -> Email su Firestore
                        db.collection("utenti").document(username_reg).set({
                            "email": email_reg,
                            "uid": user_record.uid
                        })
                        
                        st.success("Registrazione completata! Ora puoi effettuare l'accesso.")
                        
                except admin_auth.EmailAlreadyExistsError:
                    st.error("Questa email risulta già registrata.")
                except Exception as e:
                    st.error(f"Errore durante la registrazione: {e}")

# ==========================================
# 4. APPLICAZIONE PRINCIPALE
# ==========================================
else:
    veicoli_ref = db.collection("veicoli")
    
    # Barra superiore con Logout
    col_t, col_out = st.columns([4, 1])
    with col_t:
        st.title("🚗 Gestione Parco Auto & Manutenzioni")
    with col_out:
        st.write(f"👤 Utente: **{st.session_state.username_corrente}**")
        if st.button("🚪 Esci"):
            st.session_state.autenticato = False
            st.session_state.utente_corrente = None
            st.session_state.username_corrente = None
            st.rerun()

    # Lettura veicoli
    docs = veicoli_ref.stream()
    dati = {doc.id: doc.to_dict() for doc in docs}

    if not dati:
        st.info("Nessun veicolo presente. Aggiungi la prima targa per iniziare.")
        
        with st.form("nuovo_veicolo_form"):
            st.write("### ➕ Aggiungi Nuovo Veicolo")
            nuova_targa = st.text_input("Targa").upper().strip()
            nuovo_modello = st.text_input("Modello / Descrizione")
            km_iniziali = st.number_input("Chilometri Attuali", min_value=0, step=500)
            
            if st.form_submit_button("Salva Veicolo"):
                if nuova_targa:
                    veicoli_ref.document(nuova_targa).set({
                        "modello": nuovo_modello,
                        "km_attuali": km_iniziali,
                        "storico_interventi": []
                    })
                    st.success(f"Veicolo {nuova_targa} aggiunto!")
                    st.rerun()
                else:
                    st.error("Inserisci una targa valida.")
    else:
        # Selezione Veicolo
        targhe = list(dati.keys())
        targa_selezionata = st.sidebar.selectbox("🚘 Seleziona Veicolo", targhe)
        v = dati[targa_selezionata]
        storico_lista = v.get("storico_interventi", [])

        # Sidebar
        with st.sidebar:
            st.divider()
            st.header(f"📌 {targa_selezionata}")
            st.caption(f"Modello: {v.get('modello', 'N/D')}")
            
            nuovi_km = st.number_input("Chilometri Attuali", min_value=0, value=int(v.get("km_attuali", 0)), step=100)
            if nuovi_km != v.get("km_attuali"):
                if st.button("💾 Aggiorna Km"):
                    veicoli_ref.document(targa_selezionata).update({"km_attuali": nuovi_km})
                    st.success("Km aggiornati!")
                    st.rerun()

            if storico_lista:
                st.divider()
                st.subheader("📊 Esporta Dati")
                df_csv = pd.DataFrame(storico_lista).rename(columns={
                    "data": "Data",
                    "lavoro": "Intervento",
                    "km": "Chilometri",
                    "costo": "Costo (€)"
                })[["Data", "Chilometri", "Intervento", "Costo (€)"]]
                
                st.download_button(
                    label="📥 Scarica Storico CSV",
                    data=df_csv.to_csv(index=False).encode("utf-8"),
                    file_name=f"storico_{targa_selezionata}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        # Content Main
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Veicolo Selezionato", targa_selezionata)
        with col2:
            st.metric("Chilometraggio Attuale", f"{format_km(v.get('km_attuali', 0))} Km")

        st.divider()
        st.subheader("🛠️ Registra Nuovo Intervento")

        if hasattr(st, "popover"):
            with st.popover("🛠️ INTERVENTO RAPIDO"):
                with st.form("form_rapido"):
                    data_r = st.date_input("Data", key="data_r").strftime("%d/%m/%Y")
                    km_r = st.number_input("Km", min_value=0, value=int(v.get("km_attuali", 0)), key="km_r")
                    lavoro_r = st.text_input("Descrizione lavoro", key="lavoro_r")
                    costo_r = st.number_input("Costo (€)", min_value=0.0, format="%.2f", key="costo_r")
                    
                    if st.form_submit_button("SALVA RAPIDO"):
                        if lavoro_r.strip():
                            storico_lista.append({"data": data_r, "km": km_r, "lavoro": lavoro_r, "costo": costo_r})
                            veicoli_ref.document(targa_selezionata).update({
                                "storico_interventi": storico_lista,
                                "km_attuali": max(km_r, v.get("km_attuali", 0))
                            })
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
                    lavoro_int = st.text_input("Descrizione Intervento")

                if st.form_submit_button("💾 SALVA INTERVENTO"):
                    if lavoro_int.strip():
                        storico_lista.append({
                            "data": data_int,
                            "km": km_int,
                            "lavoro": lavoro_int,
                            "costo": costo_int
                        })
                        veicoli_ref.document(targa_selezionata).update({
                            "storico_interventi": storico_lista,
                            "km_attuali": max(km_int, v.get("km_attuali", 0))
                        })
                        st.success("Intervento registrato!")
                        st.rerun()
                    else:
                        st.error("Inserisci la descrizione dell'intervento.")

        st.divider()
        st.subheader("📜 STORICO MANUTENZIONI")

        if not storico_lista:
            st.caption("Nessun intervento registrato.")
        else:
            interventi_per_anno = {}
            for item in storico_lista:
                anno = item.get("data", "").split("/")[-1] if "/" in item.get("data", "") else "Altro"
                interventi_per_anno.setdefault(anno, []).append(item)

            for anno in sorted(interventi_per_anno.keys(), reverse=True):
                totale = sum(i.get("costo", 0.0) for i in interventi_per_anno[anno])
                st.markdown(f"#### 📅 --- ANNO {anno} (Totale Spesa: {totale:.2f}€) ---")
                
                for item in reversed(interventi_per_anno[anno]):
                    st.info(f"🔧 **{item.get('lavoro', 'Intervento')}**\n\n🗓️ Data: {item.get('data', 'N/D')} | 📍 Km: {format_km(item.get('km', 0))} | 💶 Spesa: {item.get('costo', 0.0):.2f}€")
