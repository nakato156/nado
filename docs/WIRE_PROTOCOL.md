# Wire Protocol - NADO

## Visión General

El wire protocol define cómo los agentes se comunican entre sí usando mensajes JSON estructurados.

## Schemas

### 1. Proposal (Musician → Researcher)

```json
{
  "schema_version": "proposal.v1",
  "window": {
    "bar_index": 0,
    "start_step": 0,
    "end_step": 16
  },
  "agent": {
    "name": "Musician Agent",
    "version": "1.0.0"
  },
  "variants": [
    {
      "id": "v1",
      "tags": ["melodic", "energetic"],
      "events": [
        {
          "type": "note",
          "track": "pulse1",
          "pitch": 60,
          "velocity": 100,
          "start_step": 0,
          "dur_steps": 4
        }
      ]
    }
  ]
}
```

### 2. Critic Report (Researcher → Orchestrator)

```json
{
  "schema_version": "critic_report.v1",
  "window": {
    "bar_index": 0,
    "start_step": 0,
    "end_step": 16
  },
  "agent": {
    "name": "Researcher Agent",
    "version": "1.0.0"
  },
  "rankings": [
    {
      "variant_id": "v1",
      "score": 85.5,
      "passed_hard_constraints": true,
      "reasons": ["Buena repetición de motivos", "Alta variedad rítmica"]
    }
  ],
  "metrics": {
    "density": 0.5,
    "repetition": 0.3,
    "rhythm_entropy": 0.8,
    "range_violations": 0,
    "polyphony_violations": 0,
    "style_compliance": 0.95
  },
  "hints": [
    {
      "priority": "low",
      "message": "Considerar añadir más eventos",
      "target": {
        "track": "pulse2",
        "bar_index": 0
      }
    }
  ]
}
```

### 3. Constraints (PM → Todos)

```json
{
  "schema_version": "constraints.v1",
  "hard": {
    "required_tracks": ["pulse1", "triangle", "noise"],
    "monophonic_tracks": ["pulse1", "pulse2", "triangle", "noise"],
    "max_events_per_bar": 32,
    "pitch_ranges": {
      "pulse1": {"min": 48, "max": 96},
      "triangle": {"min": 24, "max": 60}
    },
    "velocity_levels": [64, 100, 127],
    "forbid_overflow": true
  },
  "soft": {
    "target_density_per_bar": 8.0,
    "target_repetition": 0.3,
    "prefer_step_grid": 4,
    "style_tags": ["8bit", "nes", "chiptune"]
  }
}
```

### 4. Score (Output Final)

```json
{
  "schema_version": "score.v1",
  "metadata": {
    "title": "Adventure Theme",
    "tempo_bpm": 140,
    "time_signature": "4/4",
    "key": "C",
    "length_bars": 8
  },
  "resolution": {
    "steps_per_beat": 4,
    "beats_per_bar": 4
  },
  "tracks": [
    {"id": "pulse1", "role": "melody", "monophonic": true, "program": 80},
    {"id": "triangle", "role": "bass", "monophonic": true, "program": 38}
  ],
  "events": [
    {
      "type": "note",
      "track": "pulse1",
      "pitch": 60,
      "velocity": 100,
      "start_step": 0,
      "dur_steps": 4
    }
  ]
}
```

## Flujo de Datos

```
┌─────────────┐     proposal.v1      ┌─────────────────┐
│   Musician  │ ─────────────────────▶│   Researcher    │
│    Agent    │                       │     Agent       │
└─────────────┘                       └────────┬────────┘
                                               │
                                    critic_report.v1
                                               │
                                               ▼
┌─────────────┐     constraints.v1   ┌─────────────────┐
│     PM      │ ◀────────────────────│   Orchestrator  │
│    Agent    │ ─────────────────────▶│                 │
└─────────────┘   validation_result   └────────┬────────┘
                                               │
                                           score.v1
                                               │
                                               ▼
                                        ┌──────────────┐
                                        │  Score Final │
                                        └──────────────┘
```

## Validación

Todos los mensajes deben validarse contra sus schemas JSON antes de procesarse.
Los schemas están en `/schemas/`.

## Extensibilidad

Para agregar un nuevo agente:

1. Definir su schema de output si es necesario
2. Implementar la interfaz `BaseAgent`
3. Registrarlo en el Orchestrator
4. El wire protocol se mantiene compatible
