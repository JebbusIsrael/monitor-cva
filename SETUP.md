# 🚀 Guía de instalación — Monitor CVA Save the Children México

## 1. Instalar dependencias

```bash
pip install streamlit streamlit-authenticator cryptography pandas plotly openpyxl pyyaml requests
```

---

## 2. Generar tu clave de cifrado (una sola vez)

Ejecuta esto en Python UNA sola vez y guarda el resultado:

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

Guarda esa clave — la necesitas en los pasos siguientes.

---

## 3. Configurar variable de entorno en tu PC (para el script)

**Windows:**
1. Busca "Variables de entorno" en el menú inicio
2. Nueva variable de usuario:
   - Nombre: `ENCRYPTION_KEY`
   - Valor: la clave generada en el paso 2

---

## 4. Generar contraseñas hasheadas para el dashboard

```python
import streamlit_authenticator as stauth
hashed = stauth.Hasher(['password_isra', 'password_operador', 'password_coordinador']).generate()
for h in hashed:
    print(h)
```

Copia cada hash y reemplaza los `$2b$12$HASH_AQUI` en `dashboard.py`

---

## 5. Configurar secrets en Streamlit Cloud

Crea el archivo `.streamlit/secrets.toml` localmente para pruebas:

```toml
ENCRYPTION_KEY = "tu_clave_fernet_aqui"
ONEDRIVE_FOLDER = "C:\\Users\\Pc\\OneDrive - Save the Children International\\Israel CVA & Infraestructura 2025\\CVA\\monitoreo de kobos para CVA"
```

En Streamlit Cloud: Settings → Secrets → pega el mismo contenido.

---

## 6. Subir a GitHub (repo privado)

```bash
git init
git add dashboard.py requirements.txt
git commit -m "Monitor CVA v1.0"
git remote add origin https://github.com/tu_usuario/monitor-cva-stc.git
git push -u origin main
```

**IMPORTANTE:** Nunca subas el archivo `.enc` ni `secrets.toml` al repo.
Agrega al `.gitignore`:
```
*.enc
.streamlit/secrets.toml
```

---

## 7. Desplegar en Streamlit Cloud

1. Ve a https://share.streamlit.io
2. Conecta tu cuenta de GitHub
3. Selecciona el repo y el archivo `dashboard.py`
4. En Settings → Secrets agrega tus variables
5. Deploy ✅

---

## Roles disponibles

| Usuario | Rol | Ve nombre/teléfono |
|---|---|---|
| isra_admin | admin | ✅ Sí |
| operador1 | operator | ✅ Sí |
| coordinador1 | viewer | ❌ No |

---

## Flujo completo

```
Tu PC corre script_kobo_actualizado.py
    → Descarga Excel de Kobo
    → Cifra con Fernet → guarda .enc en OneDrive
    → Streamlit lee .enc desde OneDrive
    → Descifra en memoria RAM
    → Muestra dashboard según rol del usuario
```
