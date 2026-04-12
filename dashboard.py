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

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Monitor PTM — Save the Children",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    .semaforo-verde {
        background: #e8f5e9;
        border-left: 5px solid #4caf50;
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 6px;
    }
    .semaforo-amarillo {
        background: #fff8e1;
        border-left: 5px solid #ffc107;
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 6px;
    }
    .semaforo-rojo {
        background: #fce4ec;
        border-left: 5px solid #e53935;
        padding: 10px 14px;
        border-radius: 8px;
        margin-bottom: 6px;
    }
    .alerta-nueva {
        background: #e8f5e9;
        border-left: 4px solid #4caf50;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 6px;
    }
    .alerta-duplicado {
        background: #fff3e0;
        border-left: 4px solid #ff9800;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 6px;
    }
    .alerta-critica {
        background: #fce4ec;
        border-left: 4px solid #e53935;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# USUARIOS — reemplaza los HASH con los tuyos
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
def contar_seleccionados(serie):
    return serie.apply(
        lambda x: pd.notna(x) and str(x).strip() not in ['', '0', 'nan', 'False', '0.0']
    ).sum()

def detectar_duplicados(df):
    col_nombre = "Nombre del paciente"
    col_tel = "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)"
    col_entidad = "Selecciona la entidad federativa en la que te encuentras"
    if col_nombre not in df.columns or col_tel not in df.columns:
        return pd.DataFrame()
    cols = [c for c in [col_nombre, col_tel, col_entidad, "_submission_time"] if c in df.columns]
    df_temp = df[cols].dropna(subset=[col_nombre, col_tel])
    return df_temp[df_temp.duplicated(subset=[col_nombre, col_tel], keep=False)].sort_values(col_nombre)

def semaforo_estado(registros, umbral_rojo=50, umbral_amarillo=150):
    if registros < umbral_rojo:
        return "rojo", "🔴"
    elif registros < umbral_amarillo:
        return "amarillo", "🟡"
    else:
        return "verde", "🟢"

def generar_reporte_dia(df, df_cc, entidad_filtro=None):
    hoy = date.today()
    output = BytesIO()
    cols_pii = [
        "Nombre del paciente",
        "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)",
        "Por favor, proporcione un número de contacto alternativo",
    ]
    col_entidad = "Selecciona la entidad federativa en la que te encuentras"

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if not df.empty and "_submission_time" in df.columns:
            df_rep = df.copy()
            if entidad_filtro and entidad_filtro != "Todas" and col_entidad in df_rep.columns:
                df_rep = df_rep[df_rep[col_entidad] == entidad_filtro]

            nuevos = df_rep[df_rep["_submission_time"].dt.date == hoy]
            resumen = pd.DataFrame({
                "Indicador": ["Total registros", "Nuevos hoy", "Entidad filtrada"],
                "Valor": [len(df_rep), len(nuevos), entidad_filtro or "Todas"]
            })
            resumen.to_excel(writer, sheet_name="Resumen", index=False)
            cols_ok = [c for c in nuevos.columns if c not in cols_pii]
            nuevos[cols_ok].to_excel(writer, sheet_name="Nuevos hoy", index=False)

        if not df_cc.empty and "_submission_time" in df_cc.columns:
            cc_hoy = df_cc[df_cc["_submission_time"].dt.date == hoy]
            cols_pii_cc = ["Nombre_de_la_persona_que_llama", "N_mero_telef_nico_de_quien_llama"]
            cols_cc = [c for c in cc_hoy.columns if c not in cols_pii_cc]
            cc_hoy[cols_cc].to_excel(writer, sheet_name="Call Center hoy", index=False)

    return output.getvalue()

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 👤 {name}")
    st.caption(f"Rol: `{rol}`")
    st.divider()

    modulo = st.radio("Módulo", ["📊 Salud / Beneficiarios", "📞 Call Center"],
                      label_visibility="collapsed")
    st.divider()

    if st.button("🔄 Actualizar datos"):
        st.cache_data.clear()
        st.rerun()

    authenticator.logout("Cerrar sesión", "sidebar")
    st.divider()
    st.caption("Monitor PTM v4.0\nSave the Children México")

# ─────────────────────────────────────────────
# CARGAR DATOS
# ─────────────────────────────────────────────
with st.spinner("Cargando datos cifrados..."):
    df_salud, df_cc = cargar_datos()

# ═══════════════════════════════════════════════
# MÓDULO 1: SALUD
# ═══════════════════════════════════════════════
if modulo == "📊 Salud / Beneficiarios":

    # ── HEADER ──
    hoy = date.today()
    st.markdown(f"""
    <div class="header-bar">
        🏥 <strong>Monitor PTM — Save the Children México</strong>
        &nbsp;&nbsp;|&nbsp;&nbsp;
        📅 {hoy.strftime("%d de %B de %Y")}
        &nbsp;&nbsp;|&nbsp;&nbsp;
        👤 {name} ({rol})
    </div>
    """, unsafe_allow_html=True)

    if df_salud.empty:
        st.warning("Sin datos disponibles aún.")
        st.stop()

    # Parsear fechas
    if "_submission_time" in df_salud.columns:
        df_salud["_submission_time"] = pd.to_datetime(df_salud["_submission_time"], errors="coerce")

    col_entidad = "Selecciona la entidad federativa en la que te encuentras"

    # ── FILTRO POR ENTIDAD ──
    entidades = ["Todas"]
    if col_entidad in df_salud.columns:
        entidades += sorted(df_salud[col_entidad].dropna().unique().tolist())

    entidad_sel = st.selectbox("🗺️ Filtrar por entidad federativa", entidades)

    df = df_salud.copy()
    if entidad_sel != "Todas" and col_entidad in df.columns:
        df = df[df[col_entidad] == entidad_sel]

    st.caption(f"Mostrando **{len(df)}** registros de **{entidad_sel}**")
    st.divider()

    # ── ALERTAS ──
    nuevos_hoy = df[df["_submission_time"].dt.date == hoy] if "_submission_time" in df.columns else pd.DataFrame()
    duplicados = detectar_duplicados(df)

    # Casos críticos — 3+ servicios
    servicios_cols = [c for c in df.columns if "Servicios que requiere el paciente:/" in c]
    if servicios_cols:
        def es_seleccionado(x):
            return pd.notna(x) and str(x).strip() not in ['', '0', 'nan', 'False', '0.0']
        df["num_servicios"] = df[servicios_cols].apply(
            lambda row: sum(es_seleccionado(v) for v in row), axis=1
        )
        casos_criticos = df[df["num_servicios"] >= 3]
    else:
        df["num_servicios"] = 0
        casos_criticos = pd.DataFrame()

    if len(nuevos_hoy) > 0:
        st.markdown(f"""<div class="alerta-nueva">
            🟢 <strong>{len(nuevos_hoy)} nuevos registros hoy</strong> — {hoy.strftime("%d/%m/%Y")}
        </div>""", unsafe_allow_html=True)

    if len(casos_criticos) > 0:
        st.markdown(f"""<div class="alerta-critica">
            🔴 <strong>{len(casos_criticos)} casos críticos</strong> — personas con 3 o más servicios requeridos. Prioridad de atención.
        </div>""", unsafe_allow_html=True)

    if len(duplicados) > 0:
        st.markdown(f"""<div class="alerta-duplicado">
            ⚠️ <strong>{len(duplicados)} posibles duplicados</strong> detectados por nombre y teléfono.
        </div>""", unsafe_allow_html=True)

    # ── MÉTRICAS ──
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Total registros", len(df))
    col2.metric("🆕 Nuevos hoy", len(nuevos_hoy))
    col3.metric("🔴 Casos críticos", len(casos_criticos))
    col4.metric("⚠️ Duplicados", len(duplicados))

    st.divider()

    # ── ÚLTIMOS 5 DÍAS ──
    st.markdown("#### 📅 Registros — últimos 5 días")
    if "_submission_time" in df.columns:
        ultimos_5 = [(hoy - timedelta(days=i)) for i in range(4, -1, -1)]
        conteos_dias = []
        for dia in ultimos_5:
            registros_dia = df[df["_submission_time"].dt.date == dia]
            conteos_dias.append({
                "Día": dia.strftime("%a %d/%m"),
                "Fecha": dia,
                "Registros": len(registros_dia),
                "Es hoy": dia == hoy
            })

        df_dias = pd.DataFrame(conteos_dias)
        colores = ["#1f4e9c" if not r else "#4caf50" for r in df_dias["Es hoy"]]

        fig_dias = go.Figure(go.Bar(
            x=df_dias["Día"],
            y=df_dias["Registros"],
            marker_color=colores,
            text=df_dias["Registros"],
            textposition="outside"
        ))
        fig_dias.update_layout(
            showlegend=False,
            yaxis_title="Registros",
            plot_bgcolor="white",
            height=300
        )
        st.plotly_chart(fig_dias, use_container_width=True)

        # Tabla expandible por día
        st.markdown("##### Ver registros por día")
        cols_pii = [
            "Nombre del paciente",
            "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)"
        ]
        cols_tabla = ["Nombre del paciente", "Edad del paciente", "Sexo",
                     "País de origen", col_entidad, "_submission_time"]

        for item in reversed(conteos_dias):
            dia = item["Fecha"]
            registros_dia = df[df["_submission_time"].dt.date == dia]
            label = f"{'🟢 Hoy' if dia == hoy else dia.strftime('%A %d/%m')} — {len(registros_dia)} registros"

            with st.expander(label, expanded=(dia == hoy)):
                if len(registros_dia) == 0:
                    st.info("Sin registros este día.")
                else:
                    if rol in ["operator", "admin"]:
                        cols_ver = [c for c in cols_tabla if c in registros_dia.columns]
                    else:
                        cols_ver = [c for c in cols_tabla if c in registros_dia.columns and c not in cols_pii]
                    st.dataframe(registros_dia[cols_ver].reset_index(drop=True),
                                use_container_width=True)

    st.divider()

    # ── SEMÁFORO DE COBERTURA ──
    st.markdown("#### 🚦 Semáforo de cobertura por entidad")
    if col_entidad in df_salud.columns:
        cobertura_estados = df_salud[col_entidad].value_counts().reset_index()
        cobertura_estados.columns = ["Entidad", "Registros"]

        col_sem_a, col_sem_b = st.columns([1, 2])

        with col_sem_a:
            for _, row in cobertura_estados.iterrows():
                nivel, emoji = semaforo_estado(row["Registros"])
                css_class = f"semaforo-{nivel}"
                st.markdown(f"""
                <div class="{css_class}">
                    {emoji} <strong>{row['Entidad']}</strong> — {row['Registros']} registros
                </div>""", unsafe_allow_html=True)

            st.caption("🔴 < 50 &nbsp; 🟡 50–150 &nbsp; 🟢 > 150")

        with col_sem_b:
            cobertura_estados_sorted = cobertura_estados.sort_values("Registros")
            fig_cob = px.bar(
                cobertura_estados_sorted,
                x="Registros", y="Entidad",
                orientation="h",
                color="Registros",
                color_continuous_scale=["#e53935", "#ffc107", "#4caf50"],
                text="Registros"
            )
            fig_cob.update_traces(textposition="outside")
            fig_cob.update_layout(coloraxis_showscale=False, plot_bgcolor="white")
            st.plotly_chart(fig_cob, use_container_width=True)

    st.divider()

    # ── CASOS CRÍTICOS ──
    st.markdown("#### 🔴 Casos críticos — 3 o más servicios requeridos")
    if len(casos_criticos) > 0:
        st.caption(f"Estas {len(casos_criticos)} personas tienen mayor vulnerabilidad y deben priorizarse.")

        servicios_nombres = [c.split("/")[-1].strip() for c in servicios_cols]

        cols_criticos_base = ["Edad del paciente", "Sexo", col_entidad, "num_servicios", "_submission_time"]
        cols_pii_crit = ["Nombre del paciente",
                        "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)"]

        if rol in ["operator", "admin"]:
            cols_criticos = cols_pii_crit + cols_criticos_base
        else:
            cols_criticos = cols_criticos_base

        cols_disp = [c for c in cols_criticos if c in casos_criticos.columns]
        casos_criticos_sorted = casos_criticos.sort_values("num_servicios", ascending=False)
        st.dataframe(casos_criticos_sorted[cols_disp].rename(
            columns={"num_servicios": "# Servicios requeridos"}
        ).reset_index(drop=True), use_container_width=True, height=350)
    else:
        st.success("✅ No hay casos con 3 o más servicios simultáneos.")

    st.divider()

    # ── SEXO Y EDAD ──
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 👥 Sexo")
        if "Sexo" in df.columns:
            fig = px.pie(df["Sexo"].value_counts().reset_index(),
                        values="count", names="Sexo",
                        color_discrete_sequence=["#1f4e9c", "#e91e8c", "#4caf50"])
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("#### 🎂 Grupo de edad")
        if "Edad del paciente" in df.columns:
            df["Edad del paciente"] = pd.to_numeric(df["Edad del paciente"], errors="coerce")
            bins = [0, 5, 12, 17, 29, 59, 120]
            labels = ["0-5", "6-12", "13-17", "18-29", "30-59", "60+"]
            df["grupo_edad"] = pd.cut(df["Edad del paciente"], bins=bins, labels=labels)
            edad_count = df["grupo_edad"].value_counts().sort_index().reset_index()
            fig2 = px.bar(edad_count, x="grupo_edad", y="count",
                         color_discrete_sequence=["#1f4e9c"])
            st.plotly_chart(fig2, use_container_width=True)

    # ── SÍNTOMAS ──
    st.markdown("#### 🤒 Síntomas más frecuentes")
    sint_cols = [c for c in df.columns if "Síntomas del paciente/" in c]
    if sint_cols:
        sint_data = {col.split("/")[-1].strip(): contar_seleccionados(df[col]) for col in sint_cols}
        df_sint = pd.DataFrame(list(sint_data.items()), columns=["Síntoma", "Total"])
        df_sint = df_sint[df_sint["Total"] > 0].sort_values("Total", ascending=False)
        fig_sint = px.bar(df_sint, x="Síntoma", y="Total", color_discrete_sequence=["#ff5722"])
        st.plotly_chart(fig_sint, use_container_width=True)

    # ── SERVICIOS / TARJETA ──
    st.markdown("#### 💳 Servicios requeridos — Tipo de tarjeta")
    if servicios_cols:
        serv_data = {col.split("/")[-1].strip(): contar_seleccionados(df[col]) for col in servicios_cols}
        df_serv = pd.DataFrame(list(serv_data.items()), columns=["Servicio", "Personas"])
        df_serv = df_serv[df_serv["Personas"] > 0].sort_values("Personas")
        fig_serv = px.bar(df_serv, x="Personas", y="Servicio", orientation="h",
                         color_discrete_sequence=["#1f4e9c"])
        st.plotly_chart(fig_serv, use_container_width=True)
        st.caption("⚠️ Una persona puede requerir más de un tipo de tarjeta.")

    st.divider()

    # ── TENDENCIA SEMANAL ──
    st.markdown("#### 📈 Tendencia de registros por semana")
    if "_submission_time" in df.columns:
        df["semana"] = df["_submission_time"].dt.to_period("W").astype(str)
        tendencia = df.groupby("semana").size().reset_index(name="Registros")
        fig_tend = px.line(tendencia, x="semana", y="Registros", markers=True,
                          color_discrete_sequence=["#1f4e9c"])
        st.plotly_chart(fig_tend, use_container_width=True)

    st.divider()

    # ── QUIÉN CAPTURÓ ──
    st.markdown("#### 👨‍⚕️ Registros por capturista")
    col_medico = "Nombre del médico/personal de salud que aplica la encuesta"
    if col_medico in df.columns:
        capturas = df[col_medico].value_counts().head(15).reset_index()
        capturas.columns = ["Capturista", "Registros"]
        fig_cap = px.bar(capturas, x="Registros", y="Capturista",
                        orientation="h", color_discrete_sequence=["#607d8b"])
        st.plotly_chart(fig_cap, use_container_width=True)

    st.divider()

    # ── DUPLICADOS ──
    st.markdown("#### 🔍 Duplicados detectados")
    if len(duplicados) > 0:
        st.warning(f"⚠️ **{len(duplicados)}** registros con mismo nombre y teléfono.")
        col_nombre = "Nombre del paciente"
        col_tel = "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)"
        cols_dup = [c for c in [col_nombre, col_tel, col_entidad, "_submission_time"] if c in duplicados.columns]
        if rol not in ["operator", "admin"]:
            cols_dup = [c for c in cols_dup if c not in [col_nombre, col_tel]]
        st.dataframe(duplicados[cols_dup].reset_index(drop=True), use_container_width=True)
    else:
        st.success("✅ Sin duplicados detectados.")

    st.divider()

    # ── REPORTE DEL DÍA ──
    st.markdown("#### 📄 Reporte del día")
    st.caption(f"Entidad: **{entidad_sel}** — Sin datos personales.")
    reporte = generar_reporte_dia(df_salud, df_cc, entidad_sel)
    st.download_button(
        label=f"⬇️ Descargar reporte {hoy.strftime('%d-%m-%Y')} — {entidad_sel}",
        data=reporte,
        file_name=f"reporte_ptm_{entidad_sel}_{hoy.strftime('%d%m%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ═══════════════════════════════════════════════
# MÓDULO 2: CALL CENTER
# ═══════════════════════════════════════════════
elif modulo == "📞 Call Center":
    hoy = date.today()
    st.markdown(f"""
    <div class="header-bar">
        📞 <strong>Monitor Call Center — Save the Children México</strong>
        &nbsp;&nbsp;|&nbsp;&nbsp;
        📅 {hoy.strftime("%d de %B de %Y")}
    </div>
    """, unsafe_allow_html=True)

    if df_cc.empty:
        st.warning("Sin datos disponibles aún.")
        st.stop()

    if "_submission_time" in df_cc.columns:
        df_cc["_submission_time"] = pd.to_datetime(df_cc["_submission_time"], errors="coerce")

    cc_hoy = df_cc[df_cc["_submission_time"].dt.date == hoy] if "_submission_time" in df_cc.columns else pd.DataFrame()

    if len(cc_hoy) > 0:
        st.markdown(f"""<div class="alerta-nueva">
            🟢 <strong>{len(cc_hoy)} nuevos casos hoy</strong> — {hoy.strftime("%d/%m/%Y")}
        </div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("📋 Total casos", len(df_cc))
    col2.metric("🆕 Casos hoy", len(cc_hoy))
    if "Ciudad" in df_cc.columns:
        col3.metric("🏙 Ciudades", df_cc["Ciudad"].nunique())

    st.divider()

    # ── ÚLTIMOS 5 DÍAS CALL CENTER ──
    st.markdown("#### 📅 Casos — últimos 5 días")
    if "_submission_time" in df_cc.columns:
        ultimos_5 = [(hoy - timedelta(days=i)) for i in range(4, -1, -1)]
        conteos_cc = []
        for dia in ultimos_5:
            n = len(df_cc[df_cc["_submission_time"].dt.date == dia])
            conteos_cc.append({"Día": dia.strftime("%a %d/%m"), "Casos": n, "Es hoy": dia == hoy})

        df_dias_cc = pd.DataFrame(conteos_cc)
        colores_cc = ["#1f4e9c" if not r else "#4caf50" for r in df_dias_cc["Es hoy"]]
        fig_cc_dias = go.Figure(go.Bar(
            x=df_dias_cc["Día"], y=df_dias_cc["Casos"],
            marker_color=colores_cc, text=df_dias_cc["Casos"], textposition="outside"
        ))
        fig_cc_dias.update_layout(showlegend=False, plot_bgcolor="white", height=280)
        st.plotly_chart(fig_cc_dias, use_container_width=True)

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 🔖 Tipos de problema")
        problemas_cols = [c for c in df_cc.columns if c.startswith("Problema/")]
        if problemas_cols:
            prob_data = {
                col.replace("Problema/", "").replace("_", " ").strip(): contar_seleccionados(df_cc[col])
                for col in problemas_cols
            }
            df_prob = pd.DataFrame(list(prob_data.items()), columns=["Problema", "Total"])
            df_prob = df_prob[df_prob["Total"] > 0].sort_values("Total")
            fig = px.bar(df_prob, x="Total", y="Problema", orientation="h",
                        color_discrete_sequence=["#1f4e9c"])
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("#### 🏙 Casos por ciudad")
        if "Ciudad" in df_cc.columns:
            ciudad = df_cc["Ciudad"].value_counts().head(10).reset_index()
            fig2 = px.bar(ciudad, x="count", y="Ciudad", orientation="h",
                         color_discrete_sequence=["#e91e8c"])
            st.plotly_chart(fig2, use_container_width=True)

    if "_submission_time" in df_cc.columns:
        st.markdown("#### 📈 Tendencia semanal")
        df_cc["semana"] = df_cc["_submission_time"].dt.to_period("W").astype(str)
        tendencia = df_cc.groupby("semana").size().reset_index(name="Casos")
        fig3 = px.line(tendencia, x="semana", y="Casos", markers=True,
                      color_discrete_sequence=["#1f4e9c"])
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    st.markdown("#### 📋 Registro de casos")
    cols_base_cc = ["Ciudad", "Problema", "Descripci_n_del_problema", "Soluci_n_brindada", "_submission_time"]
    cols_pii_cc = ["Nombre_de_la_persona_que_llama", "N_mero_telef_nico_de_quien_llama"]
    if rol in ["operator", "admin"]:
        cols_mostrar_cc = cols_pii_cc + cols_base_cc
        st.info("👁 Ves nombre y teléfono porque tu rol es **operator/admin**.")
    else:
        cols_mostrar_cc = cols_base_cc
    cols_disp_cc = [c for c in cols_mostrar_cc if c in df_cc.columns]
    st.dataframe(df_cc[cols_disp_cc].reset_index(drop=True), use_container_width=True, height=400)
