# Estructura del Proyecto de Agentes

## Descripción General

Proyecto base para crear agentes inteligentes utilizando **LangChain** y la API de **DeepSeek**.

## Árbol de Directorios

```
nado/
├── src/                          # Código fuente principal
│   ├── __init__.py
│   └── agent.py                 # Funciones para crear y gestionar agentes
│
├── agents/                       # Definición de agentes
│   ├── __init__.py
│   ├── base_agent.py            # Clase base abstracta para agentes
│   └── deepseek_agent.py        # Implementación específica para DeepSeek
│
├── tools/                        # Herramientas disponibles
│   ├── __init__.py
│   └── custom_tools.py          # Herramientas personalizadas
│
├── prompts/                      # Plantillas de prompts
│   ├── __init__.py
│   └── system_prompts.py        # Prompts del sistema
│
├── config/                       # Configuración
│   ├── __init__.py
│   └── settings.py              # Configuración centralizada
│
├── examples/                     # Ejemplos de uso
│   ├── __init__.py
│   └── basic_agent.py           # Ejemplo básico
│
├── tests/                        # Pruebas unitarias
│   ├── __init__.py
│   └── test_agent.py            # Pruebas del agente
│
├── main.py                       # Punto de entrada principal
├── requirements.txt              # Dependencias del proyecto
├── .env.example                  # Ejemplo de variables de entorno
├── .gitignore                    # Archivos a ignorar en git
└── README.md                     # Documentación general

```

## Descripción de Carpetas

### `src/`
Contiene el código core para crear agentes y manejar la comunicación con DeepSeek.

### `agents/`
Define diferentes tipos de agentes. `BaseAgent` es la clase abstracta, y `DeepseekAgent` es la implementación específica.

### `tools/`
Contiene herramientas que los agentes pueden utilizar para realizar tareas específicas.

### `prompts/`
Almacena las plantillas de prompts del sistema, útiles para configurar el comportamiento de los agentes.

### `config/`
Gestiona toda la configuración centralizada, incluyendo variables de entorno y parámetros de la API.

### `examples/`
Ejemplos prácticos de cómo usar los agentes.

### `tests/`
Pruebas unitarias para validar el funcionamiento.

## Archivo de Configuración (.env)

```env
# API Configuration
DEEPSEEK_API_KEY=tu_api_key_aqui
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# Model Configuration
MODEL_NAME=deepseek-chat
TEMPERATURE=0.7
MAX_TOKENS=2000

# Logging
LOG_LEVEL=INFO
```

## Próximos Pasos

1. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurar la API key**:
   - Copia `.env.example` a `.env`
   - Agrega tu API key de DeepSeek

3. **Ejecutar ejemplos**:
   ```bash
   python examples/basic_agent.py
   ```

4. **Ejecutar la aplicación principal**:
   ```bash
   python main.py
   ```

5. **Ejecutar pruebas**:
   ```bash
   python -m pytest tests/
   ```

## Extensiones Posibles

- Agregar más tipos de agentes especializados
- Implementar memoria persistente
- Conectar con bases de datos
- Crear un API REST
- Agregar interfaz gráfica
- Implementar logging avanzado
