"""
Configuración de la aplicación
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# Configuración del modelo
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Validar configuración
if not DEEPSEEK_API_KEY:
    raise ValueError(
        "DEEPSEEK_API_KEY no está configurada. "
        "Por favor, configúrala en el archivo .env"
    )
