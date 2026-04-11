import streamlit as st
import pandas as pd
import plotly.express as px
import io
import os
from datetime import datetime, date
from cryptography.fernet import Fernet
import streamlit_authenticator as stauth
import bcrypt
from io import BytesIO

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Monitor PTM — Save the Children",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# ESTILOS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stDataFrameResizable"] button[title="Download"] { display: none !important; }
    div[data-testid="stDownloadButton"] { display: none !important; }
    .metric-card {
        background: #f0f4ff;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        border-left: 4px solid #1f4e9c;
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
        border-left: 4px solid #e91e63;
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# USUARIOS Y ROLES
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
# REPORTE DEL DÍA (sin PII)
# ─────────────────────────────────────────────
def generar_reporte_dia(df: pd.DataFrame, df_cc: pd.DataFrame) -> bytes:
    hoy = date.today()
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Hoja 1 — Resumen salud
        if not df.empty and "_submission_time" in df.columns:
            df["_submission_time"] = pd.to_datetime(df["_submission_time"], errors="coerce")
            nuevos = df[df["_submission_time"].dt.date == hoy]

            resumen = pd.DataFrame({
                "Indicador": [
                    "Total registros acumulados",
                    "Nuevos registros hoy",
                    "Pendientes de tarjeta",
                    "Con tarjeta asignada",
                ],
                "Valor": [
                    len(df),
                    len(nuevos),
                    len(df[df[["Entregar tarjeta con monto 1", "Entregar tarjeta con monto 2", "Entregar tarjeta con monto 3"]].isnull().all(axis=1)]) if all(c in df.columns for c in ["Entregar tarjeta con monto 1", "Entregar tarjeta con monto 2", "Entregar tarjeta con monto 3"]) else "N/A",
                    len(df[df[["Entregar tarjeta con monto 1", "Entregar tarjeta con monto 2", "Entregar tarjeta con monto 3"]].notnull().any(axis=1)]) if all(c in df.columns for c in ["Entregar tarjeta con monto 1", "Entregar tarjeta con monto 2", "Entregar tarjeta con monto 3"]) else "N/A",
                ]
            })
            resumen.to_excel(writer, sheet_name="Resumen del día", index=False)

            # Hoja 2 — Nuevos sin PII
            cols_excluir = [
                "Nombre del paciente",
                "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)",
                "Por favor, proporcione un número de contacto alternativo",
            ]
            cols_mostrar = [c for c in nuevos.columns if c not in cols_excluir]
            nuevos[cols_mostrar].to_excel(writer, sheet_name="Nuevos registros hoy", index=False)

        # Hoja 3 — Call center hoy
        if not df_cc.empty and "_submission_time" in df_cc.columns:
            df_cc["_submission_time"] = pd.to_datetime(df_cc["_submission_time"], errors="coerce")
            cc_hoy = df_cc[df_cc["_submission_time"].dt.date == hoy]
            cols_excluir_cc = ["Nombre_de_la_persona_que_llama", "N_mero_telef_nico_de_quien_llama"]
            cols_cc = [c for c in cc_hoy.columns if c not in cols_excluir_cc]
            cc_hoy[cols_cc].to_excel(writer, sheet_name="Call Center hoy", index=False)

    return output.getvalue()

# ─────────────────────────────────────────────
# DETECCIÓN DE DUPLICADOS
# ─────────────────────────────────────────────
def detectar_duplicados(df: pd.DataFrame) -> pd.DataFrame:
    col_nombre = "Nombre del paciente"
    col_tel = "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)"
    col_entidad = "Selecciona la entidad federativa en la que te encuentras"

    if col_nombre not in df.columns or col_tel not in df.columns:
        return pd.DataFrame()

    df_temp = df[[col_nombre, col_tel, col_entidad, "_submission_time"]].copy() if col_entidad in df.columns else df[[col_nombre, col_tel, "_submission_time"]].copy()
    df_temp = df_temp.dropna(subset=[col_nombre, col_tel])
    duplicados = df_temp[df_temp.duplicated(subset=[col_nombre, col_tel], keep=False)]
    return duplicados.sort_values(col_nombre)

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
    st.caption("Monitor PTM v2.0\nSave the Children México")

# ─────────────────────────────────────────────
# CARGAR DATOS
# ─────────────────────────────────────────────
with st.spinner("Cargando datos cifrados..."):
    df_salud, df_cc = cargar_datos()

# ─────────────────────────────────────────────
# MÓDULO 1: SALUD
# ─────────────────────────────────────────────
if modulo == "📊 Salud / Beneficiarios":
    st.markdown("## 🏥 Monitoreo de Beneficiarios — Salud")

    if df_salud.empty:
        st.warning("Sin datos disponibles aún.")
        st.stop()

    # Parsear fechas
    if "_submission_time" in df_salud.columns:
        df_salud["_submission_time"] = pd.to_datetime(df_salud["_submission_time"], errors="coerce")

    # Tarjeta asignada
    cols_tarjeta = ["Entregar tarjeta con monto 1", "Entregar tarjeta con monto 2", "Entregar tarjeta con monto 3"]
    cols_tarjeta_exist = [c for c in cols_tarjeta if c in df_salud.columns]
    if cols_tarjeta_exist:
        df_salud["tiene_tarjeta"] = df_salud[cols_tarjeta_exist].notnull().any(axis=1)
    else:
        df_salud["tiene_tarjeta"] = False

    pendientes = df_salud[~df_salud["tiene_tarjeta"]]
    atendidos = df_salud[df_salud["tiene_tarjeta"]]

    # Nuevos hoy
    hoy = date.today()
    nuevos_hoy = df_salud[df_salud["_submission_time"].dt.date == hoy] if "_submission_time" in df_salud.columns else pd.DataFrame()

    # ── ALERTA NUEVOS HOY ──
    if len(nuevos_hoy) > 0:
        st.markdown(f"""
        <div class="alerta-nueva">
            🟢 <strong>{len(nuevos_hoy)} nuevos registros hoy</strong> — {hoy.strftime("%d/%m/%Y")}
        </div>
        """, unsafe_allow_html=True)

    # ── ALERTA DUPLICADOS ──
    duplicados = detectar_duplicados(df_salud)
    if len(duplicados) > 0:
        st.markdown(f"""
        <div class="alerta-duplicado">
            ⚠️ <strong>{len(duplicados)} registros posiblemente duplicados</strong> detectados por nombre y teléfono — revisa la sección de duplicados abajo.
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── MÉTRICAS ──
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("👥 Total", len(df_salud))
    col2.metric("⏳ Pendientes", len(pendientes))
    col3.metric("✅ Con tarjeta", len(atendidos))
    col4.metric("🆕 Nuevos hoy", len(nuevos_hoy))
    if len(df_salud) > 0:
        col5.metric("📊 Cobertura", f"{round(len(atendidos)/len(df_salud)*100,1)}%")

    st.divider()

    # ── GRÁFICAS ──
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 👥 Sexo")
        if "Sexo" in df_salud.columns:
            fig = px.pie(df_salud["Sexo"].value_counts().reset_index(),
                        values="count", names="Sexo",
                        color_discrete_sequence=["#1f4e9c", "#e91e8c", "#4caf50"])
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("#### 🎂 Edad")
        if "Edad del paciente" in df_salud.columns:
            df_salud["Edad del paciente"] = pd.to_numeric(df_salud["Edad del paciente"], errors="coerce")
            bins = [0, 5, 12, 17, 29, 59, 120]
            labels = ["0-5", "6-12", "13-17", "18-29", "30-59", "60+"]
            df_salud["grupo_edad"] = pd.cut(df_salud["Edad del paciente"], bins=bins, labels=labels)
            edad_count = df_salud["grupo_edad"].value_counts().sort_index().reset_index()
            fig2 = px.bar(edad_count, x="grupo_edad", y="count",
                         color_discrete_sequence=["#1f4e9c"])
            st.plotly_chart(fig2, use_container_width=True)

    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown("#### 🌍 País de origen")
        if "País de origen" in df_salud.columns:
            pais = df_salud["País de origen"].value_counts().head(10).reset_index()
            fig3 = px.bar(pais, x="count", y="País de origen", orientation="h",
                         color_discrete_sequence=["#1f4e9c"])
            st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        st.markdown("#### 🏥 Servicios requeridos")
        servicios_cols = [c for c in df_salud.columns if "Servicios que requiere" in c and "/" in c]
        if servicios_cols:
            serv_data = {col.split("/")[-1].strip(): df_salud[col].notna().sum() for col in servicios_cols}
            df_serv = pd.DataFrame(list(serv_data.items()), columns=["Servicio", "Total"])
            df_serv = df_serv[df_serv["Total"] > 0].sort_values("Total")
            fig4 = px.bar(df_serv, x="Total", y="Servicio", orientation="h",
                         color_discrete_sequence=["#e91e8c"])
            st.plotly_chart(fig4, use_container_width=True)

    # ── SÍNTOMAS ──
    st.markdown("#### 🤒 Síntomas más frecuentes")
    sint_cols = [c for c in df_salud.columns if "Síntomas del paciente/" in c]
    if sint_cols:
        sint_data = {col.split("/")[-1].strip(): df_salud[col].notna().sum() for col in sint_cols}
        df_sint = pd.DataFrame(list(sint_data.items()), columns=["Síntoma", "Total"])
        df_sint = df_sint[df_sint["Total"] > 0].sort_values("Total", ascending=False)
        fig5 = px.bar(df_sint, x="Síntoma", y="Total",
                     color_discrete_sequence=["#ff5722"])
        st.plotly_chart(fig5, use_container_width=True)

    # ── QUIÉN CAPTURÓ ──
    st.markdown("#### 👨‍⚕️ Registros por capturista")
    col_medico = "Nombre del médico/personal de salud que aplica la encuesta"
    if col_medico in df_salud.columns:
        capturas = df_salud[col_medico].value_counts().reset_index()
        capturas.columns = ["Capturista", "Registros"]
        fig6 = px.bar(capturas.head(15), x="Registros", y="Capturista",
                     orientation="h", color_discrete_sequence=["#607d8b"])
        st.plotly_chart(fig6, use_container_width=True)

    st.divider()

    # ── NUEVOS HOY ──
    if len(nuevos_hoy) > 0:
        st.markdown(f"#### 🆕 Nuevos registros de hoy — {hoy.strftime('%d/%m/%Y')}")
        cols_excluir_pii = [
            "Nombre del paciente",
            "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)",
            "Por favor, proporcione un número de contacto alternativo",
        ]
        if rol in ["operator", "admin"]:
            cols_nuevos = [c for c in nuevos_hoy.columns if c not in cols_excluir_pii[1:]]
        else:
            cols_nuevos = [c for c in nuevos_hoy.columns if c not in cols_excluir_pii]

        cols_base_nuevos = ["Nombre del paciente", "Edad del paciente", "Sexo", "País de origen",
                           "Selecciona la entidad federativa en la que te encuentras", "_submission_time"]
        cols_mostrar_nuevos = [c for c in cols_base_nuevos if c in nuevos_hoy.columns]
        if rol not in ["operator", "admin"]:
            cols_mostrar_nuevos = [c for c in cols_mostrar_nuevos if c != "Nombre del paciente"]

        st.dataframe(nuevos_hoy[cols_mostrar_nuevos].reset_index(drop=True), use_container_width=True)

    # ── DUPLICADOS ──
    st.divider()
    st.markdown("#### 🔍 Detección de duplicados")
    if len(duplicados) > 0:
        st.warning(f"⚠️ Se encontraron **{len(duplicados)}** registros con nombre y teléfono repetidos en la base.")
        col_nombre = "Nombre del paciente"
        col_tel = "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)"
        col_entidad = "Selecciona la entidad federativa en la que te encuentras"
        cols_dup = [c for c in [col_nombre, col_tel, col_entidad, "_submission_time"] if c in duplicados.columns]
        if rol not in ["operator", "admin"]:
            cols_dup = [c for c in cols_dup if c not in [col_nombre, col_tel]]
        st.dataframe(duplicados[cols_dup].reset_index(drop=True), use_container_width=True)
    else:
        st.success("✅ No se detectaron duplicados en la base.")

    # ── PENDIENTES ──
    st.divider()
    st.markdown("#### ⏳ Personas pendientes de transferencia")
    cols_base = ["Edad del paciente", "Sexo", "País de origen",
                "Selecciona la entidad federativa en la que te encuentras", "_submission_time"]
    cols_pii = ["Nombre del paciente",
               "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)"]

    if rol in ["operator", "admin"]:
        cols_mostrar = cols_pii + cols_base
        st.info("👁 Ves nombre y teléfono porque tu rol es **operator/admin**.")
    else:
        cols_mostrar = cols_base

    cols_disponibles = [c for c in cols_mostrar if c in pendientes.columns]
    st.dataframe(pendientes[cols_disponibles].reset_index(drop=True),
                use_container_width=True, height=400)

    # ── REPORTE DEL DÍA ──
    st.divider()
    st.markdown("#### 📄 Reporte del día")
    st.caption("El reporte no incluye datos personales (nombre, teléfono).")
    reporte = generar_reporte_dia(df_salud, df_cc)
    st.download_button(
        label=f"⬇️ Descargar reporte {hoy.strftime('%d-%m-%Y')}",
        data=reporte,
        file_name=f"reporte_ptm_{hoy.strftime('%d%m%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ─────────────────────────────────────────────
# MÓDULO 2: CALL CENTER
# ─────────────────────────────────────────────
elif modulo == "📞 Call Center":
    st.markdown("## 📞 Monitoreo Call Center")

    if df_cc.empty:
        st.warning("Sin datos disponibles aún.")
        st.stop()

    if "_submission_time" in df_cc.columns:
        df_cc["_submission_time"] = pd.to_datetime(df_cc["_submission_time"], errors="coerce")

    hoy = date.today()
    cc_hoy = df_cc[df_cc["_submission_time"].dt.date == hoy] if "_submission_time" in df_cc.columns else pd.DataFrame()

    if len(cc_hoy) > 0:
        st.markdown(f"""
        <div class="alerta-nueva">
            🟢 <strong>{len(cc_hoy)} nuevos casos hoy</strong> — {hoy.strftime("%d/%m/%Y")}
        </div>
        """, unsafe_allow_html=True)

    # ── MÉTRICAS ──
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📋 Total casos", len(df_cc))
    col2.metric("🆕 Casos hoy", len(cc_hoy))
    if "Ciudad" in df_cc.columns:
        col3.metric("🏙 Ciudades", df_cc["Ciudad"].nunique())
    problemas_cols = [c for c in df_cc.columns if c.startswith("Problema/")]
    col4.metric("🔖 Tipos de problema", len(problemas_cols))

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 🔖 Casos por tipo de problema")
        if problemas_cols:
            prob_data = {col.replace("Problema/", "").replace("_", " ").strip(): df_cc[col].notna().sum()
                        for col in problemas_cols}
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

    # ── TENDENCIA ──
    if "_submission_time" in df_cc.columns:
        st.markdown("#### 📈 Tendencia por semana")
        df_cc["semana"] = df_cc["_submission_time"].dt.to_period("W").astype(str)
        tendencia = df_cc.groupby("semana").size().reset_index(name="casos")
        fig3 = px.line(tendencia, x="semana", y="casos", markers=True,
                      color_discrete_sequence=["#1f4e9c"])
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # ── TABLA ──
    st.markdown("#### 📋 Registro de casos")
    cols_base_cc = ["Ciudad", "Problema", "Descripci_n_del_problema",
                   "Soluci_n_brindada", "_submission_time"]
    cols_pii_cc = ["Nombre_de_la_persona_que_llama", "N_mero_telef_nico_de_quien_llama"]

    if rol in ["operator", "admin"]:
        cols_mostrar_cc = cols_pii_cc + cols_base_cc
        st.info("👁 Ves nombre y teléfono porque tu rol es **operator/admin**.")
    else:
        cols_mostrar_cc = cols_base_cc

    cols_disp_cc = [c for c in cols_mostrar_cc if c in df_cc.columns]
    st.dataframe(df_cc[cols_disp_cc].reset_index(drop=True),
                use_container_width=True, height=400)
