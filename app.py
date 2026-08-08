import datetime
import json
import os
import streamlit as st

# 1. UNICA CHIAMATA A SET_PAGE_CONFIG (DEVE ESSERE IN CIMA)
st.set_page_config(
    page_title="Garage Manager Pro 📱",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 2. NASCONDE MENU, FOOTER E PULSANTE GITHUB SENZA ROMPERE L'APP
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stAppHeader {display: none;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

FILE_DATI = "dati_veicoli_multipli.json"


class Garage:

  @staticmethod
  def carica():
    if not os.path.exists(FILE_DATI) or os.path.getsize(FILE_DATI) == 0:
      return {}
    try:
      with open(FILE_DATI, "r", encoding="utf-8") as f:
        return json.load(f)
    except:
      return {}

  @staticmethod
  def salva(dati):
    with open(FILE_DATI, "w", encoding="utf-8") as f:
      json.dump(dati, f, indent=4, ensure_ascii=False)

  @staticmethod
  def giorni_a_scadenza(data_str):
    if data_str == "Non inserita" or not data_str:
      return None
    try:
      dt = datetime.datetime.strptime(data_str, "%d/%m/%Y").date()
      return (dt - datetime.date.today()).days
    except:
      return None

  @staticmethod
  def assicura_struttura_veicolo(v):
    campi_default = {
        "nome_modello": "NON SPECIFICATO",
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
        "scadenza_tergicristalli_ant": "Non inserita",
        "scadenza_tergicristalli_post": "Non inserita",
        "note_storiche": {},
        "storico_interventi": [],
    }
    for chiave, valore in campi_default.items():
      if chiave not in v:
        v[chiave] = valore
    return v


dati = Garage.carica()

for k in dati.keys():
  Garage.assicura_struttura_veicolo(dati[k])

# --- BARRA LATERALE: SELEZIONE E GESTIONE MEZZI ---
st.sidebar.title("Garage Manager Pro 📱")


def formatta_opzione(targa):
  if targa == "-- Seleziona --":
    return targa
  modello = dati[targa].get("nome_modello", "").upper()
  if modello and modello != "NON SPECIFICATO":
    return f"{targa} ({modello})"
  return targa


targhe = list(dati.keys())
targa_selezionata = st.sidebar.selectbox(
    "🏎️ Seleziona Veicolo",
    options=["-- Seleziona --"] + targhe,
    format_func=formatta_opzione,
)

st.sidebar.divider()

# Aggiungi Veicolo
with st.sidebar.expander("➕ AGGIUNGI MEZZO"):
  nuova_targa = st.text_input("Targa (es. AB123CD)").strip().upper()
  nuovo_modello = st.text_input("Modello / Nome (es. Fiat Panda)").strip().upper()

  if st.button("Salva Nuovo Veicolo"):
    if nuova_targa in dati:
      st.error("Targa già esistente!")
    elif nuova_targa:
      dati[nuova_targa] = {
          "nome_modello": (
              nuovo_modello if nuovo_modello else "NON SPECIFICATO"
          ),
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
          "scadenza_tergicristalli_ant": "Non inserita",
          "scadenza_tergicristalli_post": "Non inserita",
          "note_storiche": {},
          "storico_interventi": [],
      }
      Garage.salva(dati)
      st.success("Veicolo aggiunto!")
      st.rerun()
    else:
      st.error("Inserisci almeno la Targa!")

# Rimuovi Veicolo
with st.sidebar.expander("🗑️ RIMUOVI MEZZO"):
  if dati:
    targa_del = st.selectbox(
        "Seleziona targa da eliminare",
        options=["-- Seleziona --"] + list(dati.keys()),
        key="del_sel_box",
    )
    if st.button("Conferma Elimina", type="primary"):
      if targa_del != "-- Seleziona --" and targa_del in dati:
        del dati[targa_del]
        Garage.salva(dati)
        st.success(f"Veicolo {targa_del} rimosso con successo!")
        st.rerun()
      else:
        st.warning("Seleziona una targa valida dalla lista.")
  else:
    st.info("Nessun veicolo presente nel garage.")

# --- SCHERMATA DETTAGLIO VEICOLO ---
if targa_selezionata and targa_selezionata != "-- Seleziona --":
  v = Garage.assicura_struttura_veicolo(dati[targa_selezionata])
  km = v.get("km_attuali", 0)

  modello_str = (
      f" - {v['nome_modello'].upper()}"
      if v["nome_modello"].upper() != "NON SPECIFICATO"
      else ""
  )
  st.header(f"🚗 Scheda Veicolo: {targa_selezionata.upper()}{modello_str}")

  with st.expander("✏️ Modifica Targa / Nome Modello"):
    col_m1, col_m2 = st.columns([3, 1])
    mod_nome = (
        col_m1.text_input(
            "Nome Modello / Descrizione", value=v.get("nome_modello", "").upper()
        )
        .strip()
        .upper()
    )
    if col_m2.button("Aggiorna Nome"):
      v["nome_modello"] = mod_nome
      Garage.salva(dati)
      st.success("Nome aggiornato in MAIUSCOLO!")
      st.rerun()

  c_km1, c_km2 = st.columns([3, 1])
  nuovi_km = c_km1.number_input(
      "📊 Chilometri Attuali Mezzo", value=km, step=100
  )
  if c_km2.button("💾 AGGIORNA KM"):
    v["km_attuali"] = nuovi_km
    Garage.salva(dati)
    st.success("Km aggiornati!")
    st.rerun()

  st.divider()

  col_doc, col_mec = st.columns(2)

  # 1. SCADENZE DOCUMENTI & TERGI
  with col_doc:
    st.subheader("📋 Scadenze Documenti & Tergi")

    doc_list = [
        ("Revisione", "scadenza_revisione"),
        ("Bollo", "scadenza_bollo"),
        ("Assicurazione", "scadenza_assicurazione"),
        ("Tergicristalli ANT", "scadenza_tergicristalli_ant"),
        ("Tergicristalli POST", "scadenza_tergicristalli_post"),
    ]

    for nome_doc, campo in doc_list:
      scad = v.get(campo, "Non inserita")
      giorni = Garage.giorni_a_scadenza(scad)

      c_label, c_date, c_btn = st.columns([2, 2, 1])
      if giorni is not None and giorni < 0:
        c_label.error(f"• {nome_doc}: {scad}")
      else:
        c_label.write(f"• **{nome_doc}**: {scad}")

      val_default = datetime.date.today()
      dt_input = c_date.date_input(
          f"Seleziona {nome_doc}",
          value=val_default,
          key=f"dt_{campo}",
          label_visibility="collapsed",
      )
      if c_btn.button("Salva", key=f"btn_{campo}"):
        v[campo] = dt_input.strftime("%d/%m/%Y")
        Garage.salva(dati)
        st.rerun()

  # 2. STATO MECCANICA E USURA
  with col_mec:
    st.subheader(f"⚙️ Meccanica (Odom: {km:,} Km)".replace(",", "."))

    km_olio = km - v.get("ultimo_cambio_olio", 0)
    spec_olio = v.get("tipo_olio_corrente", "Non specificato").upper()
    color_o = "🔴" if km_olio >= 15000 else "🟢"
    st.write(
        f"{color_o} **Olio Motore** ({spec_olio}): Usati {km_olio}/15.000 Km"
    )

    filtri = [
        ("Filtro Olio", "ultimo_filtro_olio"),
        ("Filtro Aria", "ultimo_filtro_aria"),
        ("Filtro Abitacolo", "ultimo_filtro_abitacolo"),
        ("Filtro Carburante", "ultimo_filtro_carburante"),
    ]
    for n, c in filtri:
      km_f = km - v.get(c, 0)
      color_f = "🔴" if km_f >= 20000 else "🟢"
      st.write(f"{color_f} **{n}**: Usati {km_f}/20.000 Km")

    p_ant = km - v.get("pastiglie_anteriori", 0)
    p_post = km - v.get("pastiglie_posteriori", 0)
    st.write(
        f"🛑 **Pastiglie**: ANT {p_ant}/40.000 Km | POST {p_post}/60.000 Km"
    )

    d_ant = km - v.get("dischi_anteriori", 0)
    d_post = km - v.get("dischi_posteriore", 0)
    st.write(f"💿 **Dischi**: ANT {d_ant}/80.000 Km | POST {d_post}/100.000 Km")

    km_inv = km - v.get("km_ultima_inversione", 0)
    data_inv = v.get("data_ultima_inversione", "Mai fatta")
    st.write(
        f"🔄 **Inversione Gomme**: Fatti {km_inv}/10.000 Km (Data: {data_inv})"
    )
    st.write(
        f"🛞 **Ultimo Cambio Gomme**: {v.get('data_cambio_gomme', 'Non inserita')}"
    )

  st.divider()

  # 3. INTERVENTI RAPIDI & GOMME
  st.subheader("🛠️ Interventi Rapidi Componenti")

  col_rap1, col_rap2, col_rap3 = st.columns(3)

  with col_rap1:
    with st.expander("🔄 Inversione Pneumatici"):
      costo_inv = st.number_input("Costo (€)", value=0.0, key="c_inv")
      note_inv = st.text_input("Note Inversione", key="n_inv").strip()
      if st.button("Registra Inversione"):
        oggi_str = datetime.date.today().strftime("%d/%m/%Y")
        v["km_ultima_inversione"] = km
        v["data_ultima_inversione"] = oggi_str
        v["storico_interventi"].append({
            "data": oggi_str,
            "lavoro": f"INVERSIONE GOMME [NOTE: {note_inv}]",
            "km": km,
            "costo": costo_inv,
        })
        Garage.salva(dati)
        st.success("Inversione registrata!")
        st.rerun()

  with col_rap2:
    with st.expander("🛞 Cambio Gomme Nuovo"):
      costo_g = st.number_input("Costo Totale (€)", value=0.0, key="c_g")
      marca_g = st.text_input("Marca Pneumatici", key="m_g").strip().upper()
      cod_g = st.text_input("Modello / Misura", key="cd_g").strip()
      if st.button("Registra Cambio Gomme"):
        oggi_str = datetime.date.today().strftime("%d/%m/%Y")
        v["data_cambio_gomme"] = oggi_str
        v["km_ultima_inversione"] = km
        v["data_ultima_inversione"] = oggi_str
        v["storico_interventi"].append({
            "data": oggi_str,
            "lavoro": (
                f"SOSTITUZIONE PNEUMATICI NUOVI [{marca_g} - {cod_g}]"
            ),
            "km": km,
            "costo": costo_g,
        })
        Garage.salva(dati)
        st.success("Cambio gomme salvato!")
        st.rerun()

  with col_rap3:
    with st.expander("🛑 Pastiglie / Dischi"):
      comp_scelta = st.selectbox(
          "Seleziona Componente",
          [
              ("Pastiglie Anteriori", "pastiglie_anteriori"),
              ("Pastiglie Posteriori", "pastiglie_posteriori"),
              ("Dischi Anteriori", "dischi_anteriori"),
              ("Dischi Posteriori", "dischi_posteriore"),
          ],
          format_func=lambda x: x[0],
      )
      costo_p = st.number_input("Costo (€)", value=0.0, key="c_p")
      marca_p = st.text_input("Marca Ricambio", key="m_p").strip().upper()
      cod_p = st.text_input("Codice Ricambio", key="cd_p").strip()
      if st.button("Registra Componente"):
        nome_c, chiave_c = comp_scelta
        v[chiave_c] = km
        oggi_str = datetime.date.today().strftime("%d/%m/%Y")
        v["storico_interventi"].append({
            "data": oggi_str,
            "lavoro": f"{nome_c.upper()} [{marca_p} - COD:{cod_p}]",
            "km": km,
            "costo": costo_p,
        })
        Garage.salva(dati)
        st.success(f"{nome_c} salvato!")
        st.rerun()

  st.divider()

  # 4. TAGLIANDO COMPLETO
  with st.expander(
      "🛠️ COMPONI TAGLIANDO COMPLETO (OLIO E FILTRI)", expanded=False
  ):
    st.write("Seleziona i componenti sostituiti durante questo tagliando:")

    filtri_tagliando = [
        ("🛢️ Olio Motore", "ultimo_cambio_olio"),
        ("🛢️ Filtro Olio Motore", "ultimo_filtro_olio"),
        ("💨 Filtro Aria", "ultimo_filtro_aria"),
        ("🍃 Filtro Abitacolo", "ultimo_filtro_abitacolo"),
        ("⛽ Filtro Carburante", "ultimo_filtro_carburante"),
    ]

    dati_tagliando_form = {}
    for nome_f, chiave_f in filtri_tagliando:
      c_sw, c_pr, c_mr, c_cd, c_sp = st.columns([2, 1.5, 2, 2, 2])
      attivo = c_sw.checkbox(nome_f, key=f"sw_{chiave_f}")
      prezzo = c_pr.number_input(
          "Prezzo €", value=0.0, key=f"pr_{chiave_f}", disabled=not attivo
      )
      marca = (
          c_mr.text_input(
              "Marca Ricambio", key=f"mr_{chiave_f}", disabled=not attivo
          )
          .strip()
          .upper()
      )
      codice = c_cd.text_input(
          "Codice Ricambio", key=f"cd_{chiave_f}", disabled=not attivo
      ).strip()

      spec_o = None
      if chiave_f == "ultimo_cambio_olio":
        spec_o = (
            c_sp.text_input(
                "Specifica Olio (es. 5W-30)", key="spec_o", disabled=not attivo
            )
            .strip()
            .upper()
        )

      dati_tagliando_form[chiave_f] = (attivo, prezzo, marca, codice, spec_o)

    if st.button("REGISTRA TAGLIANDO COMPLETO", type="primary"):
      filtri_cambiati = []
      costo_totale = 0.0
      oggi_str = datetime.date.today().strftime("%d/%m/%Y")

      for chiav, (att, prz, mrc, cod, spc) in dati_tagliando_form.items():
        if att:
          v[chiav] = km
          costo_totale += prz
          mrc_t = mrc or "GENERICA"
          cod_t = cod or "N/D"

          if chiav == "ultimo_cambio_olio" and spc:
            spc_t = spc or "NON SPECIFICATO"
            v["tipo_olio_corrente"] = spc_t
            nome_pulito = f"CAMBIO OLIO MOTORE ({spc_t})"
          else:
            nome_pulito = (
                chiav.replace("ultimo_", "").replace("_", " ").upper()
            )

          filtri_cambiati.append(
              f"{nome_pulito} ({mrc_t} - COD:{cod_t}) [{prz}€]"
          )

      if filtri_cambiati:
        descrizione = "TAGLIANDO COMPLETO: " + ", ".join(filtri_cambiati)
        v["storico_interventi"].append({
            "data": oggi_str,
            "lavoro": descrizione,
            "km": km,
            "costo": costo_totale,
        })
        Garage.salva(dati)
        st.success("Tagliando completo registrato!")
        st.rerun()

  st.divider()

  # 5. NOTE E PROMEMORIA DIARIO
  st.subheader("📝 Note e Diario di Bordo")
  oggi_str = datetime.date.today().strftime("%d/%m/%Y")
  ora_str = datetime.datetime.now().strftime("%H:%M")
  note_storiche = v.get("note_storiche", {})

  def aggiungi_nota_oggi_cb():
    testo = st.session_state.get("txt_nuova_nota", "").strip()
    if testo:
      testo_formattato = f"[{oggi_str} alle {ora_str}] {testo}"
      if "note_storiche" not in dati[targa_selezionata]:
        dati[targa_selezionata]["note_storiche"] = {}

      cur_notes = dati[targa_selezionata]["note_storiche"]
      if oggi_str in cur_notes and cur_notes[oggi_str].strip():
        cur_notes[oggi_str] += f"\n\n{testo_formattato}"
      else:
        cur_notes[oggi_str] = testo_formattato

      Garage.salva(dati)
      st.session_state["txt_nuova_nota"] = ""
      key_exp = f"txt_note_{oggi_str}"
      if key_exp in st.session_state:
        del st.session_state[key_exp]

  col_n1, col_n2 = st.columns([3, 1])
  col_n1.text_area(
      f"Aggiungi nuova nota per Oggi ({oggi_str})",
      key="txt_nuova_nota",
      placeholder="Scrivi qui una nuova nota...",
  )
  col_n2.button(
      "💾 Aggiungi Nota Oggi",
      key="btn_salva_oggi",
      on_click=aggiungi_nota_oggi_cb,
  )

  if note_storiche:
    with st.expander("📌 Modifica o Elimina Note Passate", expanded=True):
      date_ordinate = sorted(note_storiche.keys(), reverse=True)
      for d_nota in date_ordinate:
        st.markdown(f"### 📅 Data Nota: {d_nota}")
        col_txt, col_save, col_del = st.columns([3, 1, 1])

        txt_mod = col_txt.text_area(
            f"Testo nota {d_nota}",
            value=note_storiche[d_nota],
            key=f"txt_note_{d_nota}",
            label_visibility="collapsed",
        )

        if col_save.button("💾 Aggiorna", key=f"btn_save_note_{d_nota}"):
          if txt_mod.strip():
            v["note_storiche"][d_nota] = txt_mod.strip()
            st.success(f"Nota del {d_nota} aggiornata!")
          else:
            del v["note_storiche"][d_nota]
            st.info(f"Nota del {d_nota} rimossa!")
          Garage.salva(dati)
          st.rerun()

        if col_del.button("🗑️ Elimina", key=f"btn_del_note_{d_nota}"):
          del v["note_storiche"][d_nota]
          if f"txt_note_{d_nota}" in st.session_state:
            del st.session_state[f"txt_note_{d_nota}"]
          Garage.salva(dati)
          st.success(f"Nota del {d_nota} eliminata!")
          st.rerun()

        st.divider()

  st.divider()

  # 6. STORICO INTERVENTI RAGGRUPPATO PER ANNO
  st.subheader("📜 Storico Manutenzioni")
  storico_lista = v.get("storico_interventi", [])

  if not storico_lista:
    st.info("Nessun intervento registrato.")
  else:
    interventi_per_anno = {}
    for intv in storico_lista:
      data_int = intv.get("data", "01/01/2026")
      try:
        anno = data_int.split("/")[-1]
      except:
        anno = "Altro"

      if anno not in interventi_per_anno:
        interventi_per_anno[anno] = []
      interventi_per_anno[anno].append(intv)

    for anno in sorted(interventi_per_anno.keys(), reverse=True):
      st.write(f"### 📅 Anno {anno}")
      for intv in reversed(interventi_per_anno[anno]):
        st.info(
            f"🔧 **{intv.get('lavoro')}**  \nData: {intv.get('data')} | Km:"
            f" {intv.get('km'):,} | Costo: € {intv.get('costo'):.2f}".replace(
                ",", "."
            )
        )

else:
  st.info(
      "👈 Seleziona un veicolo dal menu a sinistra o creane uno nuovo per"
      " iniziare!"
  )
