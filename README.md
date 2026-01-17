# Proyecto de Agentes con LangChain y DeepSeek

Este proyecto implementa un sistema de agentes inteligentes utilizando LangChain y la API de DeepSeek.

## Estructura del Proyecto

```
.
├── src/                    # Código fuente principal
├── agents/                 # Definición de agentes
├── tools/                  # Herramientas disponibles para los agentes
├── prompts/                # Plantillas de prompts
├── config/                 # Configuración de la aplicación
├── examples/               # Ejemplos de uso
├── tests/                  # Pruebas unitarias
├── requirements.txt        # Dependencias del proyecto
├── .env.example            # Archivo de ejemplo para variables de entorno
└── README.md              # Este archivo
```

## Instalación

1. Crea un ambiente virtual:
```bash
python -m venv env
source env/bin/activate  # En Windows: env\Scripts\activate
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Configura las variables de entorno:
```bash
cp .env.example .env
# Edita .env y agrega tu API key de DeepSeek
```

## Uso

### Ejecutar un agente simple

```python
from src.agent import create_deepseek_agent

agent = create_deepseek_agent()
response = agent.run("Tu pregunta aquí")
print(response)
```

## Configuración

Las configuraciones se manejan mediante:
- Variables de entorno (`.env`)
- Archivos de configuración en `config/`

## API DeepSeek

Para usar DeepSeek, necesitas:
1. Una API key de [DeepSeek](https://www.deepseek.com)
2. Agregar la API key a la variable de entorno `DEEPSEEK_API_KEY`

## Desarrollo

Para ejecutar los tests:
```bash
pytest tests/
```

## Licencia

MIT
