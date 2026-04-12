import requests
import time
import pandas as pd
import io
import os
import shutil
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
TOKEN = "b3c668ef9eb542be03840192e32c7a36e4ce72cd"  # Reemplaza con tu token de KoboToolbox

FORM_URLS = {
    "datos_dudas_callcenter.xlsx": "https://kobo.savethechildren.net/api/v2/assets/amGYbSxV8fX2sy7xTJut5F/export-settings/esN2rhGwBJy2aD9JF3EdZts/data.xlsx",
    "salud_kobo.xlsx": "https://kobo.savethechildren.net/api/v2/assets/a8KGhCwvMnZHzxETUac67N/export-settings/esBKTZcgZXrCcECdPWuR5k6/data.xlsx",
}

ONEDRIVE_FOLDER = r"C:\Users\Pc\OneDrive - Save the Children International\Israel CVA & Infraestructura 2025\CVA\monitoreo de kobos para CVA"

HEADERS = {"Authorization": f"Token {TOKEN}"}

# Columnas PII por formulario — visible solo para rol operator/admin en el dashboard
PII_SALUD = [
    "Nombre del paciente",
    "Número de teléfono con whatsapp (en caso de no contar con whatsapp, proporcionar de cualquier manera un número de contacto)",
    "Por favor, proporcione un número de contacto alternativo",
]

PII_CALLCENTER = [
    "Nombre_de_la_persona_que_llama",
    "N_mero_telef_nico_de_quien_llama",
]

# ─────────────────────────────────────────────
# CIFRADO
# ─────────────────────────────────────────────
def get_fernet():
    """Carga la clave de cifrado desde variable de entorno."""
    clave = os.environ.get("ENCRYPTION_KEY")
    if not clave:
        raise ValueError("❌ Variable de entorno ENCRYPTION_KEY no encontrada.")
    return Fernet(clave.encode())


def cifrar_y_guardar(df: pd.DataFrame, nombre_archivo: str):
    """Convierte el dataframe a bytes, lo cifra y guarda como .enc en OneDrive."""
    f = get_fernet()
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    datos_cifrados = f.encrypt(buffer.getvalue())

    nombre_enc = nombre_archivo.replace(".xlsx", ".enc")
    ruta_enc = os.path.join(ONEDRIVE_FOLDER, nombre_enc)

    with open(ruta_enc, "wb") as archivo:
        archivo.write(datos_cifrados)

    print(f"🔐 Archivo cifrado guardado: {nombre_enc}")

    # ── NUEVO: copiar .enc al repo y subir a GitHub ──
    ruta_repo = os.path.join(r"C:\Users\Pc\Desktop\sabad", nombre_enc)
    import shutil
    shutil.copy(ruta_enc, ruta_repo)
    
    os.chdir(r"C:\Users\Pc\Desktop\sabad")
    os.system(f'git add {nombre_enc}')
    os.system('git commit -m "Actualización datos cifrados"')
    os.system('git push origin master')
    print(f"🚀 {nombre_enc} subido a GitHub")


# ─────────────────────────────────────────────
# LÓGICA ORIGINAL (sin cambios en la descarga)
# ─────────────────────────────────────────────
def eliminar_archivo(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"✅ Archivo eliminado: {file_path}")
        else:
            print(f"⚠️ No encontrado para eliminar: {file_path}")
    except PermissionError:
        try:
            temp_path = file_path + ".bak"
            shutil.move(file_path, temp_path)
            os.remove(temp_path)
            print(f"✅ Archivo movido y eliminado: {file_path}")
        except Exception as e:
            print(f"❌ No se pudo eliminar {file_path}. Error: {e}")


def actualizar_formulario(filename, url):
    file_path = os.path.join(ONEDRIVE_FOLDER, filename)
    print(f"🔄 Descargando {filename} desde KoboToolbox...")

    try:
        response = requests.get(url, headers=HEADERS, timeout=60)

        if response.status_code == 200:
            df = pd.read_excel(io.BytesIO(response.content))

            if df.empty:
                print(f"⚠️ El archivo descargado está vacío. No se actualizará {filename}.")
                return

            # Guardar Excel original en OneDrive (como antes)
            eliminar_archivo(file_path)
            df.to_excel(file_path, index=False)
            print(f"✅ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {filename} actualizado en OneDrive.")

            # ── NUEVO: cifrar y guardar versión para el dashboard ──
            cifrar_y_guardar(df, filename)

        else:
            print(f"❌ Error {response.status_code} al descargar {filename}: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error al conectar con KoboToolbox para {filename}: {e}")


# ─────────────────────────────────────────────
# LOOP PRINCIPAL (igual que antes)
# ─────────────────────────────────────────────
def ejecutar_actualizaciones():
    horarios = ["08:30", "09:10", "10:00", "11:35", "12:00",
                "12:50", "13:30", "14:10", "15:45", "16:45", "17:35"]
    ultima_actualizacion = None
    eliminaciones_realizadas = set()

    while True:
        ahora = datetime.now()
        hora_str = ahora.strftime("%H:%M")
        print(f"🕒 Hora actual: {hora_str}", end="\r", flush=True)

        for horario in horarios:
            hora_programada = datetime.strptime(horario, "%H:%M")
            hora_eliminacion = (hora_programada - timedelta(minutes=5)).strftime("%H:%M")

            if hora_str == hora_eliminacion and horario not in eliminaciones_realizadas:
                print(f"\n🗑 Eliminando archivos 5 min antes de actualización ({horario})...")
                for archivo in FORM_URLS.keys():
                    eliminar_archivo(os.path.join(ONEDRIVE_FOLDER, archivo))
                eliminaciones_realizadas.add(horario)

        if hora_str in horarios and hora_str != ultima_actualizacion:
            print(f"\n\n⏰ ¡Hora de actualización! ({hora_str})")
            for filename, url in FORM_URLS.items():
                actualizar_formulario(filename, url)
            ultima_actualizacion = hora_str
            eliminaciones_realizadas.discard(hora_str)
            print("\n✅ Proceso completado. Volviendo al modo de espera...\n")

        time.sleep(30)


if __name__ == "__main__":
    # Para generar la clave por primera vez, ejecuta esto UNA sola vez:
    # from cryptography.fernet import Fernet
    # print(Fernet.generate_key().decode())
    # Luego guarda esa clave como variable de entorno ENCRYPTION_KEY
    ejecutar_actualizaciones()
