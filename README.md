# NADO - Sistema de Composición Musical 8-bit con Agentes

Sistema multi-agente para composición de música estilo 8-bit/chiptune usando LangChain y DeepSeek.

## 🎮 Características

- **Arquitectura multi-agente**: PM, Musician, Researcher y Orchestrator
- **Wire Protocol**: Comunicación estructurada via JSON schemas
- **Estilo 8-bit**: Emula restricciones de consolas NES/GameBoy
- **Validación automática**: Constraints duros y suaves
- **Extensible**: Fácil agregar nuevos agentes y estilos

## 📁 Estructura del Proyecto

```
nado/
├── agents/                   # Implementación de agentes
│   ├── base_agent.py        # Clase base abstracta
│   ├── pm_agent.py          # Product Manager - Constraints
│   ├── musician_agent.py    # Compositor - Genera música
│   ├── researcher_agent.py  # Crítico - Evalúa y rankea
│   └── orchestrator.py      # Conductor - Coordina todo
│
├── models/                   # Modelos Pydantic
│   ├── score.py             # Score v1
│   ├── proposal.py          # Proposals del Musician
│   ├── critic_report.py     # Reports del Researcher
│   └── constraints.py       # Constraints del PM
│
├── schemas/                  # JSON Schemas
│   ├── score.schema.v1.json
│   ├── proposal.schema.v1.json
│   ├── critic_report.schema.v1.json
│   └── constraints.schema.v1.json
│
├── presets/                  # Presets de estilo
│   ├── 8bit_nes_strict.json
│   ├── gameboy_classic.json
│   └── arcade_energetic.json
│
├── docs/                     # Documentación
│   ├── AGENTS.md            # Arquitectura de agentes
│   └── WIRE_PROTOCOL.md     # Protocolo de comunicación
│
├── examples/                 # Ejemplos de uso
│   ├── compose_8bit.py      # Composición completa
│   └── wire_protocol_demo.py # Demo del protocolo
│
├── src/                      # Código core
├── config/                   # Configuración
├── tests/                    # Tests
└── main.py                   # Punto de entrada
```

## 🚀 Instalación

```bash
# Crear entorno virtual
python -m venv env
source env/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar API key
cp .env.example .env
# Editar .env con tu DEEPSEEK_API_KEY
```

## 💻 Uso

### Composición rápida

```bash
python examples/compose_8bit.py
```

### Demo del Wire Protocol

```bash
python examples/wire_protocol_demo.py
```

### Composición interactiva
```bash
python main.py --title "Mi Tema 8-bit" --tempo 120 --key "C" --length 8
```

### Uso programático

```python
from agents.orchestrator import Orchestrator

# Crear orchestrator
orchestrator = Orchestrator(use_llm=True)

# Componer
score = orchestrator.compose(
    title="My 8-bit Theme",
    tempo_bpm=140,
    key="C",
    length_bars=8,
)

# Exportar
orchestrator.export_to_json("my_score.json")
```

## 🎵 Wire Protocol

El sistema usa un protocolo de mensajes JSON:

1. **Musician** envía `proposal.v1` (variantes por ventana)
2. **Researcher** devuelve `critic_report.v1` (ranking + hints)
3. **Orchestrator** elige, aplica passes
4. **PM** valida con `constraints.v1`
5. Resultado se integra al `score.v1`

Ver [docs/WIRE_PROTOCOL.md](docs/WIRE_PROTOCOL.md) para detalles.

## 🤖 Agentes

| Agente | Rol | Responsabilidad |
|--------|-----|-----------------|
| PM | Product Manager | Define constraints, valida, rechaza |
| Musician | Compositor | Genera contenido musical |
| Researcher | Crítico | Evalúa, puntúa, sugiere mejoras |
| Orchestrator | Conductor | Coordina, aplica passes, merge final |

Ver [docs/AGENTS.md](docs/AGENTS.md) para arquitectura completa.

## 📊 Presets Disponibles

- **8bit_nes_strict**: Estilo NES estricto (4 canales mono)
- **gameboy_classic**: Estilo Game Boy
- **arcade_energetic**: Arcade más libre

## 🔧 Configuración

Variables de entorno (`.env`):

```env
DEEPSEEK_API_KEY=tu_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
TEMPERATURE=0.7
```

## 📝 Licencia

MIT
