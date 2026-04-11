import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import os
from datetime import datetime
from cryptography.fernet import Fernet
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Monitor CVA — Save the Children",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #f0f4ff;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        border-left: 4px solid #1f4e9c;
    }
    .alert-card {
        background: #fff3cd;
        border-radius: 10px;
        padding: 12px;
        border-left: 4px solid #ff9800;
        margin-bottom: 8px;
    }
    .header-logo {
        color: #1f4e9c;
        font-size: 22px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# USUARIOS Y ROLES
# Genera contraseñas hasheadas con:
# import streamlit_authenticator as stauth
# print(stauth.Hasher(['tu_password']).generate())
# ─────────────────────────────────────────────
config = {
    "credentials": {
        "usernames": {
            "tijuana": {
                "name": "Equipo Tijuana",
                "password": "$2b$12$BhOVLaSzAurxpX3E2tBj/.nysVwxEmgds8GrN9vZDL9nLAQy0hC9u",
                "role": "operator",
            },
            "oaxaca": {
                "name": "Equipo Oaxaca",
                "password": "$2b$12$QNoD66.3qsTDGHq6FqiR8.u2sbTNIyQzcGrEtsSqkZtH176nNw8Ke",
                "role": "operator",
            },
            "cdmx": {
                "name": "Equipo CDMX",
                "password": "$2b$12$xp1Cn5nCKLGiZQikf0WqBeqs6crp3tPRtF9ab7S92kNPBc8Xe4TSe",
                "role": "operator",
            },
            "tapachula": {
                "name": "Equipo Tapachula",
                "password": "$2b$12$Reco9TLppZJCBXfWbuokWOTKNSnF6WpJodfLYpiFkuMtIxVljQn3q",
                "role": "operator",
            },
            "tamaulipas": {
                "name": "Equipo Tamaulipas",
                "password": "$2b$12$VF2x0pO2QnjXj/jDatDDVOjK3cCkBRsCLFhKFVRaP5CmmUu1SVrBC",
                "role": "operator",
            },
            "tabasco": {
                "name": "Equipo Tabasco",
                "password": "$2b$12$8VpQpbLRQitjhh1iX0Sa/.7Bvyv8KaTxpwPC0LB6QKEgSndVvTzVa",
                "role": "operator",
            },
            "Monitoreo_admin": {
                "name": "Monitoreo",
                "password": "$2b$12$Lquzvyq6SYH0zJp4nnVRj.KZkJ7VIp2Y0RYRphVjev3nMPmRpfERe",
                "role": "admin",
            },
        }
    },
    "cookie": {
        "expiry_days": 1,
        "key": "monitor_cva_stc",
        "name": "monitor_cva_cookie",
    },
}
# ─────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────
authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

authenticator.login(location="main")

name = st.session_state.get("name")
authentication_status = st.session_state.get("authentication_status")
username = st.session_state.get("username")

if authentication_status is False:
    st.error("Usuario o contraseña incorrectos.")
    st.stop()

if authentication_status is None:
    st.warning("Ingresa tus credenciales para continuar.")
    st.stop()
# ─────────────────────────────────────────────
# OBTENER ROL DEL USUARIO
# ─────────────────────────────────────────────
rol = config["credentials"]["usernames"][username]["role"]

# ─────────────────────────────────────────────
# DESCIFRADO
# ─────────────────────────────────────────────
def descifrar_archivo(nombre_enc: str) -> pd.DataFrame:
    """Lee el archivo .enc desde OneDrive y descifra en memoria."""
    clave = st.secrets["ENCRYPTION_KEY"]
    f = Fernet(clave.encode())

    ruta = os.path.join(st.secrets["ONEDRIVE_FOLDER"], nombre_enc)

    if not os.path.exists(ruta):
        return pd.DataFrame()

    with open(ruta, "rb") as archivo:
        datos_cifrados = archivo.read()

    datos = f.decrypt(datos_cifrados)
    return pd.read_excel(io.BytesIO(datos))


@st.cache_data(ttl=300)  # refresca cada 5 minutos
def cargar_datos():
    salud = descifrar_archivo("salud_kobo.enc")
    callcenter = descifrar_archivo("datos_dudas_callcenter.enc")
    return salud, callcenter


# ─────────────────────────────────────────────
# COLUMNAS CLAVE
# ─────────────────────────────────────────────
COL_NOMBRE_SALUD = "Nombre del paciente"
COL_TEL_SALUD = "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)"
COL_EDAD = "Edad del paciente"
COL_SEXO = "Sexo"
COL_PAIS = "País de origen"
COL_ENTIDAD = "Selecciona la entidad federativa en la que te encuentras"
COL_SINTOMAS = "Síntomas del paciente"
COL_SERVICIOS = "Servicios que requiere el paciente:"
COL_TARJETA1 = "Entregar tarjeta con monto 1"
COL_TARJETA2 = "Entregar tarjeta con monto 2"
COL_TARJETA3 = "Entregar tarjeta con monto 3"
COL_FECHA = "_submission_time"

COL_NOMBRE_CC = "Nombre_de_la_persona_que_llama"
COL_TEL_CC = "N_mero_telef_nico_de_quien_llama"
COL_CIUDAD_CC = "Ciudad"
COL_PROBLEMA_CC = "Problema"
COL_DESC_CC = "Descripci_n_del_problema"
COL_SOLUCION_CC = "Soluci_n_brindada"


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 👤 {name}")
    st.caption(f"Rol: `{rol}`")
    st.divider()

    modulo = st.radio(
        "Módulo",
        ["📊 Salud / Beneficiarios", "📞 Call Center"],
        label_visibility="collapsed",
    )

    st.divider()

    if st.button("🔄 Actualizar datos"):
        st.cache_data.clear()
        st.rerun()

    authenticator.logout("Cerrar sesión", "sidebar")

    st.divider()
    st.caption("Monitor CVA v1.0\nSave the Children México")


# ─────────────────────────────────────────────
# CARGAR DATOS
# ─────────────────────────────────────────────
with st.spinner("Cargando datos..."):
    df_salud, df_cc = cargar_datos()

# Timestamp de última actualización
def get_timestamp(nombre_enc):
    ruta = os.path.join(st.secrets.get("ONEDRIVE_FOLDER", ""), nombre_enc)
    if os.path.exists(ruta):
        ts = os.path.getmtime(ruta)
        return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")
    return "Sin datos"


# ─────────────────────────────────────────────
# MÓDULO 1: SALUD / BENEFICIARIOS
# ─────────────────────────────────────────────
if modulo == "📊 Salud / Beneficiarios":
    st.markdown("## 🏥 Monitoreo de Beneficiarios — Salud")

    ts = get_timestamp("salud_kobo.enc")
    st.caption(f"🕒 Última actualización: **{ts}**")

    if df_salud.empty:
        st.warning("Sin datos disponibles aún. El script de actualización aún no ha corrido.")
        st.stop()

    # ── Parsear fecha ──
    if COL_FECHA in df_salud.columns:
        df_salud[COL_FECHA] = pd.to_datetime(df_salud[COL_FECHA], errors="coerce")

    # ── Detectar pendientes (sin tarjeta asignada) ──
    def tiene_tarjeta(row):
        for col in [COL_TARJETA1, COL_TARJETA2, COL_TARJETA3]:
            if col in row and pd.notna(row[col]) and str(row[col]).strip() != "":
                return True
        return False

    df_salud["tiene_tarjeta"] = df_salud.apply(tiene_tarjeta, axis=1)
    pendientes = df_salud[~df_salud["tiene_tarjeta"]]
    atendidos = df_salud[df_salud["tiene_tarjeta"]]

    # ─── MÉTRICAS PRINCIPALES ───
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Total registros", len(df_salud))
    col2.metric("⏳ Pendientes", len(pendientes), delta=f"-{len(pendientes)}", delta_color="inverse")
    col3.metric("✅ Con tarjeta asignada", len(atendidos))
    if len(df_salud) > 0:
        col4.metric("📊 Cobertura", f"{round(len(atendidos)/len(df_salud)*100, 1)}%")

    st.divider()

    # ─── GRÁFICAS DEMOGRÁFICAS ───
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 👥 Distribución por Sexo")
        if COL_SEXO in df_salud.columns:
            sexo_count = df_salud[COL_SEXO].value_counts().reset_index()
            sexo_count.columns = ["Sexo", "Total"]
            fig = px.pie(sexo_count, values="Total", names="Sexo",
                         color_discrete_sequence=["#1f4e9c", "#e91e8c", "#4caf50"])
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("#### 🎂 Distribución por Edad")
        if COL_EDAD in df_salud.columns:
            df_salud[COL_EDAD] = pd.to_numeric(df_salud[COL_EDAD], errors="coerce")
            bins = [0, 5, 12, 17, 29, 59, 120]
            labels = ["0-5", "6-12", "13-17", "18-29", "30-59", "60+"]
            df_salud["grupo_edad"] = pd.cut(df_salud[COL_EDAD], bins=bins, labels=labels, right=True)
            edad_count = df_salud["grupo_edad"].value_counts().sort_index().reset_index()
            edad_count.columns = ["Grupo", "Total"]
            fig2 = px.bar(edad_count, x="Grupo", y="Total",
                          color_discrete_sequence=["#1f4e9c"])
            st.plotly_chart(fig2, use_container_width=True)

    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown("#### 🌍 País de Origen")
        if COL_PAIS in df_salud.columns:
            pais_count = df_salud[COL_PAIS].value_counts().head(10).reset_index()
            pais_count.columns = ["País", "Total"]
            fig3 = px.bar(pais_count, x="Total", y="País", orientation="h",
                          color_discrete_sequence=["#1f4e9c"])
            st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        st.markdown("#### 🏥 Servicios más requeridos")
        servicios_cols = [c for c in df_salud.columns if "Servicios que requiere" in c and "/" in c]
        if servicios_cols:
            servicios_data = {}
            for col in servicios_cols:
                nombre = col.split("/")[-1].strip()
                servicios_data[nombre] = df_salud[col].notna().sum()
            df_serv = pd.DataFrame(list(servicios_data.items()), columns=["Servicio", "Total"])
            df_serv = df_serv[df_serv["Total"] > 0].sort_values("Total", ascending=True)
            fig4 = px.bar(df_serv, x="Total", y="Servicio", orientation="h",
                          color_discrete_sequence=["#e91e8c"])
            st.plotly_chart(fig4, use_container_width=True)

    # ─── SÍNTOMAS ───
    st.markdown("#### 🤒 Síntomas más frecuentes")
    sintomas_cols = [c for c in df_salud.columns if "Síntomas del paciente/" in c]
    if sintomas_cols:
        sint_data = {}
        for col in sintomas_cols:
            nombre = col.split("/")[-1].strip()
            sint_data[nombre] = df_salud[col].notna().sum()
        df_sint = pd.DataFrame(list(sint_data.items()), columns=["Síntoma", "Total"])
        df_sint = df_sint[df_sint["Total"] > 0].sort_values("Total", ascending=False)
        fig5 = px.bar(df_sint, x="Síntoma", y="Total",
                      color_discrete_sequence=["#ff5722"])
        st.plotly_chart(fig5, use_container_width=True)

    st.divider()

    # ─── TABLA DE PENDIENTES ───
    st.markdown("#### ⏳ Personas pendientes de transferencia")

    cols_base = [COL_EDAD, COL_SEXO, COL_PAIS, COL_ENTIDAD, COL_FECHA]
    cols_pii = [COL_NOMBRE_SALUD, COL_TEL_SALUD]

    if rol in ["operator", "admin"]:
        cols_mostrar = cols_pii + cols_base
        st.info("👁 Ves nombre y teléfono porque tu rol es **operator/admin**.")
    else:
        cols_mostrar = cols_base
        st.info("🔒 Nombre y teléfono solo visibles para operadores.")

    cols_disponibles = [c for c in cols_mostrar if c in pendientes.columns]
    st.dataframe(
        pendientes[cols_disponibles].reset_index(drop=True),
        use_container_width=True,
        height=400,
    )

    st.caption(f"Total pendientes: **{len(pendientes)}** personas")


# ─────────────────────────────────────────────
# MÓDULO 2: CALL CENTER
# ─────────────────────────────────────────────
elif modulo == "📞 Call Center":
    st.markdown("## 📞 Monitoreo Call Center")

    ts = get_timestamp("datos_dudas_callcenter.enc")
    st.caption(f"🕒 Última actualización: **{ts}**")

    if df_cc.empty:
        st.warning("Sin datos disponibles aún.")
        st.stop()

    if COL_FECHA in df_cc.columns:
        df_cc[COL_FECHA] = pd.to_datetime(df_cc[COL_FECHA], errors="coerce")

    # ─── MÉTRICAS ───
    col1, col2, col3 = st.columns(3)
    col1.metric("📋 Total casos", len(df_cc))

    problemas_cols = [c for c in df_cc.columns if c.startswith("Problema/")]
    col2.metric("🔖 Tipos de problema", len(problemas_cols))

    if COL_CIUDAD_CC in df_cc.columns:
        col3.metric("🏙 Ciudades", df_cc[COL_CIUDAD_CC].nunique())

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 🔖 Casos por tipo de problema")
        if problemas_cols:
            prob_data = {}
            for col in problemas_cols:
                nombre = col.replace("Problema/", "").replace("_", " ").strip()
                prob_data[nombre] = df_cc[col].notna().sum()
            df_prob = pd.DataFrame(list(prob_data.items()), columns=["Problema", "Total"])
            df_prob = df_prob[df_prob["Total"] > 0].sort_values("Total", ascending=True)
            fig = px.bar(df_prob, x="Total", y="Problema", orientation="h",
                         color_discrete_sequence=["#1f4e9c"])
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("#### 🏙 Casos por ciudad")
        if COL_CIUDAD_CC in df_cc.columns:
            ciudad_count = df_cc[COL_CIUDAD_CC].value_counts().head(10).reset_index()
            ciudad_count.columns = ["Ciudad", "Total"]
            fig2 = px.bar(ciudad_count, x="Ciudad", y="Total",
                          color_discrete_sequence=["#e91e8c"])
            st.plotly_chart(fig2, use_container_width=True)

    # ─── TENDENCIA ───
    if COL_FECHA in df_cc.columns:
        st.markdown("#### 📈 Tendencia de casos por semana")
        df_cc["semana"] = df_cc[COL_FECHA].dt.to_period("W").astype(str)
        tendencia = df_cc.groupby("semana").size().reset_index(name="casos")
        fig3 = px.line(tendencia, x="semana", y="casos", markers=True,
                       color_discrete_sequence=["#1f4e9c"])
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # ─── TABLA DE CASOS ───
    st.markdown("#### 📋 Registro de casos")

    cols_base_cc = [COL_CIUDAD_CC, COL_PROBLEMA_CC, COL_DESC_CC, COL_SOLUCION_CC, COL_FECHA]
    cols_pii_cc = [COL_NOMBRE_CC, COL_TEL_CC]

    if rol in ["operator", "admin"]:
        cols_mostrar_cc = cols_pii_cc + cols_base_cc
        st.info("👁 Ves nombre y teléfono porque tu rol es **operator/admin**.")
    else:
        cols_mostrar_cc = cols_base_cc
        st.info("🔒 Nombre y teléfono solo visibles para operadores.")

    cols_disponibles_cc = [c for c in cols_mostrar_cc if c in df_cc.columns]
    st.dataframe(
        df_cc[cols_disponibles_cc].reset_index(drop=True),
        use_container_width=True,
        height=400,
    )
