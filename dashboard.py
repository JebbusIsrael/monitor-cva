import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import bcrypt
import os
from datetime import datetime, date, timedelta
from cryptography.fernet import Fernet
from fpdf import FPDF

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Monitor PTM — Save the Children",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

MESES_ES = {1:"enero",2:"febrero",3:"marzo",4:"abril",5:"mayo",6:"junio",
            7:"julio",8:"agosto",9:"septiembre",10:"octubre",11:"noviembre",12:"diciembre"}
DIAS_ES = {0:"lunes",1:"martes",2:"miércoles",3:"jueves",4:"viernes",5:"sábado",6:"domingo"}

def fecha_es(d): return f"{DIAS_ES[d.weekday()]} {d.day:02d}/{d.month:02d}"
def fecha_larga_es(d): return f"{d.day} de {MESES_ES[d.month]} de {d.year}"

# ─────────────────────────────────────────────
# COORDENADAS MUNICIPIOS MÉXICO
# ─────────────────────────────────────────────
COORDENADAS_MX = {
    "Tijuana": (32.5149, -117.0382), "Mexicali": (32.6245, -115.4523),
    "Ensenada": (31.8667, -116.5967), "Tecate": (32.5728, -116.6269),
    "Tapachula": (14.9000, -92.2667), "Tuxtla Gutiérrez": (16.7500, -93.1167),
    "San Cristóbal de las Casas": (16.7370, -92.6376), "Palenque": (17.5136, -91.9820),
    "Oaxaca de Juárez": (17.0732, -96.7266), "Oaxaca": (17.0732, -96.7266),
    "Salina Cruz": (16.1667, -95.2000), "Juchitán": (16.4333, -95.0167),
    "Reynosa": (26.0923, -98.2775), "Matamoros": (25.8694, -97.5044),
    "Nuevo Laredo": (27.4769, -99.5156), "Tampico": (22.2333, -97.8667),
    "Ciudad Victoria": (23.7369, -99.1411),
    "Ciudad de México": (19.4326, -99.1332), "CDMX": (19.4326, -99.1332),
    "Villahermosa": (17.9893, -92.9475), "Cárdenas": (18.0000, -93.3667),
    "Acapulco": (16.8531, -99.8237), "Chilpancingo": (17.5500, -99.5000),
    "Ciudad Juárez": (31.6904, -106.4245), "Chihuahua": (28.6353, -106.0889),
    "Hermosillo": (29.0729, -110.9559), "Nogales": (31.3036, -110.9478),
    "Culiacán": (24.7994, -107.3879), "Mazatlán": (23.2329, -106.4062),
    "Guadalajara": (20.6597, -103.3496), "Monterrey": (25.6866, -100.3161),
    "Veracruz": (19.1903, -96.1533), "Xalapa": (19.5438, -96.9102),
    "Puebla": (19.0414, -98.2063), "Mérida": (20.9670, -89.6237),
    "Cancún": (21.1619, -86.8515), "Chetumal": (18.5001, -88.3000),
    "San Luis Potosí": (22.1500, -100.9167),
    "Baja California": (30.8406, -115.2838), "Tamaulipas": (24.2669, -98.8363),
    "Chiapas": (16.7569, -93.1292), "Tabasco": (17.9893, -92.9475),
    "Guerrero": (17.4392, -100.0119), "Chihuahua (Estado)": (28.6353, -106.0889),
}

def geocodificar(lugar):
    if not lugar or str(lugar).lower() in ["nan", "none", ""]:
        return None
    if lugar in COORDENADAS_MX:
        return COORDENADAS_MX[lugar]
    for key, coords in COORDENADAS_MX.items():
        if key.lower() in str(lugar).lower() or str(lugar).lower() in key.lower():
            return coords
    return None

# ─────────────────────────────────────────────
# SERVICIOS MAP
# ─────────────────────────────────────────────
SERVICIO_MAP = {
    "medicamentos": "💊 Medicamentos",
    "estudios_de_laboratorio": "🧪 Laboratorio",
    "atenci_n_de_especialistas": "🩺 Especialista",
    "atenci_n_psicoemocional": "🧠 Psicoemocional",
    "cirug_as_u_otras_intervenciones_m_dicas": "🏥 Cirugías",
    "servicios_dentales": "🦷 Dental",
    "servicios_ginecol_gicos": "👩‍⚕️ Ginecológico",
    "otros": "❓ Otro",
    "Medicamentos": "💊 Medicamentos",
    "Estudios de laboratorio": "🧪 Laboratorio",
    "Atención de médicos especialistas": "🩺 Especialista",
    "Atención psicoemocional": "🧠 Psicoemocional",
    "Cirugías u otras intervenciones médicas": "🏥 Cirugías",
    "Servicios dentales": "🦷 Dental",
    "Servicios ginecológicos": "👩‍⚕️ Ginecológico",
    "Otros": "❓ Otro",
}

def parsear_servicios(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return []
    val = str(valor).strip()
    if any(s in val for s in ["Medicamentos", "Estudios de laboratorio", "Atención", "Cirugías", "Servicios"]):
        tokens = val.split(" ")
        resultado = []
        i = 0
        while i < len(tokens):
            matched = False
            for length in [5, 4, 3, 2, 1]:
                frase = " ".join(tokens[i:i+length])
                if frase in SERVICIO_MAP:
                    resultado.append(SERVICIO_MAP[frase])
                    i += length
                    matched = True
                    break
            if not matched:
                i += 1
        return list(dict.fromkeys(resultado))
    else:
        return [SERVICIO_MAP.get(p.strip().lower(), f"❓ {p.strip()}") for p in val.split(" ") if p.strip()]

# ─────────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stDataFrameResizable"] button[title="Download"] { display: none !important; }
    .header-bar { background:linear-gradient(90deg,#c8102e,#1f4e9c); padding:14px 20px; border-radius:10px; color:white; margin-bottom:20px; }
    .semaforo-verde { background:#e8f5e9; border-left:5px solid #4caf50; padding:10px 14px; border-radius:8px; margin-bottom:6px; }
    .semaforo-amarillo { background:#fff8e1; border-left:5px solid #ffc107; padding:10px 14px; border-radius:8px; margin-bottom:6px; }
    .semaforo-rojo { background:#fce4ec; border-left:5px solid #e53935; padding:10px 14px; border-radius:8px; margin-bottom:6px; }
    .alerta-nueva { background:#e8f5e9; border-left:4px solid #4caf50; padding:10px; border-radius:8px; margin-bottom:6px; }
    .alerta-duplicado { background:#fff3e0; border-left:4px solid #ff9800; padding:10px; border-radius:8px; margin-bottom:6px; }
    .alerta-critica { background:#fce4ec; border-left:4px solid #e53935; padding:10px; border-radius:8px; margin-bottom:6px; }
    .cruce-card { background:#f3e5f5; border-left:4px solid #9c27b0; padding:10px; border-radius:8px; margin-bottom:6px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# USUARIOS — reemplaza los HASH con los tuyos
# ─────────────────────────────────────────────
config = {
    "credentials": {
        "usernames": {
            "Monitoreo_admin": {"name": "Monitoreo", "password":"$2b$12$Lquzvyq6SYH0zJp4nnVRj.KZkJ7VIp2Y0RYRphVjev3nMPmRpfERe", "role": "admin"},
            "Tijuana": {"name": "Equipo Tijuana", "password":"$2b$12$BhOVLaSzAurxpX3E2tBj/.nysVwxEmgds8GrN9vZDL9nLAQy0hC9u", "role": "operator"},
            "Oaxaca": {"name": "Equipo Oaxaca", "password":"$2b$12$QNoD66.3qsTDGHq6FqiR8.u2sbTNIyQzcGrEtsSqkZtH176nNw8Ke", "role": "operator"},
            "CDMX": {"name": "Equipo CDMX", "password":"$2b$12$xp1Cn5nCKLGiZQikf0WqBeqs6crp3tPRtF9ab7S92kNPBc8Xe4TSe", "role": "operator"},
            "Tapachula": {"name": "Equipo Tapachula", "password":"$2b$12$Reco9TLppZJCBXfWbuokWOTKNSnF6WpJodfLYpiFkuMtIxVljQn3q", "role": "operator"},
            "Tamaulipas": {"name": "Equipo Tamaulipas", "password":"$2b$12$VF2x0pO2QnjXj/jDatDDVOjK3cCkBRsCLFhKFVRaP5CmmUu1SVrBC", "role": "operator"},
            "Tabasco": {"name": "Equipo Tabasco", "password":"$2b$12$8VpQpbLRQitjhh1iX0Sa/.7Bvyv8KaTxpwPC0LB6QKEgSndVvTzVa", "role": "operator"},
        }
    },
    "cookie": {"expiry_days": 1, "key": "monitor_cva_stc", "name": "monitor_cva_cookie"},
}

# ─────────────────────────────────────────────
# LOGIN PROPIO (sin cookies externas)
# ─────────────────────────────────────────────
def verificar_login(username, password):
    usuarios = config["credentials"]["usernames"]
    if username not in usuarios:
        return False
    hashed = usuarios[username]["password"]
    return bcrypt.checkpw(password.encode(), hashed.encode())

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.username = ""
    st.session_state.name = ""
    st.session_state.rol = ""

if not st.session_state.autenticado:
    st.markdown("""
    <div style="max-width:400px;margin:80px auto;padding:30px;border-radius:12px;
    box-shadow:0 4px 20px rgba(0,0,0,0.1);background:white;">
    <div style="background:linear-gradient(90deg,#c8102e,#1f4e9c);padding:16px;
    border-radius:8px;text-align:center;color:white;margin-bottom:24px;">
    <h2 style="margin:0">🏥 Monitor PTM</h2>
    <p style="margin:4px 0 0">Save the Children México</p>
    </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        st.markdown("### Iniciar sesión")
        usuario_input = st.text_input("Usuario")
        password_input = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar", use_container_width=True)

        if submitted:
            if verificar_login(usuario_input, password_input):
                st.session_state.autenticado = True
                st.session_state.username = usuario_input
                st.session_state.name = config["credentials"]["usernames"][usuario_input]["name"]
                st.session_state.rol = config["credentials"]["usernames"][usuario_input]["role"]
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

    st.markdown("""
    <div style="margin-top:16px; padding:12px; background:#fff8e1; border-left:4px solid #ff9800;
    border-radius:8px; font-size:12px; color:#555;">
    <strong>⚠️ Aviso de privacidad y uso responsable</strong><br><br>
    Al acceder a este sistema usted acepta las siguientes condiciones:<br>
    🔒 <strong>Confidencialidad</strong> — La información de beneficiarios es estrictamente confidencial.
    No comparta sus credenciales ni el contenido del dashboard con personas no autorizadas.<br>
    💻 <strong>Dispositivos seguros</strong> — Acceda únicamente desde equipos institucionales o de confianza.
    Evite el uso en computadoras públicas o redes WiFi abiertas.<br>
    📥 <strong>Descarga de información</strong> — No descargue ni almacene datos sensibles fuera de los
    sistemas autorizados por Save the Children.<br>
    🎯 <strong>Uso exclusivo</strong> — Este sistema es para fines operativos de monitoreo de transferencias
    monetarias. Cualquier otro uso no está autorizado.<br><br>
    <em>De conformidad con la Ley Federal de Protección de Datos Personales en Posesión de los Particulares
    y los estándares CHS de Save the Children México.</em>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

name = st.session_state.name
username = st.session_state.username
rol = st.session_state.rol

# ─────────────────────────────────────────────
# COLUMNAS
# ─────────────────────────────────────────────
COL_NOMBRE = "Nombre del paciente"
COL_TEL = "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)"
COL_TEL2 = "Por favor, proporcione un número de contacto alternativo"
COL_EDAD = "Edad del paciente"
COL_SEXO = "Sexo"
COL_PAIS = "País de origen"
COL_ENTIDAD = "Selecciona la entidad federativa en la que te encuentras"
COL_MUNICIPIO = "Municipio:"
COL_FECHA = "_submission_time"
COL_MEDICO = "Nombre del médico/personal de salud que aplica la encuesta"
COL_ORG = "Nombre de la organización a la que pertenece"
COL_ESPECIALIDAD = "Especifique el tipo de especialidad que requiere el paciente:"
COL_OTRO_SERVICIO = "¿Cuáles?"
COL_SERVICIOS = "Servicios que requiere el paciente:"
COL_NOMBRE_CC = "Nombre_de_la_persona_que_llama"
COL_TEL_CC = "N_mero_telef_nico_de_quien_llama"
COL_CIUDAD_CC = "Ciudad"
COL_PROBLEMA_CC = "Problema"
COL_DESC_CC = "Descripci_n_del_problema"
COL_SOL_CC = "Soluci_n_brindada"
COLS_PII = [COL_NOMBRE, COL_TEL, COL_TEL2]

# ─────────────────────────────────────────────
# DESCIFRADO
# ─────────────────────────────────────────────
def descifrar_archivo(nombre_enc):
    clave = st.secrets["ENCRYPTION_KEY"]
    f = Fernet(clave.encode())
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre_enc)
    if not os.path.exists(ruta):
        return pd.DataFrame()
    with open(ruta, "rb") as archivo:
        datos_cifrados = archivo.read()
    return pd.read_excel(io.BytesIO(f.decrypt(datos_cifrados)))

@st.cache_data(ttl=300)
def cargar_datos():
    return descifrar_archivo("salud_kobo.enc"), descifrar_archivo("datos_dudas_callcenter.enc")

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def contar_sel(serie):
    return serie.apply(lambda x: pd.notna(x) and str(x).strip() not in ['','0','nan','False','0.0']).sum()

def detectar_duplicados(df):
    if COL_NOMBRE not in df.columns or COL_TEL not in df.columns:
        return pd.DataFrame()
    cols = [c for c in [COL_NOMBRE, COL_TEL, COL_ENTIDAD, COL_FECHA] if c in df.columns]
    df_t = df[cols].dropna(subset=[COL_NOMBRE, COL_TEL])
    return df_t[df_t.duplicated(subset=[COL_NOMBRE, COL_TEL], keep=False)].sort_values(COL_NOMBRE)

def semaforo(n, rojo=50, amarillo=150):
    if n < rojo: return "rojo", "🔴"
    elif n < amarillo: return "amarillo", "🟡"
    else: return "verde", "🟢"

def norm_tel(x):
    return str(x).strip().replace("-","").replace(" ","").replace("+52","") if pd.notna(x) else ""

def norm_nombre(x):
    return str(x).strip().lower() if pd.notna(x) else ""

# ─────────────────────────────────────────────
# MAPA DE CALOR
# ─────────────────────────────────────────────
def mostrar_mapa(df):
    # Usar entidad como base, municipio como complemento
    if COL_ENTIDAD in df.columns and df[COL_ENTIDAD].notna().sum() > 0:
        col_lugar = COL_ENTIDAD
    elif COL_MUNICIPIO in df.columns and df[COL_MUNICIPIO].notna().sum() > 0:
        col_lugar = COL_MUNICIPIO
    else:
        st.warning("No se encontró columna de municipio o entidad.")
        return

    conteo = df[col_lugar].value_counts().reset_index()
    conteo.columns = ["Lugar", "Registros"]
    conteo["lat"] = conteo["Lugar"].apply(lambda x: geocodificar(x)[0] if geocodificar(x) else None)
    conteo["lon"] = conteo["Lugar"].apply(lambda x: geocodificar(x)[1] if geocodificar(x) else None)

    con_coords = conteo.dropna(subset=["lat", "lon"])
    sin_coords = conteo[conteo["lat"].isna()]

    if len(con_coords) == 0:
        st.warning("No se pudieron geocodificar los municipios.")
        st.dataframe(conteo[["Lugar","Registros"]], use_container_width=True)
        return

    fig = px.scatter_geo(
        con_coords,
        lat="lat", lon="lon",
        size="Registros",
        color="Registros",
        hover_name="Lugar",
        hover_data={"Registros": True, "lat": False, "lon": False},
        color_continuous_scale=["#4caf50", "#ffc107", "#e53935"],
        size_max=50,
        scope="north america",
    )
    fig.update_geos(
        showcountries=True, countrycolor="lightgray",
        showcoastlines=True, coastlinecolor="lightgray",
        showland=True, landcolor="#f5f5f5",
        showocean=True, oceancolor="#e3f2fd",
        lataxis_range=[14, 33],
        lonaxis_range=[-118, -86],
    )
    fig.update_layout(
        height=500,
        margin={"r":0,"t":30,"l":0,"b":0},
        coloraxis_colorbar=dict(title="Casos"),
    )
    st.plotly_chart(fig, use_container_width=True)

    if len(sin_coords) > 0:
        with st.expander(f"⚠️ {len(sin_coords)} lugares sin ubicación en el mapa"):
            st.dataframe(sin_coords[["Lugar","Registros"]].reset_index(drop=True), use_container_width=True)

# ─────────────────────────────────────────────
# CRUCE SALUD + CALL CENTER
# ─────────────────────────────────────────────
def mostrar_cruce(df_salud, df_cc, rol):
    if df_cc.empty:
        st.warning("Sin datos de call center disponibles.")
        return

    df_s = df_salud.copy()
    df_c = df_cc.copy()

    df_s["tel_norm"] = df_s[COL_TEL].apply(norm_tel) if COL_TEL in df_s.columns else ""
    df_s["nom_norm"] = df_s[COL_NOMBRE].apply(norm_nombre) if COL_NOMBRE in df_s.columns else ""
    df_c["tel_norm"] = df_c[COL_TEL_CC].apply(norm_tel) if COL_TEL_CC in df_c.columns else ""
    df_c["nom_norm"] = df_c[COL_NOMBRE_CC].apply(norm_nombre) if COL_NOMBRE_CC in df_c.columns else ""

    # Cruce por teléfono o nombre
    tels_cc = set(df_c[df_c["tel_norm"] != ""]["tel_norm"])
    noms_cc = set(df_c[df_c["nom_norm"] not in ["", "nan"]]["nom_norm"]) if False else set(
        df_c["nom_norm"][df_c["nom_norm"].str.len() > 3].tolist()
    )

    mask = (
        df_s["tel_norm"].isin(tels_cc) & (df_s["tel_norm"] != "")
    ) | (
        df_s["nom_norm"].isin(noms_cc) & (df_s["nom_norm"].str.len() > 3)
    )

    personas_cruce = df_s[mask]

    # Métricas
    col1, col2, col3 = st.columns(3)
    col1.metric("👥 En base salud", len(df_s))
    col2.metric("📞 En call center", len(df_c))
    col3.metric("🔗 En ambas bases", len(personas_cruce))

    if len(personas_cruce) == 0:
        st.success("✅ No se encontraron personas en ambas bases.")
        return

    st.markdown(f"""<div class="cruce-card">
        🔗 <strong>{len(personas_cruce)} personas</strong> de la base de salud también contactaron al call center.
    </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("#### Detalle por persona — Salud + Call Center")

    for _, persona in personas_cruce.iterrows():
        tel = persona.get("tel_norm", "")
        nom = persona.get("nom_norm", "")
        nombre_display = persona.get(COL_NOMBRE, "Sin nombre") if rol in ["operator","admin"] else "Beneficiario"
        entidad = persona.get(COL_ENTIDAD, "")
        municipio = persona.get(COL_MUNICIPIO, "")

        # Casos en call center de esta persona
        casos_cc = df_c[
            ((df_c["tel_norm"] == tel) & (tel != "")) |
            ((df_c["nom_norm"] == nom) & (nom != "") & (df_c["nom_norm"].str.len() > 3))
        ]

        with st.expander(f"👤 {nombre_display} — {entidad} {municipio} — {len(casos_cc)} caso(s) en call center"):
            col_iz, col_der = st.columns(2)

            with col_iz:
                st.markdown("**📋 Perfil de salud:**")
                datos = {}
                for campo, col in [("Edad", COL_EDAD), ("Sexo", COL_SEXO),
                                   ("País", COL_PAIS), ("Entidad", COL_ENTIDAD),
                                   ("Municipio", COL_MUNICIPIO),
                                   ("Servicios", COL_SERVICIOS)]:
                    val = persona.get(col, "")
                    if pd.notna(val) and str(val).strip() not in ["","nan"]:
                        datos[campo] = val
                for k, v in datos.items():
                    st.caption(f"**{k}:** {v}")

            with col_der:
                st.markdown("**📞 Casos en call center:**")
                cols_cc_ver = [c for c in [COL_PROBLEMA_CC, COL_DESC_CC,
                                           COL_SOL_CC, COL_CIUDAD_CC, COL_FECHA]
                              if c in casos_cc.columns]
                if cols_cc_ver:
                    st.dataframe(casos_cc[cols_cc_ver].reset_index(drop=True),
                                use_container_width=True)

# ─────────────────────────────────────────────
# PDF
# ─────────────────────────────────────────────
def generar_pdf(df, df_cc, entidad_sel, hoy, nuevos_hoy, duplicados, casos_criticos):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_fill_color(31, 78, 156)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "Monitor PTM - Save the Children Mexico", fill=True, ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, f"Reporte: {fecha_larga_es(hoy)} | Entidad: {entidad_sel}", fill=True, ln=True, align="C")
    pdf.ln(6)
    pdf.set_text_color(0, 0, 0)

    def seccion(titulo):
        pdf.set_fill_color(200, 16, 46)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, titulo, fill=True, ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    def fila(label, valor):
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(80, 7, label + ":", ln=False)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, str(valor), ln=True)

    seccion("RESUMEN OPERATIVO")
    fila("Total registros", len(df))
    fila("Nuevos hoy", len(nuevos_hoy))
    fila("Con 3+ servicios", len(casos_criticos))
    fila("Duplicados detectados", len(duplicados))
    pdf.ln(4)

    seccion("REGISTROS ULTIMOS 7 DIAS")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(220, 230, 241)
    pdf.cell(80, 7, "Dia", border=1, fill=True)
    pdf.cell(40, 7, "Registros", border=1, fill=True, ln=True)
    pdf.set_font("Helvetica", "", 9)
    for i in range(6, -1, -1):
        d = hoy - timedelta(days=i)
        n = len(df[df[COL_FECHA].dt.date == d]) if COL_FECHA in df.columns else 0
        pdf.cell(80, 6, fecha_es(d), border=1)
        pdf.cell(40, 6, str(n), border=1, ln=True)
    pdf.ln(4)

    seccion("DEMOGRAFIA")
    if COL_SEXO in df.columns:
        for sexo, total in df[COL_SEXO].value_counts().items():
            fila(str(sexo), f"{total} ({round(total/len(df)*100,1)}%)")
    pdf.ln(2)
    if COL_EDAD in df.columns:
        df_e = df.copy()
        df_e[COL_EDAD] = pd.to_numeric(df_e[COL_EDAD], errors="coerce")
        bins = [0,5,12,17,29,59,120]
        labels = ["0-5","6-12","13-17","18-29","30-59","60+"]
        df_e["grupo"] = pd.cut(df_e[COL_EDAD], bins=bins, labels=labels)
        for g, n in df_e["grupo"].value_counts().sort_index().items():
            fila(f"Edad {g}", n)
    pdf.ln(2)
    if COL_PAIS in df.columns:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "Nacionalidades:", ln=True)
        pdf.set_font("Helvetica", "", 9)
        for pais, n in df[COL_PAIS].value_counts().head(8).items():
            pdf.cell(0, 6, f"  {pais}: {n}", ln=True)
    pdf.ln(4)

    seccion("SERVICIOS REQUERIDOS - TIPO DE TARJETA")
    servicios_ind = [c for c in df.columns if "Servicios que requiere el paciente:/" in c]
    if servicios_ind:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(220, 230, 241)
        pdf.cell(120, 7, "Servicio / Tipo de tarjeta", border=1, fill=True)
        pdf.cell(40, 7, "Personas", border=1, fill=True, ln=True)
        pdf.set_font("Helvetica", "", 9)
        for col in servicios_ind:
            nombre = col.split("/")[-1].strip()
            total = contar_sel(df[col])
            if total > 0:
                pdf.cell(120, 6, nombre, border=1)
                pdf.cell(40, 6, str(int(total)), border=1, ln=True)
    pdf.ln(4)

    seccion("COBERTURA POR ENTIDAD")
    if COL_ENTIDAD in df.columns:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(220, 230, 241)
        pdf.cell(100, 7, "Entidad", border=1, fill=True)
        pdf.cell(30, 7, "Registros", border=1, fill=True)
        pdf.cell(50, 7, "Semaforo", border=1, fill=True, ln=True)
        pdf.set_font("Helvetica", "", 9)
        for entidad, n in df[COL_ENTIDAD].value_counts().items():
            _, e = semaforo(n)
            nivel = "VERDE >150" if n >= 150 else ("AMARILLO 50-150" if n >= 50 else "ROJO <50")
            pdf.cell(100, 6, str(entidad), border=1)
            pdf.cell(30, 6, str(n), border=1)
            pdf.cell(50, 6, nivel, border=1, ln=True)
    pdf.ln(4)

    if not df_cc.empty:
        seccion("CALL CENTER")
        cc_hoy_n = len(df_cc[df_cc[COL_FECHA].dt.date == hoy]) if COL_FECHA in df_cc.columns else 0
        fila("Total casos", len(df_cc))
        fila("Casos hoy", cc_hoy_n)
        prob_cols = [c for c in df_cc.columns if c.startswith("Problema/")]
        if prob_cols:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 7, "Tipos de problema:", ln=True)
            pdf.set_font("Helvetica", "", 9)
            for col in prob_cols:
                nombre = col.replace("Problema/","").replace("_"," ").strip()
                total = contar_sel(df_cc[col])
                if total > 0:
                    pdf.cell(0, 6, f"  {nombre}: {total}", ln=True)

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, f"Generado el {fecha_larga_es(hoy)} | Monitor PTM v7.1 | Save the Children Mexico | Confidencial",
             ln=True, align="C")
    return bytes(pdf.output())

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 👤 {name}")
    st.caption(f"Rol: `{rol}`")
    st.divider()
    modulo = st.radio("Módulo", ["📊 Salud / Beneficiarios", "📞 Call Center", "📋 MEAL & Calidad"],
                      label_visibility="collapsed")
    st.divider()
    if st.button("🔄 Actualizar datos"):
        st.cache_data.clear()
        st.rerun()
    if st.button("🚪 Cerrar sesión"):
        st.session_state.autenticado = False
        st.session_state.username = ""
        st.session_state.name = ""
        st.session_state.rol = ""
        st.rerun()
    st.divider()
    st.caption("Monitor PTM v7.1\nSave the Children México")

# ─────────────────────────────────────────────
# CARGAR
# ─────────────────────────────────────────────
with st.spinner("Cargando datos cifrados..."):
    df_salud, df_cc = cargar_datos()

for df_tmp in [df_salud, df_cc]:
    if not df_tmp.empty and COL_FECHA in df_tmp.columns:
        df_tmp[COL_FECHA] = pd.to_datetime(df_tmp[COL_FECHA], errors="coerce")

hoy = date.today()

# ═══════════════════════════════════════════════════════
# MÓDULO 1: SALUD
# ═══════════════════════════════════════════════════════
if modulo == "📊 Salud / Beneficiarios":

    st.markdown(f"""
    <div class="header-bar">
        🏥 <strong>Monitor PTM — Save the Children México</strong>
        &nbsp;|&nbsp; 📅 {fecha_larga_es(hoy)}
        &nbsp;|&nbsp; 👤 {name} ({rol})
    </div>""", unsafe_allow_html=True)

    if df_salud.empty:
        st.warning("Sin datos disponibles aún.")
        st.stop()

    # Filtro entidad
    entidades = ["Todas"]
    if COL_ENTIDAD in df_salud.columns:
        entidades += sorted(df_salud[COL_ENTIDAD].dropna().unique().tolist())
    entidad_sel = st.selectbox("🗺️ Filtrar por entidad federativa", entidades)

    df = df_salud.copy()
    if entidad_sel != "Todas" and COL_ENTIDAD in df.columns:
        df = df[df[COL_ENTIDAD] == entidad_sel]

    st.caption(f"Mostrando **{len(df)}** registros — **{entidad_sel}**")

    # Servicios
    servicios_ind = [c for c in df.columns if "Servicios que requiere el paciente:/" in c]
    def es_sel(x): return pd.notna(x) and str(x).strip() not in ['','0','nan','False','0.0']

    if servicios_ind:
        df["num_servicios"] = df[servicios_ind].apply(lambda r: sum(es_sel(v) for v in r), axis=1)
    else:
        df["num_servicios"] = 0

    if COL_SERVICIOS in df.columns:
        df["tarjetas_requeridas"] = df[COL_SERVICIOS].apply(
            lambda x: " | ".join(parsear_servicios(x)) if pd.notna(x) else ""
        )

    nuevos_hoy = df[df[COL_FECHA].dt.date == hoy] if COL_FECHA in df.columns else pd.DataFrame()
    duplicados = detectar_duplicados(df)
    casos_criticos = df[df["num_servicios"] >= 3]

    st.divider()

    # ══ SECCIÓN 1: OPERATIVO RECIENTE ══
    st.markdown("## 📅 Operativo reciente")

    if len(nuevos_hoy) > 0:
        st.markdown(f"""<div class="alerta-nueva">🟢 <strong>{len(nuevos_hoy)} nuevos registros hoy</strong> — {fecha_es(hoy)}</div>""", unsafe_allow_html=True)
    if len(duplicados) > 0:
        st.markdown(f"""<div class="alerta-duplicado">⚠️ <strong>{len(duplicados)} posibles duplicados</strong> detectados</div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Total", len(df))
    col2.metric("🆕 Nuevos hoy", len(nuevos_hoy))
    col3.metric("⚠️ Duplicados", len(duplicados))

    st.divider()

    # Últimos 7 días
    st.markdown("#### 📆 Registros últimos 9 días")
    if COL_FECHA in df.columns:
        ultimos_7 = [(hoy - timedelta(days=i)) for i in range(8, -1, -1)]
        conteos = [{"Día": fecha_es(d), "Fecha": d,
                    "Registros": len(df[df[COL_FECHA].dt.date == d]),
                    "Hoy": d == hoy} for d in ultimos_7]
        df_dias = pd.DataFrame(conteos)
        colores = ["#4caf50" if r else "#1f4e9c" for r in df_dias["Hoy"]]
        fig_dias = go.Figure(go.Bar(
            x=df_dias["Día"], y=df_dias["Registros"],
            marker_color=colores, text=df_dias["Registros"], textposition="outside"
        ))
        fig_dias.update_layout(showlegend=False, plot_bgcolor="white", height=280)
        st.plotly_chart(fig_dias, use_container_width=True)

        cols_tabla = [COL_NOMBRE, COL_EDAD, COL_SEXO, COL_PAIS,
                     COL_ENTIDAD, COL_MUNICIPIO, "tarjetas_requeridas", COL_FECHA]
        for item in reversed(conteos):
            d = item["Fecha"]
            reg = df[df[COL_FECHA].dt.date == d]
            if len(reg) > 0 and COL_ENTIDAD in reg.columns:
                oficinas_dia = reg[COL_ENTIDAD].dropna().value_counts()
                resumen_of = " | ".join([f"{of}: {n}" for of, n in oficinas_dia.items()])
            else:
                resumen_of = "sin registros"
            prefix = "🟢 Hoy" if d == hoy else fecha_es(d)
            label = f"{prefix} — {len(reg)} registros  ·  {resumen_of}"
            with st.expander(label, expanded=(d == hoy)):
                if len(reg) == 0:
                    st.info("Sin registros este día.")
                else:
                    cols_ver = [c for c in cols_tabla if c in reg.columns]
                    if rol not in ["operator","admin"]:
                        cols_ver = [c for c in cols_ver if c not in COLS_PII]
                    st.dataframe(reg[cols_ver].reset_index(drop=True), use_container_width=True)

    st.divider()

    # ══ SECCIÓN 2: SERVICIOS Y TARJETA ══
    st.markdown("## 💳 Servicios requeridos — Tipo de tarjeta")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if servicios_ind:
            serv_data = {c.split("/")[-1].strip(): contar_sel(df[c]) for c in servicios_ind}
            df_serv = pd.DataFrame(list(serv_data.items()), columns=["Servicio","Personas"])
            df_serv = df_serv[df_serv["Personas"] > 0].sort_values("Personas")
            fig_sv = px.bar(df_serv, x="Personas", y="Servicio", orientation="h",
                           color_discrete_sequence=["#1f4e9c"])
            st.plotly_chart(fig_sv, use_container_width=True)
            st.caption("⚠️ Una persona puede requerir varios tipos.")

    with col_s2:
        if COL_SERVICIOS in df.columns:
            combos = df["tarjetas_requeridas"].value_counts().head(8).reset_index()
            combos.columns = ["Combinación de servicios", "Personas"]
            st.markdown("##### Combinaciones más frecuentes")
            st.dataframe(combos, use_container_width=True, height=300)

    if COL_OTRO_SERVICIO in df.columns:
        otros = df[COL_OTRO_SERVICIO].dropna()
        otros = otros[~otros.astype(str).str.strip().str.lower().isin(["nan",""])]
        if len(otros) > 0:
            st.markdown("##### ❓ Detalle de 'Otro' servicio")
            st.dataframe(otros.value_counts().reset_index().rename(
                columns={"index":"Descripción", COL_OTRO_SERVICIO:"Frecuencia"}
            ), use_container_width=True)

    if COL_ESPECIALIDAD in df.columns:
        esp = df[COL_ESPECIALIDAD].dropna()
        esp = esp[~esp.astype(str).str.strip().str.lower().isin(["nan",""])]
        if len(esp) > 0:
            st.markdown("##### 🩺 Especialidades requeridas")
            esp_count = esp.value_counts().reset_index()
            esp_count.columns = ["Especialidad","Personas"]
            fig_esp = px.bar(esp_count.head(10), x="Personas", y="Especialidad",
                            orientation="h", color_discrete_sequence=["#9c27b0"])
            st.plotly_chart(fig_esp, use_container_width=True)

    st.divider()

    # ══ SECCIÓN 3: MAPA DE CALOR ══
    st.markdown("## 🗺️ Mapa de calor — distribución geográfica")
    mostrar_mapa(df)

    st.divider()

    # ══ SECCIÓN 4: DEMOGRAFÍA ══
    st.markdown("## 👥 Análisis demográfico")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("#### Sexo")
        if COL_SEXO in df.columns:
            fig = px.pie(df[COL_SEXO].value_counts().reset_index(),
                        values="count", names=COL_SEXO,
                        color_discrete_sequence=["#1f4e9c","#e91e8c","#4caf50"])
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("#### Grupo de edad")
        if COL_EDAD in df.columns:
            df[COL_EDAD] = pd.to_numeric(df[COL_EDAD], errors="coerce")
            bins = [0,5,12,17,29,59,120]
            labels = ["0-5","6-12","13-17","18-29","30-59","60+"]
            df["grupo_edad"] = pd.cut(df[COL_EDAD], bins=bins, labels=labels)
            edad_c = df["grupo_edad"].value_counts().sort_index().reset_index()
            fig2 = px.bar(edad_c, x="grupo_edad", y="count", color_discrete_sequence=["#1f4e9c"])
            st.plotly_chart(fig2, use_container_width=True)

    with col_c:
        st.markdown("#### Nacionalidad")
        if COL_PAIS in df.columns:
            pais_c = df[COL_PAIS].value_counts().head(8).reset_index()
            pais_c.columns = ["País","Total"]
            fig3 = px.bar(pais_c, x="Total", y="País", orientation="h",
                         color_discrete_sequence=["#607d8b"])
            st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # ══ SECCIÓN 5: ESTADÍSTICAS GENERALES ══
    st.markdown("## 📊 Estadísticas generales")

    st.markdown("#### 📈 Tendencia de registros por oficina")
    if COL_FECHA in df.columns:
        col_tend1, col_tend2 = st.columns([1, 3])
        with col_tend1:
            vista = st.radio("Ver por:", ["Semana", "Mes"], horizontal=False)
            if COL_ENTIDAD in df.columns:
                oficinas_disp = ["Todas"] + sorted(df[COL_ENTIDAD].dropna().unique().tolist())
                oficina_tend = st.multiselect("Oficinas:", oficinas_disp[1:], default=oficinas_disp[1:3] if len(oficinas_disp) > 2 else oficinas_disp[1:])
            else:
                oficina_tend = []

        with col_tend2:
            df_tend = df.copy()
            if oficina_tend and COL_ENTIDAD in df_tend.columns:
                df_tend = df_tend[df_tend[COL_ENTIDAD].isin(oficina_tend)]
            df_tend["periodo"] = df_tend[COL_FECHA].dt.to_period("W" if vista == "Semana" else "M").astype(str)

            if COL_ENTIDAD in df_tend.columns and len(oficina_tend) > 1:
                tend = df_tend.groupby(["periodo", COL_ENTIDAD]).size().reset_index(name="Registros")
                fig_t = px.line(tend, x="periodo", y="Registros", color=COL_ENTIDAD,
                               markers=True, title="Registros por oficina")
            else:
                tend = df_tend.groupby("periodo").size().reset_index(name="Registros")
                fig_t = px.line(tend, x="periodo", y="Registros", markers=True,
                               color_discrete_sequence=["#1f4e9c"])

            fig_t.update_layout(xaxis_title="Período", plot_bgcolor="white", legend_title="Oficina")
            st.plotly_chart(fig_t, use_container_width=True)

    st.markdown("#### 🤒 Síntomas más frecuentes")
    sint_cols = [c for c in df.columns if "Síntomas del paciente/" in c]
    if sint_cols:
        sint_data = {c.split("/")[-1].strip(): contar_sel(df[c]) for c in sint_cols}
        df_sint = pd.DataFrame(list(sint_data.items()), columns=["Síntoma","Total"])
        df_sint = df_sint[df_sint["Total"] > 0].sort_values("Total", ascending=False)
        fig_s = px.bar(df_sint, x="Síntoma", y="Total", color_discrete_sequence=["#ff5722"])
        st.plotly_chart(fig_s, use_container_width=True)

    st.markdown("#### 🚦 Cobertura por entidad")
    if COL_ENTIDAD in df_salud.columns:
        cob = df_salud[COL_ENTIDAD].value_counts().reset_index()
        cob.columns = ["Entidad","Registros"]
        col_sem1, col_sem2 = st.columns([1,2])
        with col_sem1:
            for _, row in cob.iterrows():
                nivel, emoji = semaforo(row["Registros"])
                st.markdown(f"""<div class="semaforo-{nivel}">
                    {emoji} <strong>{row['Entidad']}</strong> — {row['Registros']}
                </div>""", unsafe_allow_html=True)
            st.caption("🔴<50 &nbsp; 🟡 50-150 &nbsp; 🟢>150")
        with col_sem2:
            fig_cob = px.bar(cob.sort_values("Registros"), x="Registros", y="Entidad",
                            orientation="h", color="Registros",
                            color_continuous_scale=["#e53935","#ffc107","#4caf50"],
                            text="Registros")
            fig_cob.update_traces(textposition="outside")
            fig_cob.update_layout(coloraxis_showscale=False, plot_bgcolor="white")
            st.plotly_chart(fig_cob, use_container_width=True)

    st.divider()

    # ══ SECCIÓN 6: BÚSQUEDA Y TODOS LOS REGISTROS ══
    st.markdown("## 🔍 Búsqueda de beneficiarios")

    col_busq1, col_busq2, col_busq3 = st.columns(3)
    with col_busq1:
        busq_nombre = st.text_input("🔎 Buscar por nombre", placeholder="Escribe el nombre...")
    with col_busq2:
        busq_tel = st.text_input("📱 Buscar por teléfono", placeholder="Escribe el número...")
    with col_busq3:
        busq_pais = st.text_input("🌍 Buscar por país", placeholder="Ej: Venezuela...")

    # Aplicar filtros de búsqueda
    df_busq = df.copy()
    filtros_activos = []

    if busq_nombre.strip():
        if COL_NOMBRE in df_busq.columns:
            df_busq = df_busq[df_busq[COL_NOMBRE].astype(str).str.lower().str.contains(
                busq_nombre.strip().lower(), na=False)]
        filtros_activos.append(f"Nombre: '{busq_nombre}'")

    if busq_tel.strip():
        if COL_TEL in df_busq.columns:
            df_busq = df_busq[df_busq[COL_TEL].astype(str).str.contains(
                busq_tel.strip(), na=False)]
        filtros_activos.append(f"Teléfono: '{busq_tel}'")

    if busq_pais.strip():
        if COL_PAIS in df_busq.columns:
            df_busq = df_busq[df_busq[COL_PAIS].astype(str).str.lower().str.contains(
                busq_pais.strip().lower(), na=False)]
        filtros_activos.append(f"País: '{busq_pais}'")

    if filtros_activos:
        st.caption(f"🔍 Filtros activos: {' | '.join(filtros_activos)} — **{len(df_busq)}** resultados")

        if len(df_busq) == 0:
            st.warning("No se encontraron resultados para esa búsqueda.")
        else:
            cols_excluir = ["__version__","_tags","meta/rootUuid","_index",
                           "_notes","_status","_submitted_by","_validation_status"]
            cols_busq = [COL_NOMBRE, COL_TEL, COL_EDAD, COL_SEXO, COL_PAIS,
                        COL_ENTIDAD, COL_MUNICIPIO, "tarjetas_requeridas",
                        COL_ESPECIALIDAD, COL_FECHA]
            if rol not in ["operator","admin"]:
                cols_busq = [c for c in cols_busq if c not in COLS_PII]
            cols_busq_disp = [c for c in cols_busq if c in df_busq.columns]

            # Si es un solo resultado mostrar detalle completo
            if len(df_busq) == 1:
                st.success("✅ 1 registro encontrado")
                persona = df_busq.iloc[0]
                col_det1, col_det2 = st.columns(2)
                with col_det1:
                    st.markdown("**Datos personales:**")
                    for campo, col in [("Nombre", COL_NOMBRE), ("Teléfono", COL_TEL),
                                       ("Edad", COL_EDAD), ("Sexo", COL_SEXO),
                                       ("País", COL_PAIS), ("Entidad", COL_ENTIDAD),
                                       ("Municipio", COL_MUNICIPIO)]:
                        if col in persona.index and pd.notna(persona[col]):
                            if col not in COLS_PII or rol in ["operator","admin"]:
                                st.write(f"**{campo}:** {persona[col]}")
                with col_det2:
                    st.markdown("**Servicios requeridos:**")
                    if "tarjetas_requeridas" in persona.index:
                        servicios = persona.get("tarjetas_requeridas", "")
                        if servicios:
                            for s in str(servicios).split(" | "):
                                st.write(f"• {s}")
                    if COL_ESPECIALIDAD in persona.index and pd.notna(persona.get(COL_ESPECIALIDAD)):
                        st.write(f"**Especialidad:** {persona[COL_ESPECIALIDAD]}")
                    if COL_FECHA in persona.index:
                        st.write(f"**Fecha registro:** {persona[COL_FECHA]}")
            else:
                st.dataframe(df_busq[cols_busq_disp].reset_index(drop=True),
                            use_container_width=True, height=350)

    st.divider()

    st.markdown("## 📋 Todos los registros")
    cols_excluir = ["__version__","_tags","meta/rootUuid","_index",
                   "_notes","_status","_submitted_by","_validation_status"]
    todas_cols = [c for c in df.columns if c not in cols_excluir]
    if rol in ["operator","admin"]:
        cols_ver = todas_cols
        st.info("👁 Ves todos los datos incluyendo nombre y teléfono.")
    else:
        cols_ver = [c for c in todas_cols if c not in COLS_PII]
    st.dataframe(df[cols_ver].reset_index(drop=True), use_container_width=True, height=450)

    st.divider()

    st.markdown("#### 🔍 Duplicados detectados")
    if len(duplicados) > 0:
        st.warning(f"⚠️ **{len(duplicados)}** registros con mismo nombre y teléfono.")
        cols_dup = [c for c in [COL_NOMBRE, COL_TEL, COL_ENTIDAD, COL_FECHA] if c in duplicados.columns]
        if rol not in ["operator","admin"]:
            cols_dup = [c for c in cols_dup if c not in COLS_PII]
        st.dataframe(duplicados[cols_dup].reset_index(drop=True), use_container_width=True)
    else:
        st.success("✅ Sin duplicados detectados.")

    st.divider()

    st.markdown("#### 📄 Descargar reporte PDF")
    st.caption(f"Entidad: **{entidad_sel}** — Sin datos personales.")
    pdf_bytes = generar_pdf(df, df_cc, entidad_sel, hoy, nuevos_hoy, duplicados, casos_criticos)
    st.download_button(
        label=f"⬇️ Reporte PDF — {fecha_larga_es(hoy)} — {entidad_sel}",
        data=pdf_bytes,
        file_name=f"reporte_ptm_{entidad_sel}_{hoy.strftime('%d%m%Y')}.pdf",
        mime="application/pdf",
    )

# ═══════════════════════════════════════════════════════
# MÓDULO 2: CALL CENTER
# ═══════════════════════════════════════════════════════
elif modulo == "📞 Call Center":
    st.markdown(f"""
    <div class="header-bar">
        📞 <strong>Call Center — Save the Children México</strong>
        &nbsp;|&nbsp; 📅 {fecha_larga_es(hoy)}
    </div>""", unsafe_allow_html=True)

    if df_cc.empty:
        st.warning("Sin datos disponibles aún.")
        st.stop()

    cc_hoy = df_cc[df_cc[COL_FECHA].dt.date == hoy] if COL_FECHA in df_cc.columns else pd.DataFrame()

    if len(cc_hoy) > 0:
        st.markdown(f"""<div class="alerta-nueva">🟢 <strong>{len(cc_hoy)} nuevos casos hoy</strong> — {fecha_es(hoy)}</div>""", unsafe_allow_html=True)

    # Casos sin solución registrada (últimos 28 días)
    fecha_28 = hoy - timedelta(days=28)
    df_cc_28 = df_cc[df_cc[COL_FECHA].dt.date >= fecha_28] if COL_FECHA in df_cc.columns else df_cc
    sin_solucion = df_cc_28[
        df_cc_28[COL_SOL_CC].isna() | (df_cc_28[COL_SOL_CC].astype(str).str.strip() == "")
    ] if COL_SOL_CC in df_cc_28.columns else pd.DataFrame()

    if len(sin_solucion) > 0:
        st.markdown(f'''<div class="alerta-critica">
            ⚠️ <strong>{len(sin_solucion)} casos sin solución registrada</strong> en las últimas 4 semanas — requieren seguimiento.
        </div>''', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📋 Total casos", len(df_cc))
    col2.metric("🆕 Casos hoy", len(cc_hoy))
    col3.metric("⚠️ Sin solución (28 días)", len(sin_solucion))
    if COL_CIUDAD_CC in df_cc.columns:
        col4.metric("🏙 Ciudades", df_cc[COL_CIUDAD_CC].nunique())

    st.divider()

    st.markdown("#### 📆 Casos últimas 4 semanas (28 días)")
    if COL_FECHA in df_cc.columns:
        ultimos_7 = [(hoy - timedelta(days=i)) for i in range(27, -1, -1)]
        conteos_cc = [{"Día": fecha_es(d),
                       "Casos": len(df_cc[df_cc[COL_FECHA].dt.date == d]),
                       "Hoy": d == hoy} for d in ultimos_7]
        df_cc_dias = pd.DataFrame(conteos_cc)
        colores_cc = ["#4caf50" if r else "#1f4e9c" for r in df_cc_dias["Hoy"]]
        fig_cc = go.Figure(go.Bar(x=df_cc_dias["Día"], y=df_cc_dias["Casos"],
                                  marker_color=colores_cc, text=df_cc_dias["Casos"],
                                  textposition="outside"))
        fig_cc.update_layout(showlegend=False, plot_bgcolor="white", height=280)
        st.plotly_chart(fig_cc, use_container_width=True)

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 🔖 Tipos de problema")
        problemas_cols = [c for c in df_cc.columns if c.startswith("Problema/")]
        if problemas_cols:
            prob_data = {c.replace("Problema/","").replace("_"," ").strip(): contar_sel(df_cc[c])
                        for c in problemas_cols}
            df_prob = pd.DataFrame(list(prob_data.items()), columns=["Problema","Total"])
            df_prob = df_prob[df_prob["Total"] > 0].sort_values("Total")
            fig_p = px.bar(df_prob, x="Total", y="Problema", orientation="h",
                          color_discrete_sequence=["#1f4e9c"])
            st.plotly_chart(fig_p, use_container_width=True)

    with col_b:
        st.markdown("#### 🏙 Por ciudad")
        if COL_CIUDAD_CC in df_cc.columns:
            ciudad = df_cc[COL_CIUDAD_CC].value_counts().head(10).reset_index()
            fig_c = px.bar(ciudad, x="count", y=COL_CIUDAD_CC, orientation="h",
                          color_discrete_sequence=["#e91e8c"])
            st.plotly_chart(fig_c, use_container_width=True)

    if COL_FECHA in df_cc.columns:
        st.markdown("#### 📈 Tendencia")
        vista_cc = st.radio("Ver por:", ["Semana","Mes"], horizontal=True, key="cc_tend")
        df_cc["periodo"] = df_cc[COL_FECHA].dt.to_period("W" if vista_cc == "Semana" else "M").astype(str)
        tend_cc = df_cc.groupby("periodo").size().reset_index(name="Casos")
        fig_tc = px.line(tend_cc, x="periodo", y="Casos", markers=True,
                        color_discrete_sequence=["#1f4e9c"])
        st.plotly_chart(fig_tc, use_container_width=True)

    st.divider()

    # ── ÚLTIMOS 15 DÍAS DETALLE ──
    st.markdown("#### 📋 Casos últimas 4 semanas — detalle por fecha y oficina")
    if COL_FECHA in df_cc.columns:
        fecha_corte_15 = hoy - timedelta(days=28)
        df_cc_15 = df_cc[df_cc[COL_FECHA].dt.date >= fecha_corte_15].copy()
        df_cc_15 = df_cc_15.sort_values(COL_FECHA, ascending=False)

        cols_pii_cc = [COL_NOMBRE_CC, COL_TEL_CC]
        cols_15 = [COL_FECHA, COL_CIUDAD_CC, COL_PROBLEMA_CC, COL_DESC_CC, COL_SOL_CC]
        if rol in ["operator", "admin"]:
            cols_15 = [COL_NOMBRE_CC, COL_TEL_CC] + cols_15
            st.info("👁 Ves nombre y teléfono porque tu rol es **operator/admin**.")

        cols_15_disp = [c for c in cols_15 if c in df_cc_15.columns]
        st.caption(f"Mostrando **{len(df_cc_15)}** casos de los últimos 15 días")
        st.dataframe(df_cc_15[cols_15_disp].reset_index(drop=True), use_container_width=True, height=400)

    st.divider()
    st.markdown("#### 📋 Todos los casos (histórico)")
    cols_excluir_cc = ["__version__","_tags","meta/rootUuid","_index",
                      "_notes","_status","_submitted_by","_validation_status"]
    todas_cc = [c for c in df_cc.columns if c not in cols_excluir_cc]
    if rol in ["operator","admin"]:
        cols_cc_ver = todas_cc
    else:
        cols_cc_ver = [c for c in todas_cc if c not in [COL_NOMBRE_CC, COL_TEL_CC]]
    st.dataframe(df_cc[cols_cc_ver].reset_index(drop=True), use_container_width=True, height=300)


    st.divider()

    # ══ CRUCE SALUD + CALL CENTER ══
    st.markdown("## 🔗 Cruce — Personas de salud en call center (últimas 4 semanas)")
    st.caption("Beneficiarios de la base de salud que también contactaron al call center en las últimas 4 semanas.")

    if not df_salud.empty and COL_TEL in df_salud.columns and COL_TEL_CC in df_cc.columns:
        def norm_t(x):
            return str(x).strip().replace("-","").replace(" ","").replace("+52","") if pd.notna(x) else ""
        def norm_n(x):
            return str(x).strip().lower() if pd.notna(x) else ""

        fecha_corte_14 = hoy - timedelta(days=14)
        df_s = df_salud.copy()
        df_c14 = df_cc.copy()
        if COL_FECHA in df_c14.columns:
            df_c14 = df_c14[df_c14[COL_FECHA].dt.date >= fecha_corte_14]

        df_s["tel_norm"] = df_s[COL_TEL].apply(norm_t)
        df_s["nom_norm"] = df_s[COL_NOMBRE].apply(norm_n) if COL_NOMBRE in df_s.columns else ""
        df_c14["tel_norm"] = df_c14[COL_TEL_CC].apply(norm_t)
        df_c14["nom_norm"] = df_c14[COL_NOMBRE_CC].apply(norm_n) if COL_NOMBRE_CC in df_c14.columns else ""

        tels_cc = set(df_c14[df_c14["tel_norm"] != ""]["tel_norm"])
        noms_cc = set(df_c14[df_c14["nom_norm"].str.len() > 3]["nom_norm"])

        mask = (
            df_s["tel_norm"].isin(tels_cc) & (df_s["tel_norm"] != "")
        ) | (
            df_s["nom_norm"].isin(noms_cc) & (df_s["nom_norm"].str.len() > 3)
        )
        personas_cruce = df_s[mask]

        col1, col2, col3 = st.columns(3)
        col1.metric("👥 En base salud", len(df_s))
        col2.metric("📞 Call center 28 días", len(df_c14))
        col3.metric("🔗 En ambas bases", len(personas_cruce))

        if len(personas_cruce) == 0:
            st.success("✅ Sin personas en ambas bases en los últimos 14 días.")
        else:
            st.markdown(f'''<div class="cruce-card">
                🔗 <strong>{len(personas_cruce)} personas</strong> de salud también contactaron call center en los últimos 14 días.
            </div>''', unsafe_allow_html=True)

            filas = []
            for _, persona in personas_cruce.iterrows():
                tel = persona.get("tel_norm", "")
                nom = persona.get("nom_norm", "")
                casos = df_c14[
                    ((df_c14["tel_norm"] == tel) & (tel != "")) |
                    ((df_c14["nom_norm"] == nom) & (nom != "") & (df_c14["nom_norm"].str.len() > 3))
                ]
                for _, caso in casos.iterrows():
                    fila = {
                        "Fecha caso": caso.get(COL_FECHA, ""),
                        "Ciudad": caso.get(COL_CIUDAD_CC, ""),
                        "Problema": caso.get(COL_PROBLEMA_CC, ""),
                        "Descripción": caso.get(COL_DESC_CC, ""),
                        "Solución": caso.get(COL_SOL_CC, ""),
                        "Oficina salud": persona.get(COL_ENTIDAD, ""),
                        "Sexo": persona.get(COL_SEXO, ""),
                        "Edad": persona.get(COL_EDAD, ""),
                        "País": persona.get(COL_PAIS, ""),
                    }
                    if rol in ["operator", "admin"]:
                        fila["Nombre"] = persona.get(COL_NOMBRE, "")
                        fila["Teléfono"] = persona.get(COL_TEL, "")
                    filas.append(fila)

            if filas:
                df_tc = pd.DataFrame(filas).sort_values("Fecha caso", ascending=False)
                st.caption(f"**{len(filas)}** casos vinculados entre salud y call center")
                st.dataframe(df_tc.reset_index(drop=True), use_container_width=True, height=450)
    else:
        st.info("Se necesitan datos de salud y call center para mostrar el cruce.")

# ═══════════════════════════════════════════════════════
# MÓDULO 3: MEAL & CALIDAD
# ═══════════════════════════════════════════════════════
elif modulo == "📋 MEAL & Calidad":
    st.markdown(f"""
    <div class="header-bar">
        📋 <strong>MEAL & Calidad — Save the Children México</strong>
        &nbsp;|&nbsp; 📅 {fecha_larga_es(hoy)}
    </div>""", unsafe_allow_html=True)

    if df_salud.empty:
        st.warning("Sin datos disponibles aún.")
        st.stop()

    # Calidad de datos
    st.markdown("## 🔬 Calidad de datos")
    campos = {"Nombre": COL_NOMBRE, "Teléfono": COL_TEL, "Edad": COL_EDAD,
              "Sexo": COL_SEXO, "País": COL_PAIS, "Entidad": COL_ENTIDAD}
    calidad = {k: round(df_salud[v].notna().sum()/len(df_salud)*100, 1)
               for k, v in campos.items() if v in df_salud.columns}

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        for campo, pct in calidad.items():
            if pct >= 90:
                st.markdown(f"""<div class="alerta-nueva">✅ <strong>{campo}</strong>: {pct}%</div>""", unsafe_allow_html=True)
            elif pct >= 70:
                st.markdown(f"""<div class="alerta-duplicado">⚠️ <strong>{campo}</strong>: {pct}%</div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="alerta-critica">❌ <strong>{campo}</strong>: {pct}% — requiere atención</div>""", unsafe_allow_html=True)
    with col_c2:
        df_cal = pd.DataFrame(list(calidad.items()), columns=["Campo","% Completitud"])
        fig_cal = px.bar(df_cal.sort_values("% Completitud"), x="% Completitud", y="Campo",
                        orientation="h", color="% Completitud",
                        color_continuous_scale=["#e53935","#ffc107","#4caf50"],
                        range_x=[0,100])
        fig_cal.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_cal, use_container_width=True)


