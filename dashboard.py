import streamlit as st
import pandas as pd
import plotly.express as px
import io
import os
from datetime import datetime, date
from cryptography.fernet import Fernet
import streamlit_authenticator as stauth
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
    """Cuenta solo valores realmente seleccionados en campos múltiples de Kobo."""
    return serie.apply(
        lambda x: pd.notna(x) and str(x).strip() not in ['', '0', 'nan', 'False', '0.0']
    ).sum()

def detectar_duplicados(df: pd.DataFrame) -> pd.DataFrame:
    col_nombre = "Nombre del paciente"
    col_tel = "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)"
    col_entidad = "Selecciona la entidad federativa en la que te encuentras"
    if col_nombre not in df.columns or col_tel not in df.columns:
        return pd.DataFrame()
    cols = [c for c in [col_nombre, col_tel, col_entidad, "_submission_time"] if c in df.columns]
    df_temp = df[cols].dropna(subset=[col_nombre, col_tel])
    duplicados = df_temp[df_temp.duplicated(subset=[col_nombre, col_tel], keep=False)]
    return duplicados.sort_values(col_nombre)

def generar_reporte_dia(df: pd.DataFrame, df_cc: pd.DataFrame) -> bytes:
    hoy = date.today()
    output = BytesIO()
    cols_pii = [
        "Nombre del paciente",
        "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)",
        "Por favor, proporcione un número de contacto alternativo",
    ]
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if not df.empty and "_submission_time" in df.columns:
            df["_submission_time"] = pd.to_datetime(df["_submission_time"], errors="coerce")
            nuevos = df[df["_submission_time"].dt.date == hoy]

            resumen = pd.DataFrame({
                "Indicador": ["Total registros acumulados", "Nuevos registros hoy"],
                "Valor": [len(df), len(nuevos)]
            })
            resumen.to_excel(writer, sheet_name="Resumen del día", index=False)

            cols_ok = [c for c in nuevos.columns if c not in cols_pii]
            nuevos[cols_ok].to_excel(writer, sheet_name="Nuevos hoy sin PII", index=False)

        if not df_cc.empty and "_submission_time" in df_cc.columns:
            df_cc["_submission_time"] = pd.to_datetime(df_cc["_submission_time"], errors="coerce")
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
    st.caption("Monitor PTM v3.0\nSave the Children México")

# ─────────────────────────────────────────────
# CARGAR DATOS
# ─────────────────────────────────────────────
with st.spinner("Cargando datos cifrados..."):
    df_salud, df_cc = cargar_datos()

# ═══════════════════════════════════════════════
# MÓDULO 1: SALUD
# ═══════════════════════════════════════════════
if modulo == "📊 Salud / Beneficiarios":
    st.markdown("## 🏥 Monitoreo de Beneficiarios — Salud")

    if df_salud.empty:
        st.warning("Sin datos disponibles aún.")
        st.stop()

    if "_submission_time" in df_salud.columns:
        df_salud["_submission_time"] = pd.to_datetime(df_salud["_submission_time"], errors="coerce")

    hoy = date.today()
    nuevos_hoy = df_salud[df_salud["_submission_time"].dt.date == hoy] if "_submission_time" in df_salud.columns else pd.DataFrame()
    duplicados = detectar_duplicados(df_salud)

    # ── ALERTAS ──
    if len(nuevos_hoy) > 0:
        st.markdown(f"""
        <div class="alerta-nueva">
            🟢 <strong>{len(nuevos_hoy)} nuevos registros hoy</strong> — {hoy.strftime("%d/%m/%Y")}
        </div>""", unsafe_allow_html=True)

    if len(duplicados) > 0:
        st.markdown(f"""
        <div class="alerta-duplicado">
            ⚠️ <strong>{len(duplicados)} registros posiblemente duplicados</strong> detectados por nombre y teléfono.
        </div>""", unsafe_allow_html=True)

    st.divider()

    # ── MÉTRICAS ──
    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Total registros", len(df_salud))
    col2.metric("🆕 Nuevos hoy", len(nuevos_hoy))
    col3.metric("⚠️ Duplicados detectados", len(duplicados))

    st.divider()

    # ── SEXO Y EDAD ──
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 👥 Sexo")
        if "Sexo" in df_salud.columns:
            fig = px.pie(df_salud["Sexo"].value_counts().reset_index(),
                        values="count", names="Sexo",
                        color_discrete_sequence=["#1f4e9c", "#e91e8c", "#4caf50"])
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("#### 🎂 Grupo de edad")
        if "Edad del paciente" in df_salud.columns:
            df_salud["Edad del paciente"] = pd.to_numeric(df_salud["Edad del paciente"], errors="coerce")
            bins = [0, 5, 12, 17, 29, 59, 120]
            labels = ["0-5", "6-12", "13-17", "18-29", "30-59", "60+"]
            df_salud["grupo_edad"] = pd.cut(df_salud["Edad del paciente"], bins=bins, labels=labels)
            edad_count = df_salud["grupo_edad"].value_counts().sort_index().reset_index()
            fig2 = px.bar(edad_count, x="grupo_edad", y="count",
                         color_discrete_sequence=["#1f4e9c"])
            st.plotly_chart(fig2, use_container_width=True)

    # ── SÍNTOMAS CORREGIDO ──
    st.markdown("#### 🤒 Síntomas más frecuentes")
    sint_cols = [c for c in df_salud.columns if "Síntomas del paciente/" in c]
    if sint_cols:
        sint_data = {
            col.split("/")[-1].strip(): contar_seleccionados(df_salud[col])
            for col in sint_cols
        }
        df_sint = pd.DataFrame(list(sint_data.items()), columns=["Síntoma", "Total"])
        df_sint = df_sint[df_sint["Total"] > 0].sort_values("Total", ascending=False)
        fig_sint = px.bar(df_sint, x="Síntoma", y="Total",
                         color_discrete_sequence=["#ff5722"])
        st.plotly_chart(fig_sint, use_container_width=True)

    st.divider()

    # ── SERVICIOS Y TIPO DE TARJETA ──
    st.markdown("#### 💳 Servicios requeridos — Tipo de tarjeta a asignar")
    servicios_cols = [c for c in df_salud.columns if "Servicios que requiere el paciente:/" in c]
    if servicios_cols:
        serv_data = {
            col.split("/")[-1].strip(): contar_seleccionados(df_salud[col])
            for col in servicios_cols
        }
        df_serv = pd.DataFrame(list(serv_data.items()), columns=["Servicio / Tipo de tarjeta", "Personas"])
        df_serv = df_serv[df_serv["Personas"] > 0].sort_values("Personas", ascending=True)

        fig_serv = px.bar(df_serv, x="Personas", y="Servicio / Tipo de tarjeta",
                         orientation="h",
                         color_discrete_sequence=["#1f4e9c"],
                         title="Cada barra = personas que necesitan ese tipo de tarjeta")
        st.plotly_chart(fig_serv, use_container_width=True)

        # Tabla resumen servicios múltiples
        st.caption("⚠️ Una persona puede necesitar más de un tipo de tarjeta (selección múltiple)")
        total_servicios = df_serv["Personas"].sum()
        st.caption(f"Total de servicios requeridos en toda la base: **{total_servicios}** (entre {len(df_salud)} personas)")

    st.divider()

    # ── COBERTURA POR ESTADO ──
    st.markdown("#### 🗺️ Cobertura por entidad federativa")
    col_entidad = "Selecciona la entidad federativa en la que te encuentras"
    if col_entidad in df_salud.columns:
        cobertura = df_salud[col_entidad].value_counts().reset_index()
        cobertura.columns = ["Entidad", "Registros"]
        cobertura["% del total"] = (cobertura["Registros"] / len(df_salud) * 100).round(1)
        cobertura = cobertura.sort_values("Registros", ascending=True)

        fig_cob = px.bar(cobertura, x="Registros", y="Entidad",
                        orientation="h",
                        color="Registros",
                        color_continuous_scale=["#c8d8ff", "#1f4e9c"],
                        text="% del total")
        fig_cob.update_traces(texttemplate="%{text}%", textposition="outside")
        st.plotly_chart(fig_cob, use_container_width=True)

    st.divider()

    # ── TENDENCIA POR SEMANA ──
    st.markdown("#### 📈 Tendencia de registros por semana")
    if "_submission_time" in df_salud.columns:
        df_salud["semana"] = df_salud["_submission_time"].dt.to_period("W").astype(str)
        tendencia = df_salud.groupby("semana").size().reset_index(name="Registros")
        fig_tend = px.line(tendencia, x="semana", y="Registros", markers=True,
                          color_discrete_sequence=["#1f4e9c"])
        fig_tend.update_layout(xaxis_title="Semana", yaxis_title="Nuevos registros")
        st.plotly_chart(fig_tend, use_container_width=True)

    st.divider()

    # ── NUEVOS HOY POR ENTIDAD Y MUNICIPIO ──
    if len(nuevos_hoy) > 0:
        st.markdown(f"#### 🆕 Nuevos registros hoy — {hoy.strftime('%d/%m/%Y')}")

        col_mun = "Municipio:"
        col_ent = "Selecciona la entidad federativa en la que te encuentras"

        col_x, col_y = st.columns(2)
        with col_x:
            if col_ent in nuevos_hoy.columns:
                ent_hoy = nuevos_hoy[col_ent].value_counts().reset_index()
                ent_hoy.columns = ["Entidad", "Nuevos"]
                fig_ent = px.bar(ent_hoy, x="Nuevos", y="Entidad", orientation="h",
                                color_discrete_sequence=["#4caf50"])
                st.plotly_chart(fig_ent, use_container_width=True)

        with col_y:
            if col_mun in nuevos_hoy.columns:
                mun_hoy = nuevos_hoy[col_mun].value_counts().head(10).reset_index()
                mun_hoy.columns = ["Municipio", "Nuevos"]
                fig_mun = px.bar(mun_hoy, x="Nuevos", y="Municipio", orientation="h",
                                color_discrete_sequence=["#4caf50"])
                st.plotly_chart(fig_mun, use_container_width=True)

        # Tabla nuevos hoy
        cols_pii = ["Nombre del paciente",
                   "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)"]
        cols_base_nuevos = ["Nombre del paciente", "Edad del paciente", "Sexo",
                           "País de origen", col_ent, col_mun, "_submission_time"]

        if rol in ["operator", "admin"]:
            cols_ver = [c for c in cols_base_nuevos if c in nuevos_hoy.columns]
        else:
            cols_ver = [c for c in cols_base_nuevos if c in nuevos_hoy.columns and c not in cols_pii]

        st.dataframe(nuevos_hoy[cols_ver].reset_index(drop=True), use_container_width=True)

    st.divider()

    # ── QUIÉN CAPTURÓ ──
    st.markdown("#### 👨‍⚕️ Registros por capturista")
    col_medico = "Nombre del médico/personal de salud que aplica la encuesta"
    if col_medico in df_salud.columns:
        capturas = df_salud[col_medico].value_counts().head(15).reset_index()
        capturas.columns = ["Capturista", "Registros"]
        fig_cap = px.bar(capturas, x="Registros", y="Capturista",
                        orientation="h", color_discrete_sequence=["#607d8b"])
        st.plotly_chart(fig_cap, use_container_width=True)

    st.divider()

    # ── DUPLICADOS ──
    st.markdown("#### 🔍 Registros duplicados detectados")
    if len(duplicados) > 0:
        st.warning(f"⚠️ **{len(duplicados)}** registros con mismo nombre y teléfono en la base.")
        col_nombre = "Nombre del paciente"
        col_tel = "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)"
        col_ent2 = "Selecciona la entidad federativa en la que te encuentras"
        cols_dup = [c for c in [col_nombre, col_tel, col_ent2, "_submission_time"] if c in duplicados.columns]
        if rol not in ["operator", "admin"]:
            cols_dup = [c for c in cols_dup if c not in [col_nombre, col_tel]]
        st.dataframe(duplicados[cols_dup].reset_index(drop=True), use_container_width=True)
    else:
        st.success("✅ No se detectaron duplicados.")

    st.divider()

    # ── REPORTE DEL DÍA ──
    st.markdown("#### 📄 Reporte del día")
    st.caption("Sin datos personales (nombre, teléfono).")
    reporte = generar_reporte_dia(df_salud, df_cc)
    st.download_button(
        label=f"⬇️ Descargar reporte {hoy.strftime('%d-%m-%Y')}",
        data=reporte,
        file_name=f"reporte_ptm_{hoy.strftime('%d%m%Y')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# ═══════════════════════════════════════════════
# MÓDULO 2: CALL CENTER
# ═══════════════════════════════════════════════
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
        </div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("📋 Total casos", len(df_cc))
    col2.metric("🆕 Casos hoy", len(cc_hoy))
    if "Ciudad" in df_cc.columns:
        col3.metric("🏙 Ciudades", df_cc["Ciudad"].nunique())

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 🔖 Casos por tipo de problema")
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
        st.markdown("#### 📈 Tendencia por semana")
        df_cc["semana"] = df_cc["_submission_time"].dt.to_period("W").astype(str)
        tendencia = df_cc.groupby("semana").size().reset_index(name="casos")
        fig3 = px.line(tendencia, x="semana", y="casos", markers=True,
                      color_discrete_sequence=["#1f4e9c"])
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()

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
