import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import os
from datetime import datetime, date, timedelta
from cryptography.fernet import Fernet
import streamlit_authenticator as stauth
from io import BytesIO
import locale

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Monitor PTM — Save the Children",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Fecha en español sin locale (compatible con Streamlit Cloud)
MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
}
DIAS_ES = {
    0: "lunes", 1: "martes", 2: "miércoles", 3: "jueves",
    4: "viernes", 5: "sábado", 6: "domingo"
}

def fecha_es(d: date) -> str:
    return f"{DIAS_ES[d.weekday()]} {d.day:02d}/{d.month:02d}"

def fecha_larga_es(d: date) -> str:
    return f"{d.day} de {MESES_ES[d.month]} de {d.year}"

st.markdown("""
<style>
    [data-testid="stDataFrameResizable"] button[title="Download"] { display: none !important; }
    .header-bar {
        background: linear-gradient(90deg, #c8102e, #1f4e9c);
        padding: 14px 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    }
    .semaforo-verde { background:#e8f5e9; border-left:5px solid #4caf50; padding:10px 14px; border-radius:8px; margin-bottom:6px; }
    .semaforo-amarillo { background:#fff8e1; border-left:5px solid #ffc107; padding:10px 14px; border-radius:8px; margin-bottom:6px; }
    .semaforo-rojo { background:#fce4ec; border-left:5px solid #e53935; padding:10px 14px; border-radius:8px; margin-bottom:6px; }
    .alerta-nueva { background:#e8f5e9; border-left:4px solid #4caf50; padding:10px; border-radius:8px; margin-bottom:6px; }
    .alerta-duplicado { background:#fff3e0; border-left:4px solid #ff9800; padding:10px; border-radius:8px; margin-bottom:6px; }
    .alerta-critica { background:#fce4ec; border-left:4px solid #e53935; padding:10px; border-radius:8px; margin-bottom:6px; }
    .alerta-calidad { background:#e3f2fd; border-left:4px solid #1565c0; padding:10px; border-radius:8px; margin-bottom:6px; }
    .kpi-box { background:#f8f9fa; border-radius:10px; padding:16px; text-align:center; border:1px solid #dee2e6; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# USUARIOS
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

rol = config["credentials"]["usernames"][username]["role"]

# ─────────────────────────────────────────────
# COLUMNAS CLAVE
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
COL_CONSENTIMIENTO = "Favor de leer la siguiente nota al paciente: Buenos días. Estamos realizando un levantamiento de información con el objetivo de identificar posibles beneficiarios para recibir una tarjeta de dinero electrónico para la compra de medicamentos, estudios de laboratorio y otros productos relacionados con el cuidado de la salud. ¿Usted acepta ser entrevistado?"
COLS_PII = [COL_NOMBRE, COL_TEL, COL_TEL2]

# Composición familiar
COLS_NINAS = ["Número de niñas de 0 a 5 años", "Número de niñas de 6 a 12 años", "Número de niñas de 13 a 17 años"]
COLS_NINOS = ["Número de niños de 0 a 5 años", "Número de niños de 6 a 12 años", "Número de niños de 13 a 17 años"]
COL_EMBARAZADAS = "Número de mujeres embarazadas"
COL_LACTANTES = "Número de mujeres lactantes"
COL_DISCAPACIDAD_N = "Número de niñas o adolescentes en condición de discapacidad"
COL_DISCAPACIDAD_H = "Número de hombres adultos en condición de discapacidad"
COL_DISCAPACIDAD_M = "Número de mujeres adultas en condición de discapacidad"
COL_ADULTOS_M = "Número de mujeres de 65 años o más"
COL_ADULTOS_H = "Número de hombres de 65 años o más"
COL_JEFE_FAMILIA = "Sexo de la persona jefa de familia"

# Organizaciones de apoyo
COLS_ORGS_APOYO = ["¿De quién?/ACNUR", "¿De quién?/HIAS", "¿De quién?/DRC",
                   "¿De quién?/Médicos sin fronteras", "¿De quién?/Médicos del Mundo",
                   "¿De quién?/Sector salud de México", "¿De quién?/Otro"]

# Meta del proyecto (ajusta según tu proyecto)
META_PROYECTO = 1200

# ─────────────────────────────────────────────
# DESCIFRADO
# ─────────────────────────────────────────────
def descifrar_archivo(nombre_enc: str) -> pd.DataFrame:
    clave = st.secrets["ENCRYPTION_KEY"]
    f = Fernet(clave.encode())
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre_enc)
    if not os.path.exists(ruta):
        return pd.DataFrame()
    with open(ruta, "rb") as archivo:
        datos_cifrados = archivo.read()
    datos = f.decrypt(datos_cifrados)
    return pd.read_excel(io.BytesIO(datos))

@st.cache_data(ttl=300)
def cargar_datos():
    salud = descifrar_archivo("salud_kobo.enc")
    callcenter = descifrar_archivo("datos_dudas_callcenter.enc")
    return salud, callcenter

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def contar_sel(serie):
    return serie.apply(lambda x: pd.notna(x) and str(x).strip() not in ['', '0', 'nan', 'False', '0.0']).sum()

def suma_col(df, col):
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").fillna(0).sum()
    return 0

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

def calidad_datos(df):
    """Calcula % de completitud de campos críticos."""
    campos = {
        "Nombre": COL_NOMBRE,
        "Teléfono": COL_TEL,
        "Edad": COL_EDAD,
        "Sexo": COL_SEXO,
        "País": COL_PAIS,
        "Entidad": COL_ENTIDAD,
    }
    resultado = {}
    for nombre, col in campos.items():
        if col in df.columns:
            pct = round(df[col].notna().sum() / len(df) * 100, 1)
            resultado[nombre] = pct
    return resultado

def generar_reporte(df, df_cc, entidad_sel, periodo_dias=5):
    hoy = date.today()
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Filtrar
        df_rep = df.copy()
        if entidad_sel != "Todas" and COL_ENTIDAD in df_rep.columns:
            df_rep = df_rep[df_rep[COL_ENTIDAD] == entidad_sel]

        # Hoja 1 — Resumen
        cols_serv = [c for c in df_rep.columns if "Servicios que requiere" in c and "/" in c]
        resumen = pd.DataFrame({
            "Indicador": [
                "Total registros", f"Entidad filtrada",
                "Nuevos hoy", "Casos críticos (3+ servicios)",
                "Duplicados detectados", "Meta del proyecto", "% Alcance"
            ],
            "Valor": [
                len(df_rep), entidad_sel,
                len(df_rep[df_rep[COL_FECHA].dt.date == hoy]) if COL_FECHA in df_rep.columns else "N/A",
                len(df_rep[df_rep[cols_serv].apply(lambda r: sum(
                    pd.notna(v) and str(v).strip() not in ['','0','nan','False','0.0'] for v in r
                ), axis=1) >= 3]) if cols_serv else "N/A",
                len(detectar_duplicados(df_rep)),
                META_PROYECTO,
                f"{round(len(df_rep)/META_PROYECTO*100, 1)}%"
            ]
        })
        resumen.to_excel(writer, sheet_name="Resumen MEAL", index=False)

        # Hoja 2 — Últimos 5 días sin PII
        if COL_FECHA in df_rep.columns:
            fecha_corte = hoy - timedelta(days=periodo_dias)
            recientes = df_rep[df_rep[COL_FECHA].dt.date >= fecha_corte]
            cols_ok = [c for c in recientes.columns if c not in COLS_PII]
            recientes[cols_ok].to_excel(writer, sheet_name=f"Últimos {periodo_dias} días", index=False)

        # Hoja 3 — Análisis demográfico
        if COL_SEXO in df_rep.columns:
            demo = df_rep[COL_SEXO].value_counts().reset_index()
            demo.columns = ["Sexo", "Total"]
            demo.to_excel(writer, sheet_name="Demografía", index=False)

        # Hoja 4 — Servicios
        if cols_serv:
            serv_data = {c.split("/")[-1].strip(): contar_sel(df_rep[c]) for c in cols_serv}
            df_serv = pd.DataFrame(list(serv_data.items()), columns=["Servicio", "Personas"])
            df_serv.to_excel(writer, sheet_name="Servicios requeridos", index=False)

        # Hoja 5 — Call Center hoy
        if not df_cc.empty and COL_FECHA in df_cc.columns:
            cc_hoy = df_cc[df_cc[COL_FECHA].dt.date == hoy]
            cols_cc = [c for c in cc_hoy.columns if c not in ["Nombre_de_la_persona_que_llama", "N_mero_telef_nico_de_quien_llama"]]
            cc_hoy[cols_cc].to_excel(writer, sheet_name="Call Center hoy", index=False)

    return output.getvalue()

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
    authenticator.logout("Cerrar sesión", "sidebar")
    st.divider()
    st.caption("Monitor PTM v5.0\nSave the Children México")

# ─────────────────────────────────────────────
# CARGAR
# ─────────────────────────────────────────────
with st.spinner("Cargando datos cifrados..."):
    df_salud, df_cc = cargar_datos()

# Parsear fechas
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

    # ── FILTRO ENTIDAD ──
    entidades = ["Todas"]
    if COL_ENTIDAD in df_salud.columns:
        entidades += sorted(df_salud[COL_ENTIDAD].dropna().unique().tolist())
    entidad_sel = st.selectbox("🗺️ Filtrar por entidad federativa", entidades)

    df = df_salud.copy()
    if entidad_sel != "Todas" and COL_ENTIDAD in df.columns:
        df = df[df[COL_ENTIDAD] == entidad_sel]

    st.caption(f"Mostrando **{len(df)}** registros — **{entidad_sel}**")
    st.divider()

    # ── SERVICIOS ──
    servicios_cols = [c for c in df.columns if "Servicios que requiere el paciente:/" in c]

    def es_sel(x):
        return pd.notna(x) and str(x).strip() not in ['', '0', 'nan', 'False', '0.0']

    if servicios_cols:
        df["num_servicios"] = df[servicios_cols].apply(lambda r: sum(es_sel(v) for v in r), axis=1)
    else:
        df["num_servicios"] = 0

    # ── DATOS OPERATIVOS RECIENTES ──
    st.markdown("## 📅 Operativo reciente")

    nuevos_hoy = df[df[COL_FECHA].dt.date == hoy] if COL_FECHA in df.columns else pd.DataFrame()
    duplicados = detectar_duplicados(df)
    casos_criticos = df[df["num_servicios"] >= 3]

    # Alertas
    if len(nuevos_hoy) > 0:
        st.markdown(f"""<div class="alerta-nueva">
            🟢 <strong>{len(nuevos_hoy)} nuevos registros hoy</strong> — {fecha_es(hoy)}
        </div>""", unsafe_allow_html=True)
    if len(casos_criticos) > 0:
        st.markdown(f"""<div class="alerta-critica">
            🔴 <strong>{len(casos_criticos)} personas con 3+ servicios requeridos</strong> — requieren atención prioritaria
        </div>""", unsafe_allow_html=True)
    if len(duplicados) > 0:
        st.markdown(f"""<div class="alerta-duplicado">
            ⚠️ <strong>{len(duplicados)} posibles duplicados</strong> por nombre y teléfono
        </div>""", unsafe_allow_html=True)

    # Métricas
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("👥 Total", len(df))
    col2.metric("🆕 Nuevos hoy", len(nuevos_hoy))
    col3.metric("🔴 Prioridad alta", len(casos_criticos))
    col4.metric("⚠️ Duplicados", len(duplicados))
    col5.metric("🎯 Alcance meta", f"{round(len(df_salud)/META_PROYECTO*100,1)}%")

    st.divider()

    # Últimos 5 días
    st.markdown("#### 📆 Registros últimos 5 días")
    if COL_FECHA in df.columns:
        ultimos_5 = [(hoy - timedelta(days=i)) for i in range(4, -1, -1)]
        conteos = [{"Día": fecha_es(d), "Fecha": d, "Registros": len(df[df[COL_FECHA].dt.date == d]), "Hoy": d == hoy}
                   for d in ultimos_5]
        df_dias = pd.DataFrame(conteos)
        colores = ["#4caf50" if r else "#1f4e9c" for r in df_dias["Hoy"]]

        fig_dias = go.Figure(go.Bar(
            x=df_dias["Día"], y=df_dias["Registros"],
            marker_color=colores, text=df_dias["Registros"], textposition="outside"
        ))
        fig_dias.update_layout(showlegend=False, plot_bgcolor="white", height=280,
                               yaxis_title="Registros")
        st.plotly_chart(fig_dias, use_container_width=True)

        # Tablas expandibles por día
        st.markdown("##### Detalle por día")
        cols_tabla = [COL_NOMBRE, COL_EDAD, COL_SEXO, COL_PAIS, COL_ENTIDAD,
                     COL_MUNICIPIO, "num_servicios", COL_ESPECIALIDAD, COL_FECHA]

        for item in reversed(conteos):
            d = item["Fecha"]
            reg_dia = df[df[COL_FECHA].dt.date == d]
            label = f"{'🟢 Hoy' if d == hoy else fecha_es(d)} — {len(reg_dia)} registros"
            with st.expander(label, expanded=(d == hoy)):
                if len(reg_dia) == 0:
                    st.info("Sin registros este día.")
                else:
                    if rol in ["operator", "admin"]:
                        cols_ver = [c for c in cols_tabla if c in reg_dia.columns]
                    else:
                        cols_ver = [c for c in cols_tabla if c in reg_dia.columns and c not in COLS_PII]
                    st.dataframe(reg_dia[cols_ver].reset_index(drop=True), use_container_width=True)

    st.divider()

    # ── ANÁLISIS DEMOGRÁFICO ──
    st.markdown("## 👥 Análisis demográfico")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.markdown("#### Sexo")
        if COL_SEXO in df.columns:
            fig = px.pie(df[COL_SEXO].value_counts().reset_index(),
                        values="count", names=COL_SEXO,
                        color_discrete_sequence=["#1f4e9c", "#e91e8c", "#4caf50"])
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("#### Grupo de edad")
        if COL_EDAD in df.columns:
            df[COL_EDAD] = pd.to_numeric(df[COL_EDAD], errors="coerce")
            bins = [0, 5, 12, 17, 29, 59, 120]
            labels = ["0-5", "6-12", "13-17", "18-29", "30-59", "60+"]
            df["grupo_edad"] = pd.cut(df[COL_EDAD], bins=bins, labels=labels)
            edad_c = df["grupo_edad"].value_counts().sort_index().reset_index()
            fig2 = px.bar(edad_c, x="grupo_edad", y="count", color_discrete_sequence=["#1f4e9c"])
            st.plotly_chart(fig2, use_container_width=True)

    with col_c:
        st.markdown("#### Nacionalidad")
        if COL_PAIS in df.columns:
            pais_c = df[COL_PAIS].value_counts().head(8).reset_index()
            pais_c.columns = ["País", "Total"]
            fig3 = px.bar(pais_c, x="Total", y="País", orientation="h",
                         color_discrete_sequence=["#607d8b"])
            st.plotly_chart(fig3, use_container_width=True)

    # Composición familiar
    st.markdown("#### 👨‍👩‍👧‍👦 Composición familiar y grupos vulnerables")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)

    total_ninas = sum(suma_col(df, c) for c in COLS_NINAS)
    total_ninos = sum(suma_col(df, c) for c in COLS_NINOS)
    total_embarazadas = suma_col(df, COL_EMBARAZADAS)
    total_lactantes = suma_col(df, COL_LACTANTES)
    total_disc = suma_col(df, COL_DISCAPACIDAD_N) + suma_col(df, COL_DISCAPACIDAD_H) + suma_col(df, COL_DISCAPACIDAD_M)
    total_adultos_m = suma_col(df, COL_ADULTOS_M)
    total_adultos_h = suma_col(df, COL_ADULTOS_H)

    col_f1.metric("👧 Niñas", int(total_ninas))
    col_f2.metric("👦 Niños", int(total_ninos))
    col_f3.metric("🤰 Embarazadas", int(total_embarazadas))
    col_f4.metric("🍼 Lactantes", int(total_lactantes))

    col_f5, col_f6, col_f7, col_f8 = st.columns(4)
    col_f5.metric("♿ Discapacidad", int(total_disc))
    col_f6.metric("👵 Mujeres 65+", int(total_adultos_m))
    col_f7.metric("👴 Hombres 65+", int(total_adultos_h))
    if COL_JEFE_FAMILIA in df.columns:
        jefa_mujer = (df[COL_JEFE_FAMILIA].str.lower().str.strip() == "mujer").sum()
        col_f8.metric("👩‍👧 Jefa de hogar mujer", int(jefa_mujer))

    st.divider()

    # ── SÍNTOMAS Y SERVICIOS ──
    st.markdown("## 🏥 Síntomas y servicios requeridos")

    col_s1, col_s2 = st.columns(2)

    with col_s1:
        st.markdown("#### 🤒 Síntomas")
        sint_cols = [c for c in df.columns if "Síntomas del paciente/" in c]
        if sint_cols:
            sint_data = {c.split("/")[-1].strip(): contar_sel(df[c]) for c in sint_cols}
            df_sint = pd.DataFrame(list(sint_data.items()), columns=["Síntoma", "Total"])
            df_sint = df_sint[df_sint["Total"] > 0].sort_values("Total", ascending=False)
            fig_s = px.bar(df_sint, x="Síntoma", y="Total", color_discrete_sequence=["#ff5722"])
            st.plotly_chart(fig_s, use_container_width=True)

    with col_s2:
        st.markdown("#### 💳 Servicios / Tipo de tarjeta")
        if servicios_cols:
            serv_data = {c.split("/")[-1].strip(): contar_sel(df[c]) for c in servicios_cols}
            df_serv = pd.DataFrame(list(serv_data.items()), columns=["Servicio", "Personas"])
            df_serv = df_serv[df_serv["Personas"] > 0].sort_values("Personas")
            fig_sv = px.bar(df_serv, x="Personas", y="Servicio", orientation="h",
                           color_discrete_sequence=["#1f4e9c"])
            st.plotly_chart(fig_sv, use_container_width=True)
            st.caption("⚠️ Selección múltiple — una persona puede requerir varios tipos.")

    # Campo "Otro" servicio
    if COL_OTRO_SERVICIO in df.columns:
        otros = df[COL_OTRO_SERVICIO].dropna()
        otros = otros[otros.astype(str).str.strip().str.lower() != "nan"]
        if len(otros) > 0:
            st.markdown("##### ❓ Detalle de servicios 'Otro'")
            st.dataframe(otros.value_counts().reset_index().rename(
                columns={"index": "Descripción", COL_OTRO_SERVICIO: "Frecuencia"}
            ), use_container_width=True)

    # Especialidad requerida
    if COL_ESPECIALIDAD in df.columns:
        esp = df[COL_ESPECIALIDAD].dropna()
        esp = esp[esp.astype(str).str.strip().str.lower() != "nan"]
        if len(esp) > 0:
            st.markdown("##### 🩺 Especialidades médicas requeridas")
            esp_count = esp.value_counts().reset_index()
            esp_count.columns = ["Especialidad", "Personas"]
            fig_esp = px.bar(esp_count.head(10), x="Personas", y="Especialidad",
                            orientation="h", color_discrete_sequence=["#9c27b0"])
            st.plotly_chart(fig_esp, use_container_width=True)

    st.divider()

    # ── ESTADÍSTICAS GENERALES ──
    st.markdown("## 📊 Estadísticas generales")

    # Tendencia por mes y semana
    st.markdown("#### 📈 Tendencia de registros")
    if COL_FECHA in df.columns:
        vista_tend = st.radio("Ver por:", ["Semana", "Mes"], horizontal=True)
        if vista_tend == "Semana":
            df["periodo"] = df[COL_FECHA].dt.to_period("W").astype(str)
        else:
            df["periodo"] = df[COL_FECHA].dt.to_period("M").astype(str)
        tend = df.groupby("periodo").size().reset_index(name="Registros")
        fig_t = px.line(tend, x="periodo", y="Registros", markers=True,
                       color_discrete_sequence=["#1f4e9c"])
        fig_t.update_layout(xaxis_title="Período", plot_bgcolor="white")
        st.plotly_chart(fig_t, use_container_width=True)

    # Semáforo cobertura
    st.markdown("#### 🚦 Cobertura por entidad")
    if COL_ENTIDAD in df_salud.columns:
        cob = df_salud[COL_ENTIDAD].value_counts().reset_index()
        cob.columns = ["Entidad", "Registros"]

        col_sem1, col_sem2 = st.columns([1, 2])
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
                            color_continuous_scale=["#e53935", "#ffc107", "#4caf50"],
                            text="Registros")
            fig_cob.update_traces(textposition="outside")
            fig_cob.update_layout(coloraxis_showscale=False, plot_bgcolor="white")
            st.plotly_chart(fig_cob, use_container_width=True)

    # Organización de apoyo previo
    st.markdown("#### 🤝 Organización de apoyo previo")
    orgs_presentes = [c for c in COLS_ORGS_APOYO if c in df.columns]
    if orgs_presentes:
        org_data = {c.split("/")[-1].strip(): contar_sel(df[c]) for c in orgs_presentes}
        df_org = pd.DataFrame(list(org_data.items()), columns=["Organización", "Personas"])
        df_org = df_org[df_org["Personas"] > 0].sort_values("Personas")
        fig_org = px.bar(df_org, x="Personas", y="Organización", orientation="h",
                        color_discrete_sequence=["#00897b"])
        st.plotly_chart(fig_org, use_container_width=True)

    # Capturista + organización
    st.markdown("#### 👨‍⚕️ Registros por capturista y organización")
    if COL_MEDICO in df.columns:
        cols_cap = [c for c in [COL_MEDICO, COL_ORG] if c in df.columns]
        capturas = df.groupby(cols_cap).size().reset_index(name="Registros")
        capturas = capturas.sort_values("Registros", ascending=False).head(15)
        st.dataframe(capturas.reset_index(drop=True), use_container_width=True)

    st.divider()

    # ── TABLA COMPLETA ──
    st.markdown("## 📋 Todos los registros")
    cols_tabla_full = [
        COL_NOMBRE, COL_EDAD, COL_SEXO, COL_PAIS, COL_ENTIDAD, COL_MUNICIPIO,
        "num_servicios", COL_ESPECIALIDAD, COL_OTRO_SERVICIO, COL_FECHA
    ]
    if rol in ["operator", "admin"]:
        cols_ver_full = [c for c in cols_tabla_full if c in df.columns]
        st.info("👁 Ves nombre porque tu rol es **operator/admin**.")
    else:
        cols_ver_full = [c for c in cols_tabla_full if c in df.columns and c not in COLS_PII]

    st.dataframe(df[cols_ver_full].rename(
        columns={"num_servicios": "# Servicios"}
    ).reset_index(drop=True), use_container_width=True, height=400)

    st.divider()

    # ── DUPLICADOS ──
    st.markdown("#### 🔍 Duplicados detectados")
    if len(duplicados) > 0:
        st.warning(f"⚠️ **{len(duplicados)}** registros con mismo nombre y teléfono.")
        cols_dup = [c for c in [COL_NOMBRE, COL_TEL, COL_ENTIDAD, COL_FECHA] if c in duplicados.columns]
        if rol not in ["operator", "admin"]:
            cols_dup = [c for c in cols_dup if c not in COLS_PII]
        st.dataframe(duplicados[cols_dup].reset_index(drop=True), use_container_width=True)
    else:
        st.success("✅ Sin duplicados detectados.")

    st.divider()

    # ── REPORTE ──
    st.markdown("#### 📄 Descargar reporte")
    st.caption(f"Entidad: **{entidad_sel}** — Incluye resumen MEAL, últimos 5 días, demografía y servicios. Sin datos personales.")
    reporte = generar_reporte(df_salud, df_cc, entidad_sel)
    st.download_button(
        label=f"⬇️ Reporte {fecha_larga_es(hoy)} — {entidad_sel}",
        data=reporte,
        file_name=f"reporte_ptm_{entidad_sel}_{hoy.strftime('%d%m%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
        st.markdown(f"""<div class="alerta-nueva">
            🟢 <strong>{len(cc_hoy)} nuevos casos hoy</strong> — {fecha_es(hoy)}
        </div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("📋 Total casos", len(df_cc))
    col2.metric("🆕 Casos hoy", len(cc_hoy))
    if "Ciudad" in df_cc.columns:
        col3.metric("🏙 Ciudades", df_cc["Ciudad"].nunique())

    st.divider()

    # Últimos 5 días
    st.markdown("#### 📆 Casos últimos 5 días")
    if COL_FECHA in df_cc.columns:
        ultimos_5 = [(hoy - timedelta(days=i)) for i in range(4, -1, -1)]
        conteos_cc = [{"Día": fecha_es(d), "Casos": len(df_cc[df_cc[COL_FECHA].dt.date == d]), "Hoy": d == hoy}
                      for d in ultimos_5]
        df_cc_dias = pd.DataFrame(conteos_cc)
        colores_cc = ["#4caf50" if r else "#1f4e9c" for r in df_cc_dias["Hoy"]]
        fig_cc = go.Figure(go.Bar(x=df_cc_dias["Día"], y=df_cc_dias["Casos"],
                                  marker_color=colores_cc, text=df_cc_dias["Casos"], textposition="outside"))
        fig_cc.update_layout(showlegend=False, plot_bgcolor="white", height=280)
        st.plotly_chart(fig_cc, use_container_width=True)

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 🔖 Tipos de problema")
        problemas_cols = [c for c in df_cc.columns if c.startswith("Problema/")]
        if problemas_cols:
            prob_data = {c.replace("Problema/", "").replace("_", " ").strip(): contar_sel(df_cc[c]) for c in problemas_cols}
            df_prob = pd.DataFrame(list(prob_data.items()), columns=["Problema", "Total"])
            df_prob = df_prob[df_prob["Total"] > 0].sort_values("Total")
            fig_p = px.bar(df_prob, x="Total", y="Problema", orientation="h", color_discrete_sequence=["#1f4e9c"])
            st.plotly_chart(fig_p, use_container_width=True)

    with col_b:
        st.markdown("#### 🏙 Por ciudad")
        if "Ciudad" in df_cc.columns:
            ciudad = df_cc["Ciudad"].value_counts().head(10).reset_index()
            fig_c = px.bar(ciudad, x="count", y="Ciudad", orientation="h", color_discrete_sequence=["#e91e8c"])
            st.plotly_chart(fig_c, use_container_width=True)

    # Tendencia
    if COL_FECHA in df_cc.columns:
        st.markdown("#### 📈 Tendencia")
        vista_cc = st.radio("Ver por:", ["Semana", "Mes"], horizontal=True, key="cc_tend")
        df_cc["periodo"] = df_cc[COL_FECHA].dt.to_period("W" if vista_cc == "Semana" else "M").astype(str)
        tend_cc = df_cc.groupby("periodo").size().reset_index(name="Casos")
        fig_tc = px.line(tend_cc, x="periodo", y="Casos", markers=True, color_discrete_sequence=["#1f4e9c"])
        st.plotly_chart(fig_tc, use_container_width=True)

    st.divider()

    st.markdown("#### 📋 Registro de casos")
    cols_base_cc = ["Ciudad", "Problema", "Descripci_n_del_problema", "Soluci_n_brindada", COL_FECHA]
    cols_pii_cc = ["Nombre_de_la_persona_que_llama", "N_mero_telef_nico_de_quien_llama"]
    if rol in ["operator", "admin"]:
        cols_cc_ver = cols_pii_cc + cols_base_cc
        st.info("👁 Ves nombre y teléfono porque tu rol es **operator/admin**.")
    else:
        cols_cc_ver = cols_base_cc
    cols_disp_cc = [c for c in cols_cc_ver if c in df_cc.columns]
    st.dataframe(df_cc[cols_disp_cc].reset_index(drop=True), use_container_width=True, height=400)

# ═══════════════════════════════════════════════════════
# MÓDULO 3: MEAL & CALIDAD
# ═══════════════════════════════════════════════════════
elif modulo == "📋 MEAL & Calidad":
    st.markdown(f"""
    <div class="header-bar">
        📋 <strong>MEAL & Calidad de datos — Save the Children México</strong>
        &nbsp;|&nbsp; 📅 {fecha_larga_es(hoy)}
    </div>""", unsafe_allow_html=True)

    if df_salud.empty:
        st.warning("Sin datos disponibles aún.")
        st.stop()

    st.markdown("## 🎯 KPIs del proyecto")

    # Alcance vs meta
    alcance_pct = round(len(df_salud) / META_PROYECTO * 100, 1)
    col1, col2, col3 = st.columns(3)
    col1.metric("🎯 Meta del proyecto", META_PROYECTO)
    col2.metric("👥 Personas registradas", len(df_salud))
    col3.metric("📊 % Alcance", f"{alcance_pct}%")

    fig_meta = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=alcance_pct,
        delta={"reference": 100},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#1f4e9c"},
            "steps": [
                {"range": [0, 50], "color": "#fce4ec"},
                {"range": [50, 80], "color": "#fff8e1"},
                {"range": [80, 100], "color": "#e8f5e9"},
            ],
            "threshold": {"line": {"color": "red", "width": 4}, "thickness": 0.75, "value": 100}
        },
        title={"text": "% Alcance vs Meta"}
    ))
    fig_meta.update_layout(height=300)
    st.plotly_chart(fig_meta, use_container_width=True)

    st.divider()

    # Grupos vulnerables
    st.markdown("## 🛡️ Inclusión de grupos vulnerables")
    total = len(df_salud)
    total_ninas = sum(suma_col(df_salud, c) for c in COLS_NINAS)
    total_ninos = sum(suma_col(df_salud, c) for c in COLS_NINOS)

    vuln_data = {
        "Niñas": int(total_ninas),
        "Niños": int(total_ninos),
        "Embarazadas": int(suma_col(df_salud, COL_EMBARAZADAS)),
        "Lactantes": int(suma_col(df_salud, COL_LACTANTES)),
        "Discapacidad": int(suma_col(df_salud, COL_DISCAPACIDAD_N) + suma_col(df_salud, COL_DISCAPACIDAD_H) + suma_col(df_salud, COL_DISCAPACIDAD_M)),
        "Adultos mayores": int(suma_col(df_salud, COL_ADULTOS_M) + suma_col(df_salud, COL_ADULTOS_H)),
    }
    df_vuln = pd.DataFrame(list(vuln_data.items()), columns=["Grupo", "Total"])
    fig_vuln = px.bar(df_vuln.sort_values("Total"), x="Total", y="Grupo",
                     orientation="h", color_discrete_sequence=["#00897b"],
                     text="Total")
    fig_vuln.update_traces(textposition="outside")
    st.plotly_chart(fig_vuln, use_container_width=True)

    st.divider()

    # Calidad de datos
    st.markdown("## 🔬 Calidad de datos")
    calidad = calidad_datos(df_salud)
    if calidad:
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            for campo, pct in calidad.items():
                if pct >= 90:
                    st.markdown(f"""<div class="alerta-nueva">✅ <strong>{campo}</strong>: {pct}% completo</div>""", unsafe_allow_html=True)
                elif pct >= 70:
                    st.markdown(f"""<div class="alerta-duplicado">⚠️ <strong>{campo}</strong>: {pct}% completo</div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div class="alerta-critica">❌ <strong>{campo}</strong>: {pct}% completo — requiere atención</div>""", unsafe_allow_html=True)

        with col_c2:
            df_cal = pd.DataFrame(list(calidad.items()), columns=["Campo", "% Completitud"])
            fig_cal = px.bar(df_cal.sort_values("% Completitud"),
                            x="% Completitud", y="Campo", orientation="h",
                            color="% Completitud",
                            color_continuous_scale=["#e53935", "#ffc107", "#4caf50"],
                            range_x=[0, 100])
            fig_cal.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_cal, use_container_width=True)

    st.divider()

    # Tasa de consentimiento
    if COL_CONSENTIMIENTO in df_salud.columns:
        st.markdown("#### ✅ Tasa de consentimiento")
        consiente = df_salud[COL_CONSENTIMIENTO].str.lower().str.strip()
        si = (consiente == "sí").sum()
        no = (consiente == "no").sum()
        tasa = round(si / (si + no) * 100, 1) if (si + no) > 0 else 0
        st.metric("% que aceptó ser entrevistado", f"{tasa}%")

    st.divider()

    # Cruce Salud + Call Center
    st.markdown("## 🔗 Cruce Salud + Call Center")
    if not df_cc.empty and "N_mero_telef_nico_de_quien_llama" in df_cc.columns and COL_TEL in df_salud.columns:
        tels_salud = set(df_salud[COL_TEL].dropna().astype(str).str.strip())
        tels_cc = set(df_cc["N_mero_telef_nico_de_quien_llama"].dropna().astype(str).str.strip())
        en_ambos = tels_salud & tels_cc
        col_cr1, col_cr2, col_cr3 = st.columns(3)
        col_cr1.metric("📊 En base salud", len(tels_salud))
        col_cr2.metric("📞 En call center", len(tels_cc))
        col_cr3.metric("🔗 En ambas bases", len(en_ambos))
        if len(en_ambos) > 0:
            st.info(f"**{len(en_ambos)}** personas aparecen tanto en la base de salud como en el call center.")
