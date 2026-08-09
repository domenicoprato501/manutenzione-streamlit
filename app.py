import streamlit as st
import pandas as pd
import requests
import json
import firebase_admin
from firebase_admin import credentials, firestore, auth as admin_auth

# Configurazione della Pagina
st.set_page_config(page_title="Gestione Manutenzione Veicoli", layout="wide", page_icon="🚗")

# ==========================================
# 1. INIZIALIZZAZIONE FIREBASE
# ==========================================
if not firebase_admin._apps:
    try:
        # Prende le credenziali da Streamlit Secrets
        firebase_secrets = dict(st.secrets["firebase"])
        
        # Correzione formattazione newline della private_key (necessaria su Streamlit Cloud)
        if "private_key" in firebase_secrets:
            firebase_secrets["private_key"] = firebase_secrets["private_key"].replace("\\n", "\n")
            
        cred = credentials.Certificate(firebase_secrets)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Errore durante l'inizializzazione di Firebase Admin: {e}")
        st.stop()

db = firestore.client()
FIREBASE_API_KEY = st.secrets["firebase"]["api_key"]

# ==========================================
# 2. FUNZIONI DI SUPPORTO FIREBASE
# ==========================================
def login_con_firebase_rest(email, password):
    """
    Effettua la verifica della password dell'utente tramite la REST API di Firebase Auth.
    """
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    response = requests.post(url, json=payload)
    data = response.json()
    
    if "error" in data:
        messaggio_errore = data["error"]["message"]
        if messaggio_errore in ["EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS"]:
            raise Exception("Credenziali non valide. Controlla email/username e password.")
        elif messaggio_errore == "USER_DISABLED":
            raise Exception("Questo account è stato disabilitato.")
        else:
            raise Exception(messaggio_errore)
            
    return data

def ottieni_email_da_identificatore(identificatore):
    """
    Restituisce l'email associata. Se l'identificatore è già un'email, la restituisce,
    altrimenti cerca lo username nella collezione 'utenti' di Firestore.
    """
    identificatore = identificatore.strip().lower()
    
    # Se contiene @ assume sia già un'email
    if "@" in identificatore:
        return identificatore
        
    # Altrimenti cerca la corrispondenza dello username su Firestore
    doc_ref = db.collection("utenti").document(identificatore).get()
    if doc_ref.exists:
        dati_utente = doc_ref.to_dict()
        return dati_utente.get("email")
    else:
        return None

def format_km(valore):
    try:
        return f"{int(valore):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"

# Inizializzazione Session State
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False
if "utente_corrente" not in st.session_state:
    st.session_state.utente_corrente = None
if "username_corrente" not in st.session_state:
    st.session_state.username_corrente = None

# ==========================================
# 3. SCHERMATA LOGIN / REGISTRAZIONE
# ==========================================
if not st.session_state.autenticato:
    st.title("🚗 Gestione Parco Auto")
    
    tab_login, tab_registrazione = st.tabs(["🔑 Accedi", "📝 Registrati"])
    
    # --- TAB LOGIN ---
    with tab_login:
        st.subheader("Accedi al tuo account")
        input_login = st.text_input("Email o Username", key="login_input").strip().lower()
        password_login = st.text_input("Password", type="password", key="login_pass").strip()
        
        if st.button("ACCEDI", use_container_width=True):
            if not input_login or not password_login:
                st.error("Inserisci sia l'email/username che la password.")
            else:
                try:
                    # Trova l'email associata (sia se inserito username che email)
                    email_target = ottieni_email_da_identificatore(input_login)
                    
                    if not email_target:
                        st.error("Username non trovato.")
                    else:
                        # Autenticazione tramite Firebase Auth REST API
                        risultato = login_con_firebase_rest(email_target, password_login)
                        
                        # Recupera lo username associato all'email per la sessione
                        username_trovato = None
                        utenti_query = db.collection("utenti").where("email", "==", email_target).limit(1).get()
                        for doc in utenti_query:
                            username_trovato = doc.id
                            
                        st.session_state.autenticato = True
                        st.session_state.utente_corrente = email_target
                        st.session_state.username_corrente = username_trovato or email_target
                        
                        st.success("Accesso effettuato con successo!")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"Errore di accesso: {e}")

    # --- TAB REGISTRAZIONE ---
    with tab_registrazione:
        st.subheader("Crea un nuovo account")
        username_reg = st.text_input("Scegli Username", key="reg_user").strip().lower()
        email_reg = st.text_input("La tua Email", key="reg_email").strip().lower()
        password_reg = st.text_input("Scegli Password (min. 6 caratteri)", type="password", key="reg_pass").strip()
        
        if st.button("REGISTRATI", use_container_width=True):
            if not username_reg or not email_reg or not password_reg:
                st.error("Compila tutti i campi richiesti.")
            elif "@" in username_reg:
                st.error("Lo username non può contenere il carattere '@'.")
            elif len(password_reg) < 6:
                st.error("La password deve contenere almeno 6 caratteri.")
            else:
                try:
                    # 1. Verificare se lo username esiste già in Firestore
                    doc_username = db.collection("utenti").document(username_reg).get()
                    if doc_username.exists:
                        st.error("Questo Username è già stato preso. Scegline un altro.")
                    else:
                        # 2. Creare l'utente in Firebase Authentication
                        user_record = admin_auth.create_user(
                            email=email_reg,
                            password=password_reg,
                            display_name=username_reg
                        )
                        
                        # 3. Salvare la mappatura Username -> Email su Firestore
                        db.collection("utenti").document(username_reg).set({
                            "email": email_reg,
                            "uid": user_record.uid
                        })
                        
                        st.success("Registrazione completata con successo! Ora puoi accedere.")
                        
                except admin_auth.EmailAlreadyExistsError:
                    st.error("Questa email è già registrata. Prova ad accedere.")
                except Exception as e:
                    st.error(f"Errore durante la registrazione: {e}")

# ==========================================
# 4. APPLICAZIONE PRINCIPALE (Dopo il Login)
# ==========================================
else:
    # Gestione Dati Veicoli tramite Firestore
    veicoli_ref = db.collection("veicoli")
    
    # Intestazione e Logout
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

    # Carica veicoli dal database Firestore
    docs = veicoli_ref.stream()
    dati = {doc.id: doc.to_dict() for doc in docs}

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
                    nuovo_doc = {
                        "modello": nuovo_modello,
                        "km_attuali": km_iniziali,
                        "storico_interventi": []
                    }
                    veicoli_ref.document(nuova_targa).set(nuovo_doc)
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
                    veicoli_ref.document(targa_selezionata).update({"km_attuali": nuovi_km})
                    st.success("Km aggiornati!")
                    st.rerun()

            # === DOWNLOAD CSV ===
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
                            nuovo_int = {"data": data_r, "km": km_r, "lavoro": lavoro_r, "costo": costo_r}
                            storico_lista.append(nuovo_int)
                            nuovi_km_attuali = max(km_r, v.get("km_attuali", 0))
                            
                            veicoli_ref.document(targa_selezionata).update({
                                "storico_interventi": storico_lista,
                                "km_attuali": nuovi_km_attuali
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
                        storico_lista.append(nuovo_registro)
                        nuovi_km_attuali = max(km_int, v.get("km_attuali", 0))
                        
                        veicoli_ref.document(targa_selezionata).update({
                            "storico_interventi": storico_lista,
                            "km_attuali": nuovi_km_attuali
                        })
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
