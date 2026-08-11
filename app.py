import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime
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

# Recupero Firebase Web API Key
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
# 2. FUNZIONI UTILI & CALCOLO SCADENZE
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

def verifica_stato_scadenza(data_str):
    if not data_str:
        return "non_impostata", "⚪ Non Impostata"
    try:
        parti = data_str.strip().split("/")
        if len(parti) == 2:
            mese, anno = int(parti[0]), int(parti[1])
        elif len(parti) == 3:
            mese, anno = int(parti[1]), int(parti[2])
        else:
            return "sconosciuta", f"❓ {data_str}"

        oggi = datetime.now()
        if anno < oggi.year or (anno == oggi.year and mese < oggi.month):
            return "scaduta", f"🚨 SCADUTO ({data_str})"
        elif anno == oggi.year and mese == oggi.month:
            return "in_scadenza", f"⚠️ IN SCADENZA ({data_str})"
        else:
            return "valida", f"✅ REGOLARE ({data_str})"
    except Exception:
        return "sconosciuta", f"ℹ️ {data_str}"

# Stato Sessione
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
    st.title("🚗 Gestione Parco Auto Personale")
    
    tab_login, tab_registrazione = st.tabs(["🔑 Accedi", "📝 Registrati"])
    
    with tab_login:
        st.subheader("Accedi ai tuoi veicoli")
        input_login = st.text_input("Email o Username", key="login_user").strip().lower()
        password_login = st.text_input("Password", type="password", key="login_pass").strip()
        
        if st.button("ACCEDI", use_container_width=True):
            if not input_login or not password_login:
                st.error("Compila tutti i campi.")
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
        st.subheader("Crea un account personale")
        username_reg = st.text_input("Username", key="reg_user").strip().lower()
        email_reg = st.text_input("Email", key="reg_email").strip().lower()
        password_reg = st.text_input("Password (min. 6 caratteri)", type="password", key="reg_pass").strip()
        
        if st.button("REGISTRATI", use_container_width=True):
            if not username_reg or not email_reg or not password_reg:
                st.error("Compila tutti i campi.")
            elif "@" in username_reg:
                st.error("Lo username non può contenere la '@'.")
            elif len(password_reg) < 6:
                st.error("La password deve contenere almeno 6 caratteri.")
            else:
                try:
                    if db.collection("utenti").document(username_reg).get().exists:
                        st.error("Username già occupato.")
                    else:
                        user = admin_auth.create_user(email=email_reg, password=password_reg, display_name=username_reg)
                        db.collection("utenti").document(username_reg).set({"email": email_reg, "uid": user.uid})
                        st.success("Registrazione completata! Puoi accedere.")
                except admin_auth.EmailAlreadyExistsError:
                    st.error("Email già registrata.")
                except Exception as e:
                    st.error(f"Errore durante la registrazione: {e}")

# ==========================================
# 4. DASHBOARD PERSONALIZZATA UTENTE
# ==========================================
else:
    veicoli_ref = db.collection("veicoli")
    
    col_t, col_out = st.columns([4, 1])
    with col_t:
        st.title("🚗 Il Mio Parco Auto")
    with col_out:
        st.write(f"👤 Utente: **{st.session_state.username_corrente}**")
        if st.button("🚪 Esci"):
            st.session_state.autenticato = False
            st.session_state.utente_corrente = None
            st.session_state.username_corrente = None
            st.rerun()

    # Filtro isolamento utenti
    query_veicoli = veicoli_ref.where("utente", "==", st.session_state.utente_corrente).stream()
    dati_veicoli = {}
    for doc in query_veicoli:
        dict_v = doc.to_dict()
        targa_key = dict_v.get("targa", doc.id)
        dati_veicoli[targa_key] = (doc.id, dict_v)

    if not dati_veicoli:
        st.info("Nessun veicolo associato al tuo account. Aggiungi la tua prima auto.")
        with st.form("form_primo_veicolo"):
            st.subheader("➕ Aggiungi Nuovo Veicolo")
            targa_new = st.text_input("Targa Auto").upper().strip()
            modello_new = st.text_input("Marca / Modello (es. Fiat Punto 1.3 Multijet)")
            km_new = st.number_input("Chilometri Attuali", min_value=0, step=500)
            scad_rev_new = st.text_input("Scadenza Revisione (MM/AAAA)", placeholder="es. 10/2026")
            scad_bollo_new = st.text_input("Scadenza Bollo (MM/AAAA)", placeholder="es. 12/2026")
            
            if st.form_submit_button("💾 Salva Veicolo"):
                if targa_new:
                    doc_id = f"{st.session_state.username_corrente}_{targa_new}"
                    veicoli_ref.document(doc_id).set({
                        "utente": st.session_state.utente_corrente,
                        "username": st.session_state.username_corrente,
                        "targa": targa_new,
                        "modello": modello_new,
                        "km_attuali": km_new,
                        "scadenza_revisione": scad_rev_new,
                        "scadenza_bollo": scad_bollo_new,
                        "km_ultimo_tagliando": km_new,
                        "storico_interventi": []
                    })
                    st.success(f"Veicolo {targa_new} inserito con successo!")
                    st.rerun()
                else:
                    st.error("Inserisci la targa del veicolo.")
    else:
        # Selezione Veicolo
        targhe_disponibili = list(dati_veicoli.keys())
        targa_selezionata = st.sidebar.selectbox("🚘 Seleziona Veicolo", targhe_disponibili)
        doc_id_attuale, v = dati_veicoli[targa_selezionata]
        storico = v.get("storico_interventi", [])

        # Sidebar
        with st.sidebar:
            st.divider()
            st.header(f"📌 {targa_selezionata}")
            st.caption(f"Modello: {v.get('modello', 'N/D')}")
            
            nuovi_km = st.number_input("Aggiorna Km Attuali", min_value=0, value=int(v.get("km_attuali", 0)), step=100)
            if nuovi_km != v.get("km_attuali"):
                if st.button("💾 Aggiorna Km"):
                    veicoli_ref.document(doc_id_attuale).update({"km_attuali": nuovi_km})
                    st.success("Km aggiornati!")
                    st.rerun()

            st.divider()
            st.subheader("➕ Aggiungi altro Veicolo")
            with st.expander("Nuova Auto"):
                with st.form("form_altro_veicolo"):
                    t_new = st.text_input("Targa").upper().strip()
                    m_new = st.text_input("Modello")
                    k_new = st.number_input("Km", min_value=0, step=500)
                    if st.form_submit_button("Aggiungi"):
                        if t_new:
                            id_new = f"{st.session_state.username_corrente}_{t_new}"
                            veicoli_ref.document(id_new).set({
                                "utente": st.session_state.utente_corrente,
                                "username": st.session_state.username_corrente,
                                "targa": t_new,
                                "modello": m_new,
                                "km_attuali": k_new,
                                "scadenza_revisione": "",
                                "scadenza_bollo": "",
                                "km_ultimo_tagliando": k_new,
                                "storico_interventi": []
                            })
                            st.rerun()

            if storico:
                st.divider()
                st.subheader("📊 Esportazione")
                df_csv = pd.DataFrame(storico)
                st.download_button(
                    label="📥 Scarica Report CSV",
                    data=df_csv.to_csv(index=False).encode("utf-8"),
                    file_name=f"storico_{targa_selezionata}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        # ==========================================
        # 5. AVVISI & SCADENZE
        # ==========================================
        st.subheader("⚠️ Avvisi & Scadenze Veicolo")
        
        stato_rev, msg_rev = verifica_stato_scadenza(v.get("scadenza_revisione"))
        stato_bollo, msg_bollo = verifica_stato_scadenza(v.get("scadenza_bollo"))
        
        km_attuali = v.get("km_attuali", 0)
        km_ultimo_tagl = v.get("km_ultimo_tagliando", 0)
        km_da_tagliando = km_attuali - km_ultimo_tagl
        
        c_rev, c_bollo, c_tagl = st.columns(3)
        
        with c_rev:
            st.metric("Revisione Ministeriale", v.get("scadenza_revisione") or "N/D")
            if stato_rev == "scaduta":
                st.error(msg_rev)
            elif stato_rev == "in_scadenza":
                st.warning(msg_rev)
            else:
                st.success(msg_rev)

        with c_bollo:
            st.metric("Bollo Auto", v.get("scadenza_bollo") or "N/D")
            if stato_bollo == "scaduta":
                st.error(msg_bollo)
            elif stato_bollo == "in_scadenza":
                st.warning(msg_bollo)
            else:
                st.success(msg_bollo)

        with c_tagl:
            st.metric("Km dall'ultimo Tagliando", f"{format_km(km_da_tagliando)} Km")
            if km_da_tagliando >= 15000:
                st.error(f"🚨 TAGLIANDO CONSIGLIATO (+{format_km(km_da_tagliando)} Km)")
            elif km_da_tagliando >= 12000:
                st.warning(f"⚠️ Tagliando Vicino ({format_km(km_da_tagliando)} Km)")
            else:
                st.success("✅ Tagliando OK")

        st.divider()

        # ==========================================
        # 6. REGISTRAZIONE MANUTENZIONI CON RICAMBI
        # ==========================================
        st.subheader("🛠️ Registra Intervento Manutenzione")

        tab_rapida, tab_completa, tab_scadenze = st.tabs([
            "⚡ Manutenzione Rapida", 
            "🛠️ Manutenzione Completa (con Ricambi)",
            "📅 Aggiorna Scadenze Legali"
        ])

        # --- TAB 1: MANUTENZIONE RAPIDA ---
        with tab_rapida:
            st.caption("Registrazione rapida di spesa e descrizione senza dettagli aggiuntivi.")
            with st.form("form_rapido"):
                c_r1, c_r2, c_r3 = st.columns([1, 1, 1])
                with c_r1:
                    data_r = st.date_input("Data Intervento", key="dt_r").strftime("%d/%m/%Y")
                    km_r = st.number_input("Km al momento", min_value=0, value=int(km_attuali), key="km_r")
                with c_r2:
                    lavoro_r = st.text_input("Descrizione lavoro veloce", placeholder="Es. Rabbocco liquido lavavetri", key="lab_r")
                    costo_r = st.number_input("Costo Totale (€)", min_value=0.0, format="%.2f", key="c_r")
                with c_r3:
                    st.write("")
                    st.write("")
                    btn_rapido = st.form_submit_button("⚡ SALVA RAPIDO", use_container_width=True)

                if btn_rapido:
                    if lavoro_r.strip():
                        nuovo_i = {
                            "tipo": "Rapida",
                            "data": data_r,
                            "km": km_r,
                            "categoria": "Generica / Rapida",
                            "lavoro": lavoro_r,
                            "costo": costo_r,
                            "officina": "-",
                            "codice_ricambio": "",
                            "descrizione_ricambio": "",
                            "prezzo_ricambio": 0.0,
                            "note": ""
                        }
                        storico.append(nuovo_i)
                        veicoli_ref.document(doc_id_attuale).update({
                            "storico_interventi": storico,
                            "km_attuali": max(km_r, km_attuali)
                        })
                        st.success("Intervento rapido registrato!")
                        st.rerun()
                    else:
                        st.error("Inserisci la descrizione del lavoro.")

        # --- TAB 2: MANUTENZIONE COMPLETA CON CODICE E PREZZO RICAMBIO ---
        with tab_completa:
            st.caption("Scheda dettagliata con officina, campo ricambi (codice/descrizione/prezzo) e azzeramento tagliando.")
            CATEGORIE = [
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
            with st.form("form_completo"):
                ca, cb = st.columns(2)
                with ca:
                    data_c = st.date_input("Data Intervento", key="dt_c").strftime("%d/%m/%Y")
                    km_c = st.number_input("Chilometraggio", min_value=0, value=int(km_attuali), key="km_c")
                    categoria_c = st.selectbox("Categoria Intervento", CATEGORIE, key="cat_c")
                    officina_c = st.text_input("Officina / Meccanico", placeholder="Es. Garage Rossi SRL", key="off_c")
                
                with cb:
                    costo_c = st.number_input("Costo Totale Intervento (€)", min_value=0.0, format="%.2f", key="c_c")
                    note_c = st.text_area("Note e Dettagli Aggiuntivi", placeholder="Es. Sostituito olio 5W30 e filtro aria.", key="nt_c")
                    is_tagliando = st.checkbox("Segna come Tagliando Completo (Azzera i km dal prossimo tagliando)", value=(categoria_c in ["Tagliando Completo", "Cambio Olio e Filtri"]))

                st.markdown("---")
                st.markdown("##### 🔩 Dettaglio Pezzo di Ricambio (Opzionale)")
                cr1, cr2, cr3 = st.columns(3)
                with cr1:
                    cod_ric = st.text_input("Codice Ricambio", placeholder="Es. BOSCH-0986479098", key="cod_ric")
                with cr2:
                    desc_ric = st.text_input("Descrizione Ricambio", placeholder="Es. Dischi Freno Anteriori", key="desc_ric")
                with cr3:
                    prz_ric = st.number_input("Prezzo Ricambio (€)", min_value=0.0, format="%.2f", key="prz_ric")

                if st.form_submit_button("💾 SALVA SCHEDA COMPLETA", use_container_width=True):
                    if categoria_c:
                        nuovo_c = {
                            "tipo": "Completa",
                            "data": data_c,
                            "km": km_c,
                            "categoria": categoria_c,
                            "lavoro": categoria_c,
                            "costo": costo_c,
                            "officina": officina_c,
                            "codice_ricambio": cod_ric.strip(),
                            "descrizione_ricambio": desc_ric.strip(),
                            "prezzo_ricambio": prz_ric,
                            "note": note_c
                        }
                        storico.append(nuovo_c)
                        
                        upd = {
                            "storico_interventi": storico,
                            "km_attuali": max(km_c, km_attuali)
                        }
                        if is_tagliando:
                            upd["km_ultimo_tagliando"] = km_c
                            
                        veicoli_ref.document(doc_id_attuale).update(upd)
                        st.success(f"Intervento completo '{categoria_c}' registrato con successo!")
                        st.rerun()

        # --- TAB 3: AGGIORNA SCADENZE ---
        with tab_scadenze:
            with st.form("form_aggiorna_scadenze"):
                st.write("Modifica le date di scadenza legali per il veicolo:")
                c_s1, c_s2 = st.columns(2)
                with c_s1:
                    nuova_rev = st.text_input("Nuova Scadenza Revisione (MM/AAAA)", value=v.get("scadenza_revisione", ""))
                with c_s2:
                    nuovo_bollo = st.text_input("Nuova Scadenza Bollo (MM/AAAA)", value=v.get("scadenza_bollo", ""))
                
                if st.form_submit_button("💾 Salva Nuove Scadenze"):
                    veicoli_ref.document(doc_id_attuale).update({
                        "scadenza_revisione": nuova_rev,
                        "scadenza_bollo": nuovo_bollo
                    })
                    st.success("Scadenze aggiornate!")
                    st.rerun()

        st.divider()

        # ==========================================
        # 7. STORICO MANUTENZIONI CON VISUALIZZAZIONE RICAMBI
        # ==========================================
        st.subheader("📜 STORICO INTERVENTI & RICAMBI")

        if not storico:
            st.info("Nessun intervento registrato per questa auto.")
        else:
            interventi_per_anno = {}
            for item in storico:
                parti = item.get("data", "").split("/")
                anno = parti[-1] if len(parti) == 3 else "Vari"
                interventi_per_anno.setdefault(anno, []).append(item)

            for anno in sorted(interventi_per_anno.keys(), reverse=True):
                totale_spesa_anno = sum(i.get("costo", 0.0) for i in interventi_per_anno[anno])
                st.markdown(f"### 📅 Anno {anno} — Spesa Totale: **{totale_spesa_anno:.2f} €**")
                
                for item in reversed(interventi_per_anno[anno]):
                    tipo_int = item.get("tipo", "Rapida")
                    cat = item.get("categoria", item.get("lavoro", "Manutenzione"))
                    costo = item.get("costo", 0.0)
                    km_i = format_km(item.get("km", 0))
                    dt = item.get("data", "N/D")
                    off = item.get("officina", "")
                    note = item.get("note", "")
                    lavoro = item.get("lavoro", "")

                    c_ric = item.get("codice_ricambio", "")
                    d_ric = item.get("descrizione_ricambio", "")
                    p_ric = item.get("prezzo_ricambio", 0.0)

                    badg = "⚡ RAPIDA" if tipo_int == "Rapida" else "🛠️ COMPLETA"
                    titolo_expander = f"[{badg}] {cat} | 🗓️ {dt} | 📍 {km_i} Km | 💶 {costo:.2f} €"
                    
                    with st.expander(titolo_expander):
                        st.write(f"**Lavoro Eseguito:** {lavoro}")
                        if off and off != "-":
                            st.write(f"**Officina:** {off}")
                        
                        # Sezione Ricambi nel Dettaglio
                        if c_ric or d_ric or p_ric > 0:
                            st.markdown("---")
                            st.markdown("**🔩 Pezzo di Ricambio Sostituito:**")
                            c_col1, c_col2, c_col3 = st.columns(3)
                            if c_ric:
                                c_col1.write(f"🏷️ **Codice:** `{c_ric}`")
                            if d_ric:
                                c_col2.write(f"📝 **Descrizione:** {d_ric}")
                            if p_ric > 0:
                                c_col3.write(f"💶 **Costo Ricambio:** {p_ric:.2f} €")

                        if note:
                            st.write(f"**Note/Dettagli:** {note}")
