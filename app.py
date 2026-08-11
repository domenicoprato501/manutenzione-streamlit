import streamlit as st
import pandas as pd
import requests
import json
import firebase_admin
from firebase_admin import credentials, firestore, auth as admin_auth

# Configurazione della Pagina
st.set_page_config(page_title="Gestione Parco Auto", layout="wide", page_icon="🚗")

# ==========================================
# 1. INIZIALIZZAZIONE FIREBASE ADMIN & AUTH
# ==========================================
if not firebase_admin._apps:
    try:
        firebase_secrets = st.secrets["firebase"]
        
        # Caricamento credenziali sia da stringa JSON (text_key) che da chiavi dirette
        if "text_key" in firebase_secrets:
            key_dict = json.loads(firebase_secrets["text_key"])
        else:
            key_dict = dict(firebase_secrets)
            
        if "private_key" in key_dict:
            key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
            
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.error(f"Errore durante l'inizializzazione di Firebase Admin: {e}")
        st.stop()

db = firestore.client()

# Recupero della Firebase Web API Key
FIREBASE_API_KEY = None
try:
    if "api_key" in st.secrets["firebase"]:
        FIREBASE_API_KEY = st.secrets["firebase"]["api_key"]
    elif "text_key" in st.secrets["firebase"]:
        key_dict_temp = json.loads(st.secrets["firebase"]["text_key"])
        FIREBASE_API_KEY = key_dict_temp.get("api_key")
except Exception:
    FIREBASE_API_KEY = None

# ==========================================
# 2. FUNZIONI DI SUPPORTO AUTH & FORMATTAZIONE
# ==========================================
def login_con_firebase_rest(email, password):
    if not FIREBASE_API_KEY:
        raise Exception("Chiave 'api_key' non trovata nei secrets di Streamlit.")
        
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(url, json=payload)
    data = response.json()
    
    if "error" in data:
        msg = data["error"]["message"]
        if msg in ["EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS"]:
            raise Exception("Credenziali errate. Verifica email/username e password.")
        elif msg == "USER_DISABLED":
            raise Exception("Account disabilitato.")
        else:
            raise Exception(msg)
    return data

def ottieni_email_da_identificatore(identificatore):
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

# Inizializzazione Session State
if "autenticato" not in st.session_state:
    st.session_state.autenticato = False
if "utente_corrente" not in st.session_state:
    st.session_state.utente_corrente = None
if "username_corrente" not in st.session_state:
    st.session_state.username_corrente = None

# ==========================================
# 3. ACCESSO / REGISTRAZIONE UTENTI
# ==========================================
if not st.session_state.autenticato:
    st.title("🚗 Gestione Parco Auto & Manutenzioni")
    
    tab_login, tab_registrazione = st.tabs(["🔑 Accedi", "📝 Registrati"])
    
    with tab_login:
        st.subheader("Accedi al sistema")
        input_login = st.text_input("Email o Username", key="login_user").strip().lower()
        password_login = st.text_input("Password", type="password", key="login_pass").strip()
        
        if st.button("ACCEDI", use_container_width=True):
            if not input_login or not password_login:
                st.error("Inserisci credenziali valide.")
            else:
                try:
                    email_target = ottieni_email_da_identificatore(input_login)
                    if not email_target:
                        st.error("Username non trovato.")
                    else:
                        login_con_firebase_rest(email_target, password_login)
                        
                        username_trovato = None
                        utenti = db.collection("utenti").where("email", "==", email_target).limit(1).get()
                        for doc in utenti:
                            username_trovato = doc.id
                            
                        st.session_state.autenticato = True
                        st.session_state.utente_corrente = email_target
                        st.session_state.username_corrente = username_trovato or email_target
                        st.success("Accesso eseguito!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Errore di accesso: {e}")

    with tab_registrazione:
        st.subheader("Registra un nuovo account")
        username_reg = st.text_input("Username", key="reg_user").strip().lower()
        email_reg = st.text_input("Email", key="reg_email").strip().lower()
        password_reg = st.text_input("Password (minimo 6 caratteri)", type="password", key="reg_pass").strip()
        
        if st.button("REGISTRATI", use_container_width=True):
            if not username_reg or not email_reg or not password_reg:
                st.error("Compila tutti i campi.")
            elif "@" in username_reg:
                st.error("Lo username non può contenere la '@'.")
            elif len(password_reg) < 6:
                st.error("La password deve essere di almeno 6 caratteri.")
            else:
                try:
                    if db.collection("utenti").document(username_reg).get().exists:
                        st.error("Username già in uso.")
                    else:
                        user = admin_auth.create_user(email=email_reg, password=password_reg, display_name=username_reg)
                        db.collection("utenti").document(username_reg).set({"email": email_reg, "uid": user.uid})
                        st.success("Registrazione effettuata! Ora puoi accedere.")
                except admin_auth.EmailAlreadyExistsError:
                    st.error("Email già registrata.")
                except Exception as e:
                    st.error(f"Errore di registrazione: {e}")

# ==========================================
# 4. DASHBOARD COMPLETA MANUTENZIONI & REVISIONI
# ==========================================
else:
    veicoli_ref = db.collection("veicoli")
    
    # Intestazione Utente
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

    # Lettura Veicoli
    docs = veicoli_ref.stream()
    dati = {doc.id: doc.to_dict() for doc in docs}

    if not dati:
        st.info("Nessun veicolo presente nel parco auto. Aggiungi il primo veicolo.")
        with st.form("nuovo_veicolo_form"):
            st.write("### ➕ Aggiungi Nuovo Veicolo")
            targa_new = st.text_input("Targa").upper().strip()
            modello_new = st.text_input("Modello / Descrizione")
            km_new = st.number_input("Chilometri Attuali", min_value=0, step=500)
            
            if st.form_submit_button("Salva Veicolo"):
                if targa_new:
                    veicoli_ref.document(targa_new).set({
                        "modello": modello_new,
                        "km_attuali": km_new,
                        "scadenza_revisione": "",
                        "scadenza_bollo": "",
                        "storico_interventi": []
                    })
                    st.success(f"Veicolo {targa_new} salvato!")
                    st.rerun()
    else:
        # Selezione Veicolo Sidebar
        targhe = list(dati.keys())
        targa_selezionata = st.sidebar.selectbox("🚘 Seleziona Veicolo", targhe)
        v = dati[targa_selezionata]
        storico = v.get("storico_interventi", [])

        # Sidebar con gestione Km e Scadenze
        with st.sidebar:
            st.divider()
            st.header(f"📌 {targa_selezionata}")
            st.caption(f"Modello: {v.get('modello', 'N/D')}")
            
            # Modifica Km
            nuovi_km = st.number_input("Chilometri Attuali", min_value=0, value=int(v.get("km_attuali", 0)), step=100)
            if nuovi_km != v.get("km_attuali"):
                if st.button("💾 Aggiorna Km"):
                    veicoli_ref.document(targa_selezionata).update({"km_attuali": nuovi_km})
                    st.success("Chilometraggio aggiornato!")
                    st.rerun()

            st.divider()
            st.subheader("📅 Scadenze Legali")
            
            rev_val = v.get("scadenza_revisione", "")
            bollo_val = v.get("scadenza_bollo", "")
            
            nuova_scad_rev = st.text_input("Scadenza Revisione (es. MM/AAAA)", value=rev_val)
            nuova_scad_bollo = st.text_input("Scadenza Bollo (es. MM/AAAA)", value=bollo_val)
            
            if st.button("💾 Salva Scadenze"):
                veicoli_ref.document(targa_selezionata).update({
                    "scadenza_revisione": nuova_scad_rev,
                    "scadenza_bollo": nuova_scad_bollo
                })
                st.success("Scadenze salvate!")
                st.rerun()

            # Esportazione
            if storico:
                st.divider()
                st.subheader("📊 Esportazione Dati")
                df_exp = pd.DataFrame(storico)
                st.download_button(
                    label="📥 Scarica Report CSV",
                    data=df_exp.to_csv(index=False).encode("utf-8"),
                    file_name=f"report_{targa_selezionata}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        # Dashboard Metriche Principali
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Veicolo", targa_selezionata)
        c2.metric("Chilometraggio", f"{format_km(v.get('km_attuali', 0))} Km")
        c3.metric("Scadenza Revisione", v.get("scadenza_revisione") or "Non impostata")
        c4.metric("Scadenza Bollo", v.get("scadenza_bollo") or "Non impostata")

        st.divider()

        # ==========================================
        # FORM REGISTRAZIONE MANUTENZIONI E REVISIONI
        # ==========================================
        st.subheader("🛠️ Registra Intervento o Revisione")

        # Categorie Manutenzione
        CATEGORIE_INTERVENTO = [
            "Tagliando Completo",
            "Cambio Olio e Filtri",
            "Freni (Pasticche / Dischi)",
            "Cinghia di Distribuzione",
            "Pneumatici / Cambio Stagionale",
            "Batteria",
            "Revisione Ministeriale",
            "Ricarica Clima",
            "Riparazione Meccanica",
            "Altro"
        ]

        with st.expander("➕ Inserisci Dettaglio Manutenzione / Revisione", expanded=True):
            with st.form("form_dettaglio_intervento"):
                col_a, col_b = st.columns(2)
                with col_a:
                    data_i = st.date_input("Data Intervento").strftime("%d/%m/%Y")
                    km_i = st.number_input("Km all'intervento", min_value=0, value=int(v.get("km_attuali", 0)))
                    categoria_i = st.selectbox("Tipo / Categoria Intervento", CATEGORIE_INTERVENTO)
                
                with col_b:
                    costo_i = st.number_input("Costo (€)", min_value=0.0, format="%.2f")
                    officina_i = st.text_input("Officina / Meccanico")
                    dettagli_i = st.text_area("Note / Componenti Sostituiti", placeholder="Es. Sostituite pasticche anteriori e liquido freni...")

                if st.form_submit_button("💾 SALVA INTERVENTO NEL DATABASE"):
                    if categoria_i:
                        nuovo_record = {
                            "data": data_i,
                            "km": km_i,
                            "categoria": categoria_i,
                            "costo": costo_i,
                            "officina": officina_i,
                            "note": dettagli_i
                        }
                        
                        storico.append(nuovo_record)
                        
                        # Se è una revisione, aggiorna anche la scadenza (fra 2 anni)
                        aggiornamenti = {
                            "storico_interventi": storico,
                            "km_attuali": max(km_i, v.get("km_attuali", 0))
                        }
                        
                        veicoli_ref.document(targa_selezionata).update(aggiornamenti)
                        st.success(f"Intervento '{categoria_i}' salvato con successo!")
                        st.rerun()

        st.divider()

        # ==========================================
        # STORICO DETTAGLIATO E RAGGRUPPATO
        # ==========================================
        st.subheader("📜 STORICO COMPLETO MANUTENZIONI E REVISIONI")

        if not storico:
            st.info("Nessuna manutenzione o revisione salvata per questo veicolo.")
        else:
            # Raggruppamento per Anno
            interventi_anno = {}
            for item in storico:
                parti_data = item.get("data", "").split("/")
                anno = parti_data[-1] if len(parti_data) == 3 else "Varie"
                interventi_anno.setdefault(anno, []).append(item)

            for anno in sorted(interventi_anno.keys(), reverse=True):
                spesa_totale_anno = sum(i.get("costo", 0.0) for i in interventi_anno[anno])
                st.markdown(f"### 📅 Anno {anno} — Totale Spesa: **{spesa_totale_anno:.2f} €**")
                
                for idx, item in enumerate(reversed(interventi_anno[anno])):
                    cat = item.get("categoria", "Manutenzione Generica")
                    costo = item.get("costo", 0.0)
                    km_rec = format_km(item.get("km", 0))
                    dt = item.get("data", "N/D")
                    off = item.get("officina", "")
                    note = item.get("note", "")
                    
                    titolo_box = f"🔧 **{cat}** | 🗓️ {dt} | 📍 {km_rec} Km | 💶 {costo:.2f} €"
                    if off:
                        titolo_box += f" | 🏢 Officina: {off}"
                        
                    with st.expander(titolo_box):
                        if note:
                            st.write(f"**Dettagli e Note:** {note}")
                        else:
                            st.caption("Nessuna nota aggiuntiva inserita.")
