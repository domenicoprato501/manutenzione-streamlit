import json
import datetime
import hashlib
import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

# -----------------------------------------------------------------------------
# 1. CONFIGURAZIONE PAGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Garage Manager Pro 📱",
    page_icon="🚗",
    layout="centered"
)

# -----------------------------------------------------------------------------
# 2. CONNESSIONE FIRESTORE
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
# FUNZIONI DI SUPPORTO & HASHING
# -----------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Restituisce l'hash SHA-256 della password."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_default_vehicle_data():
    return {
        "modello": "Non specificato",
        "km_attuali": 0,
        "ultimo_cambio_olio": 0,
        "tipo_olio_corrente": "Non specificato",
        "ultimo_filtro_olio": 0,
        "ultimo_filtro_aria": 0,
        "ultimo_filtro_abitacolo": 0,
        "ultimo_filtro_carburante": 0,
        "pastiglie_anteriori": 0,
        "pastiglie_posteriori": 0,
        "dischi_anteriori": 0,
        "dischi_posteriore": 0,
        "km_ultima_inversione": 0,
        "data_ultima_inversione": "Mai fatta",
        "data_cambio_gomme": "Non inserita",
        "scadenza_revisione": "Non inserita",
        "scadenza_bollo": "Non inserita",
        "scadenza_assicurazione": "Non inserita",
        "scadenza_bombole": "Non inserita",
        "scadenza_tergicristalli_ant": "Non inserita",
        "scadenza_tergicristalli_post": "Non inserita",
        "note_storiche": {},
        "storico_interventi": []
    }

def giorni_a_scadenza(data_str):
    if data_str in ["Non inserita", "Mai fatta", ""] or not data_str:
        return None
    try:
        dt = datetime.datetime.strptime(data_str, "%d/%m/%Y").date()
        return (dt - datetime.date.today()).days
    except:
        return None

def format_km(km_val):
    return f"{km_val:,}".replace(",", ".")

# -----------------------------------------------------------------------------
# 3. SISTEMA DI LOGIN E REGISTRAZIONE
# -----------------------------------------------------------------------------
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Accesso a Garage Manager Pro 📱")
    
    tab_login, tab_register = st.tabs(["🔑 Accedi", "📝 Registrati"])

    # --- TAB LOGIN ---
    with tab_login:
        with st.form("form_login"):
            user_input = st.text_input("Username", key="login_user").strip()
            pwd_input = st.text_input("Password", type="password", key="login_pwd").strip()
            submit_login = st.form_submit_button("Accedi", use_container_width=True)
            
            if submit_login:
                if not user_input or not pwd_input:
                    st.warning("Compila tutti i campi!")
                else:
                    secrets_passwords = st.secrets.get("passwords", {})
                    user_doc = db.collection("utenti").document(user_input).get()
                    
                    hashed_input = hash_password(pwd_input)
                    is_valid = False

                    if user_input in secrets_passwords:
                        secret_val = str(secrets_passwords[user_input])
                        if secret_val == pwd_input or secret_val == hashed_input:
                            is_valid = True
                    elif user_doc.exists:
                        stored_pwd = user_doc.to_dict().get("password")
                        if stored_pwd == hashed_input:
                            is_valid = True

                    if is_valid:
                        st.session_state["password_correct"] = True
                        st.session_state["current_user"] = user_input
                        st.rerun()
                    else:
                        st.error("❌ Username o password errati")

    # --- TAB REGISTRAZIONE ---
    with tab_register:
        with st.form("form_register"):
            new_user = st.text_input("Scegli un Username", key="reg_user").strip()
            new_pwd = st.text_input("Scegli una Password", type="password", key="reg_pwd").strip()
            confirm_pwd = st.text_input("Conferma Password", type="password", key="reg_pwd_confirm").strip()
            submit_reg = st.form_submit_button("Crea Account", type="primary", use_container_width=True)
            
            if submit_reg:
                if not new_user or not new_pwd or not confirm_pwd:
                    st.warning("Compila tutti i campi!")
                elif new_pwd != confirm_pwd:
                    st.error("❌ Le password non coincidono")
                else:
                    user_ref = db.collection("utenti").document(new_user)
                    if user_ref.get().exists or new_user in st.secrets.get("passwords", {}):
                        st.error("❌ Questo username è già esistente. Scegli un altro nome.")
                    else:
                        user_ref.set({
                            "password": hash_password(new_pwd),
                            "data_creazione": datetime.date.today().strftime("%d/%m/%Y")
                        })
                        st.success("✅ Account creato con successo! Ora puoi effettuare l'accesso dal tab 'Accedi'.")

    return False

if not check_password():
    st.stop()

# -----------------------------------------------------------------------------
# 4. RIFERIMENTO AL GARAGE DELL'UTENTE CORRENTE
# -----------------------------------------------------------------------------
current_user = st.session_state.get("current_user", "Admin")
# Riferimento dinamico alla sotto-collezione riservata all'utente attivo
veicoli_user_ref = db.collection("utenti").document(current_user).collection("veicoli")

# -----------------------------------------------------------------------------
# 5. SIDEBAR: LISTA VEICOLI PERSONALI
# -----------------------------------------------------------------------------
st.sidebar.title("Garage Manager Pro 📱")
st.sidebar.write(f"👤 Utente: **{current_user}**")
if st.sidebar.button("Logout"):
    st.session_state["password_correct"] = False
    st.session_state["current_user"] = None
    st.rerun()

st.sidebar.divider()

# Recupera solo i veicoli associati a questo specifico utente
docs = veicoli_user_ref.stream()
veicoli_dict = {doc.id: doc.to_dict() for doc in docs}
targhe_list = sorted(list(veicoli_dict.keys()))

st.sidebar.subheader("🚗 I Miei Veicoli")
targa_selezionata = st.sidebar.selectbox("Seleziona un mezzo", options=["-- Seleziona --"] + targhe_list)

with st.sidebar.expander("➕ / 🗑️ Gestisci Mezzi"):
    nuova_targa = st.text_input("Targa Mezzo").upper().strip()
    nuovo_modello = st.text_input("Modello (es. Fiat Punto)").strip()
    if st.button("➕ AGGIUNGI MEZZO", use_container_width=True):
        if nuova_targa:
            if nuova_targa in veicoli_dict:
                st.warning("Hai già un veicolo con questa targa!")
            else:
                dati_v = get_default_vehicle_data()
                dati_v["modello"] = nuovo_modello if nuovo_modello else "Non specificato"
                veicoli_user_ref.document(nuova_targa).set(dati_v)
                st.success(f"Veicolo {nuova_targa} aggiunto al tuo garage!")
                st.rerun()

    st.divider()
    targa_elimina = st.text_input("Scrivi targa da eliminare").upper().strip()
    if st.button("🗑️ RIMUOVI MEZZO", type="primary", use_container_width=True):
        if targa_elimina in veicoli_dict:
            veicoli_user_ref.document(targa_elimina).delete()
            st.success(f"Veicolo {targa_elimina} rimosso dal tuo garage!")
            st.rerun()

# -----------------------------------------------------------------------------
# 6. SCHERMATA DETTAGLIO VEICOLO
# -----------------------------------------------------------------------------
if targa_selezionata and targa_selezionata != "-- Seleziona --":
    v_ref = veicoli_user_ref.document(targa_selezionata)
    v = v_ref.get().to_dict() or get_default_vehicle_data()
    km = v.get("km_attuali", 0)
    modello_v = v.get("modello", "Non specificato")

    st.header(f"📱 Scheda: {targa_selezionata}")
    st.caption(f"🚘 **Modello:** {modello_v}")

    # === 1. SEZIONE DOCUMENTI ===
    st.subheader("=== SCADENZE DOCUMENTI ===")
    documenti = [
        ("Revisione", "scadenza_revisione"),
        ("Bollo", "scadenza_bollo"),
        ("Assicurazione", "scadenza_assicurazione"),
        ("Revisione Bombole", "scadenza_bombole")
    ]
    for tipo, campo in documenti:
        scad = v.get(campo, "Non inserita")
        giorni = giorni_a_scadenza(scad)
        
        if giorni is not None and giorni < 0:
            st.error(f"• {tipo}: {scad} (Scaduto da {-giorni} giorni)")
        elif giorni is not None:
            st.success(f"• {tipo}: {scad} (Scade tra {giorni} giorni)")
        else:
            st.info(f"• {tipo}: {scad}")

    st.divider()

    # === 2. SEZIONE MECCANICA ===
    st.subheader(f"=== MECCANICA (Odom: {format_km(km)} Km) ===")
    
    # Olio Motore
    km_olio = km - v.get('ultimo_cambio_olio', 0)
    spec_olio = v.get("tipo_olio_corrente", "Non specificato")
    msg_olio = f"• Olio Motore ({spec_olio}): Usati {format_km(km_olio)}/15.000 Km"
    if km_olio >= 15000:
        st.error(msg_olio)
    else:
        st.success(msg_olio)

    # Filtri
    filtri = [
        ("Filtro Olio", "ultimo_filtro_olio"),
        ("Filtro Aria", "ultimo_filtro_aria"),
        ("Filtro Abitacolo", "ultimo_filtro_abitacolo"),
        ("Filtro Carburante", "ultimo_filtro_carburante")
    ]
    for n, c in filtri:
        km_f = km - v.get(c, 0)
        msg_f = f"• {n}: Usati {format_km(km_f)}/20.000 Km"
        if km_f >= 20000:
            st.error(msg_f)
        else:
            st.success(msg_f)

    # Pastiglie & Dischi
    p_ant = km - v.get('pastiglie_anteriori', 0)
    p_post = km - v.get('pastiglie_posteriori', 0)
    st.success(f"• Pastiglie ANT: {format_km(p_ant)}/40.000 Km | POST: {format_km(p_post)}/60.000 Km")

    d_ant = km - v.get('dischi_anteriori', 0)
    d_post = km - v.get('dischi_posteriore', 0)
    st.success(f"• Dischi ANT: {format_km(d_ant)}/80.000 Km | POST: {format_km(d_post)}/100.000 Km")

    # Inversione & Cambio Gomme
    km_inv = km - v.get('km_ultima_inversione', 0)
    data_inv = v.get('data_ultima_inversione', 'Mai fatta')
    st.success(f"• Inversione Gomme: Fatti {format_km(km_inv)}/10.000 Km | Data: {data_inv}")

    ultimo_cambio_g = v.get('data_cambio_gomme', 'Non inserita')
    st.success(f"• Ultimo Cambio Gomme: {ultimo_cambio_g}")

    # Tergicristalli
    for tipo, campo in [("Tergicristalli ANT", "scadenza_tergicristalli_ant"), ("Tergicristalli POST", "scadenza_tergicristalli_post")]:
        scad = v.get(campo, "Non inserita")
        giorni = giorni_a_scadenza(scad)
        if giorni is not None and giorni < 0:
            st.error(f"• {tipo}: {scad}")
        elif giorni is not None:
            st.success(f"• {tipo}: {scad}")
        else:
            st.info(f"• {tipo}: {scad}")

    st.divider()

    # === 3. SEZIONE INTERVENTI RAPIDI ===
    st.subheader("=== INTERVENTI RAPIDI ===")

    # Aggiorna KM / Modello
    with st.popover("📊 AGGIORNA KM / MODELLO", use_container_width=True):
        n_km = st.number_input("Chilometri attuali", value=km, step=100)
        n_mod = st.text_input("Modello Veicolo", value=modello_v)
        if st.button("SALVA DATI", use_container_width=True):
            v["km_attuali"] = int(n_km)
            v["modello"] = n_mod.strip() or "Non specificato"
            v_ref.set(v)
            st.rerun()

    # Intervento Straordinario
    with st.popover("🛠️ INTERVENTO GENERICO / STRAORDINARIO", use_container_width=True):
        titolo_straord = st.text_input("Titolo Intervento (es. Cinghia Distribuzione, Batteria)")
        costo_straord = st.number_input("Costo (€)", min_value=0.0, value=0.0, step=10.0)
        data_straord = st.date_input("Data Intervento", value=datetime.date.today())
        note_straord = st.text_area("Note / Officina / Dettagli Ricambi")
        if st.button("SALVA INTERVENTO STRAORDINARIO", type="primary", use_container_width=True):
            if titolo_straord.strip():
                data_str = data_straord.strftime("%d/%m/%Y")
                desc = f"{titolo_straord.strip()}"
                if note_straord.strip():
                    desc += f" [Note: {note_straord.strip()}]"
                
                v.setdefault("storico_interventi", []).append({
                    "data": data_str,
                    "lavoro": desc,
                    "km": v["km_attuali"],
                    "costo": costo_straord
                })
                v_ref.set(v)
                st.success("Intervento registrato con successo!")
                st.rerun()
            else:
                st.warning("Inserisci almeno il titolo dell'intervento!")

    # Inversione e Cambio Gomme
    c1, c2 = st.columns(2)
    with c1:
        with st.popover("🔄 INVERSIONE", use_container_width=True):
            c_inv = st.number_input("Costo Inversione (€)", min_value=0.0, value=0.0)
            note_inv = st.text_input("Note / Dettagli Officina")
            if st.button("SALVA INVERSIONE", use_container_width=True):
                oggi_str = datetime.date.today().strftime("%d/%m/%Y")
                v["km_ultima_inversione"] = v["km_attuali"]
                v["data_ultima_inversione"] = oggi_str
                desc = f"Inversione Gomme [Note: {note_inv.strip() or 'N/D'}]"
                v.setdefault("storico_interventi", []).append({"data": oggi_str, "lavoro": desc, "km": v["km_attuali"], "costo": c_inv})
                v_ref.set(v)
                st.rerun()

    with c2:
        with st.popover("🛞 CAMBIO GOMME", use_container_width=True):
            c_cg = st.number_input("Costo Totale (€)", min_value=0.0, value=0.0)
            m_cg = st.text_input("Marca Pneumatici Nuovi")
            cod_cg = st.text_input("Modello / Misura")
            if st.button("SALVA CAMBIO", use_container_width=True):
                oggi_str = datetime.date.today().strftime("%d/%m/%Y")
                v["data_cambio_gomme"] = oggi_str
                v["km_ultima_inversione"] = v["km_attuali"]
                v["data_ultima_inversione"] = oggi_str
                desc = f"Sostituzione Pneumatici Nuovi [{m_cg.strip() or 'Generica'} - {cod_cg.strip() or 'N/D'}]"
                v.setdefault("storico_interventi", []).append({"data": oggi_str, "lavoro": desc, "km": v["km_attuali"], "costo": c_cg})
                v_ref.set(v)
                st.rerun()

    # Tergicristalli
    c3, c4 = st.columns(2)
    with c3:
        with st.popover("🧹 TERGI ANT", use_container_width=True):
            d_t_ant = st.date_input("Scadenza Tergi ANT")
            if st.button("SALVA TERGI ANT", use_container_width=True):
                v["scadenza_tergicristalli_ant"] = d_t_ant.strftime("%d/%m/%Y")
                v_ref.set(v)
                st.rerun()
    with c4:
        with st.popover("🧹 TERGI POST", use_container_width=True):
            d_t_post = st.date_input("Scadenza Tergi POST")
            if st.button("SALVA TERGI POST", use_container_width=True):
                v["scadenza_tergicristalli_post"] = d_t_post.strftime("%d/%m/%Y")
                v_ref.set(v)
                st.rerun()

    # Pastiglie
    c5, c6 = st.columns(2)
    for col, nome, campo in [(c5, "🛑 PAST. ANT", "pastiglie_anteriori"), (c6, "🛑 PAST. POST", "pastiglie_posteriori")]:
        with col:
            with st.popover(nome, use_container_width=True):
                costo = st.number_input(f"Costo (€) - {nome}", min_value=0.0, value=0.0)
                marca = st.text_input(f"Marca - {nome}")
                codice = st.text_input(f"Codice - {nome}")
                if st.button(f"SALVA {nome}", use_container_width=True):
                    v[campo] = v["km_attuali"]
                    oggi_str = datetime.date.today().strftime("%d/%m/%Y")
                    desc = f"{nome.replace('🛑 ', '')} [{marca.strip() or 'Generica'} - Cod:{codice.strip() or 'N/D'}]"
                    v.setdefault("storico_interventi", []).append({"data": oggi_str, "lavoro": desc, "km": v["km_attuali"], "costo": costo})
                    v_ref.set(v)
                    st.rerun()

    # Dischi
    c7, c8 = st.columns(2)
    for col, nome, campo in [(c7, "💿 DISCHI ANT", "dischi_anteriori"), (c8, "💿 DISCHI POST", "dischi_posteriore")]:
        with col:
            with st.popover(nome, use_container_width=True):
                costo = st.number_input(f"Costo (€) - {nome}", min_value=0.0, value=0.0)
                marca = st.text_input(f"Marca - {nome}")
                codice = st.text_input(f"Codice - {nome}")
                if st.button(f"SALVA {nome}", use_container_width=True):
                    v[campo] = v["km_attuali"]
                    oggi_str = datetime.date.today().strftime("%d/%m/%Y")
                    desc = f"{nome.replace('💿 ', '')} [{marca.strip() or 'Generica'} - Cod:{codice.strip() or 'N/D'}]"
                    v.setdefault("storico_interventi", []).append({"data": oggi_str, "lavoro": desc, "km": v["km_attuali"], "costo": costo})
                    v_ref.set(v)
                    st.rerun()

    # Documenti
    c9, c10, c11, c12 = st.columns(4)
    doc_buttons = [
        (c9, "📅 REV", "scadenza_revisione"),
        (c10, "📅 BOLLO", "scadenza_bollo"),
        (c11, "🛡️ ASSIC", "scadenza_assicurazione"),
        (c12, "🔥 BOMBOLE", "scadenza_bombole")
    ]
    for col, nome, campo in doc_buttons:
        with col:
            with st.popover(nome, use_container_width=True):
                d_scad = st.date_input(f"Scadenza {nome}")
                if st.button(f"SALVA {nome}", use_container_width=True):
                    v[campo] = d_scad.strftime("%d/%m/%Y")
                    v_ref.set(v)
                    st.rerun()

    st.divider()

    # === 4. SEZIONE MANUTENZIONE COMPLETA ===
    st.subheader("=== MANUTENZIONE COMPLETA ===")
    with st.expander("🛠️ COMPONI TAGLIANDO COMPLETO (OLIO E FILTRI) ➕"):
        filtri_config = [
            ("🛢️ Olio Motore + Tipo Olio", "ultimo_cambio_olio"),
            ("🛢️ F. Olio Motore", "ultimo_filtro_olio"),
            ("💨 Filtro Aria", "ultimo_filtro_aria"),
            ("🍃 Filtro Abitacolo", "ultimo_filtro_abitacolo"),
            ("⛽ Filtro Carburante", "ultimo_filtro_carburante")
        ]

        elementi_selezionati = []
        costo_totale_tagliando = 0.0

        for nome, chiave in filtri_config:
            attivo = st.checkbox(nome, key=f"tg_sw_{chiave}")
            if attivo:
                cx, cy, cz = st.columns([1, 1.5, 1.5])
                prezzo = cx.number_input("Prezzo (€)", min_value=0.0, value=0.0, key=f"tg_p_{chiave}")
                marca = cy.text_input("Marca", key=f"tg_m_{chiave}")
                codice = cz.text_input("Cod. Ricambio", key=f"tg_c_{chiave}")
                
                spec_olio_val = ""
                if chiave == "ultimo_cambio_olio":
                    spec_olio_val = st.text_input("Specifica Olio (es. 5W-30, 0W-20)", key=f"tg_spec_{chiave}")

                costo_totale_tagliando += prezzo
                elementi_selezionati.append((chiave, nome, prezzo, marca, codice, spec_olio_val))

        if st.button("REGISTRA COMPLETO", type="primary", use_container_width=True):
            if elementi_selezionati:
                oggi_str = datetime.date.today().strftime("%d/%m/%Y")
                filtri_cambiati = []

                for chiave, nome, prezzo, marca, codice, spec in elementi_selezionati:
                    v[chiave] = v["km_attuali"]
                    m_str = marca.strip() or "Generica"
                    c_str = codice.strip() or "N/D"

                    if chiave == "ultimo_cambio_olio" and spec:
                        spec_p = spec.strip().upper() or "NON SPECIFICATO"
                        v["tipo_olio_corrente"] = spec_p
                        nome_p = f"Cambio Olio Motore ({spec_p})"
                    else:
                        nome_p = chiave.replace("ultimo_", "").replace("_", " ").title()

                    filtri_cambiati.append(f"{nome_p} ({m_str} - Cod:{c_str}) [{prezzo}€]")

                desc_completa = "Tagliando Completo: " + ", ".join(filtri_cambiati)
                v.setdefault("storico_interventi", []).append({
                    "data": oggi_str,
                    "lavoro": desc_completa,
                    "km": v["km_attuali"],
                    "costo": costo_totale_tagliando
                })
                v_ref.set(v)
                st.success("Tagliando salvato!")
                st.rerun()

    st.divider()

    # === 5. SEZIONE NOTE GIORNALIERE E STORICO DIARIO ===
    st.subheader("=== NOTE E PROMEMORIA DIARIO ===")
    oggi_str = datetime.date.today().strftime("%d/%m/%Y")
    note_storiche = v.get("note_storiche", {})
    nota_oggi_corrente = note_storiche.get(oggi_str, "")

    with st.popover(f"📝 SCRIVI NOTA DI OGGI ({oggi_str})", use_container_width=True):
        t_nota = st.text_area("Scrivi la nota di oggi...", value=nota_oggi_corrente)
        if st.button("SALVA NOTA", use_container_width=True):
            if t_nota.strip():
                v.setdefault("note_storiche", {})[oggi_str] = t_nota.strip()
            else:
                if "note_storiche" in v and oggi_str in v["note_storiche"]:
                    del v["note_storiche"][oggi_str]
            v_ref.set(v)
            st.rerun()

    if not note_storiche:
        st.caption("Nessuna nota nel diario.")
    else:
        st.markdown("**📌 Diario Note Passate:**")
        for data_nota in sorted(note_storiche.keys(), reverse=True):
            with st.expander(f"📌 Nota del {data_nota}: {note_storiche[data_nota][:30]}..."):
                t_modifica = st.text_area("Modifica nota:", value=note_storiche[data_nota], key=f"note_{data_nota}")
                if st.button("CORREGGI NOTA", key=f"btn_note_{data_nota}"):
                    if t_modifica.strip():
                        v["note_storiche"][data_nota] = t_modifica.strip()
                    else:
                        del v["note_storiche"][data_nota]
                    v_ref.set(v)
                    st.rerun()

    st.divider()

    # === 6. SEZIONE STORICO INTERVENTI PER ANNO ===
    st.subheader("📜 STORICO MANUTENZIONI")
    storico_lista = v.get("storico_interventi", [])

    if not storico_lista:
        st.caption("Nessun intervento registrato.")
    else:
        interventi_per_anno = {}
        for intervento in storico_lista:
            data_int = intervento.get("data", "01/01/2026")
            try:
                anno = data_int.split("/")[-1]
            except:
                anno = "Altro"
            
            interventi_per_anno.setdefault(anno, []).append(intervento)

        for anno in sorted(interventi_per_anno.keys(), reverse=True):
            totale_anno = sum(item.get("costo", 0.0) for item in interventi_per_anno[anno])
            st.markdown(f"#### 📅 --- ANNO {anno} (Totale: {totale_anno:.2f}€) ---")
            
            for intervento in reversed(interventi_per_anno[anno]):
                data_int = intervento.get("data", "Sconosciuta")
                lavoro_int = intervento.get("lavoro", "Intervento")
                km_int = intervento.get("km", 0)
                costo_int = intervento.get("costo", 0.0)
                
                st.info(f"🔧 **{lavoro_int}**\n\nData: {data_int} | Km: {format_km(km_int)} | Spesa: {costo_int:.2f}€")

else:
    st.info("👈 Seleziona un veicolo dal menu a sinistra per accedere alla tua scheda personale.")
