

## 0) Principios de diseño (para que escale)

* **Los agentes no renderizan audio.** Solo producen/consumen `score.v1` (eventos en steps).
* **Un solo “Orchestrator/Conductor” integra.** Los agentes proponen; el orchestrator decide.
* **Separación estricta:**

  * *Producto* = constraints + aceptación
  * *Creativo* = contenido musical
  * *I+D* = evaluadores + optimización del loop

---

## 1) Componentes del sistema

### 1.1 Orchestrator (Conductor) — componente central (no humano)

**Responsabilidad:** coordinar iteraciones, evitar conflictos, aplicar passes y validar.

**Entradas**

* `ScoreV1` parcial o vacío
* `SectionPlan` (si existe)
* Propuestas de agentes `List[NoteEvent]` por ventana

**Salidas**

* `ScoreV1` actualizado y validado

**Garantías**

* Monofonía por track (si aplica)
* No overlaps / no eventos fuera de rango
* Cuantización consistente
* Logging de métricas por compás/iteración

---

## 2) Agentes (definición clara)

### 2.1 PM Agent — “Product Constraints & Acceptance”

**Rol:** traducir objetivos de producto a constraints verificables, y bloquear salidas inválidas.

**Responsabilidades**

* Define el **Definition of Done** en términos del contrato:

  * duración: `metadata.length_bars`
  * BPM: `metadata.tempo_bpm`
  * estructura: intro/loop/outro (si aplica)
  * pistas requeridas (mínimo): `pulse1`, `triangle`, `noise` (y opcional `pulse2`)
  * límites: densidad máxima por barra, rango de pitches por rol, etc.
* Ejecuta el **validador** (JSON-Schema + reglas adicionales).
* Genera “tickets” de corrección: qué regla se violó y en qué ventana.

**Entradas**

* `ScoreV1`, métricas del critic, configuración del producto (YAML/JSON)

**Salidas**

* `ConstraintSpec` (config) y/o `ConstraintViolations`
* No necesariamente emite notas. Puede, opcionalmente, emitir “meta” (en v2).

**KPIs**

* % scores que pasan validación sin intervención humana
* Estabilidad: variación de métricas vs objetivo (tempo/estructura/densidad)

**Autoridad**

* Puede **rechazar** commits de una ventana si violan reglas duras (“hard constraints”).

---

### 2.2 Musician Agent — “Composer / Motif & Arrangement”

**Rol:** generar contenido musical coherente y estilísticamente consistente.

**Responsabilidades**

* Propone notas para tracks musicales según rol:

  * `pulse1`: melodía (monofónica)
  * `pulse2`: armonía/arpegios (monofónica, opcional)
  * `triangle`: bajo (monofónico)
  * `noise`: batería (monofónico por diseño)
* Mantiene continuidad: motivos, cadencias, energía por sección.
* Respeta constraints del PM y recomendaciones del critic.

**Entradas**

* `WindowContext` (bar_index, start/end_step, key, tempo)
* Estado del score previo (para continuidad)
* “StylePreset” (8-bit strict, density, swing=0/…)
* Feedback del critic (qué mejorar en la siguiente iteración)

**Salidas**

* `List[NoteEvent]` por ventana

**KPIs**

* Coherencia (repetición controlada)
* Cumplimiento de constraints sin correcciones
* “Musicality score” (según evaluador + feedback humano)

**Autoridad**

* Es la **fuente principal** de contenido; no hace merge final.

---

### 2.3 Researcher Agent — “Evaluator / Critic & Optimization”

**Rol:** medir, puntuar y dirigir la mejora iterativa; prepara el camino a aprendizaje automático.

**Responsabilidades**

* Implementa un **critic** que calcula métricas por ventana y globales:

  * densidad de eventos (por track y total)
  * repetición/motivos (n-grams de pitch/intervalos)
  * consonancia aproximada (pitch-class vs key)
  * estabilidad rítmica (entropía de onsets)
  * colisiones/overlaps (aunque el orchestrator lo arregle, se mide)
  * “8-bit compliance” (polifonía, buckets de velocity, etc.)
* Sugiere acciones: “reduce densidad en bar 5”, “más repetición en hook”.
* (Escalable) Implementa búsqueda: beam search / MCTS / bandits / RL.
* Diseña dataset interno: (score, métricas, rating humano) para entrenar un reward model.

**Entradas**

* Propuestas por ventana + score parcial
* Historial (scores anteriores y métricas)
* Ratings humanos (del músico o QA)

**Salidas**

* `MetricsReport` + `CriticScore`
* `ImprovementHints` (texto estructurado o JSON)
* En fases futuras: “re-rank” de propuestas alternativas

**KPIs**

* Correlación entre `CriticScore` y rating humano
* Mejora iterativa: Δ score por iteración
* Robustez: baja varianza en outputs con mismos seeds

**Autoridad**

* No bloquea por reglas duras (eso es PM); su peso es en ranking/selección.

---

## 3) Flujo de trabajo por ventana (cómo interactúan)

Para cada compás (o bloque de 2 compases):

1. **PM Agent** publica constraints activos (hard/soft).
2. **Musician Agent** propone notas (una o varias variantes).
3. **Researcher/Critic** puntúa cada variante y sugiere ajustes.
4. **Orchestrator**:

   * selecciona (o combina) la mejor propuesta
   * aplica passes (monofonía, velocity buckets, etc.)
   * valida con reglas del PM
   * comitea la ventana al score global

Escala natural: agregas más agentes (drums, harmony, bass, arranger) sin romper el contrato.

---

## 4) División de autoridad (para evitar “agentes peleando”)

* **PM**: reglas duras (aceptación/rechazo), estructura, límites.
* **Músico**: contenido musical y estilo.
* **Researcher**: medición, ranking, optimización y aprendizaje.
* **Orchestrator**: merge final, passes, validación y logging.

Esto elimina loops caóticos y te permite crecer a 10+ agentes.

---

## 5) Entregables concretos por rol (para tu implementación)

* **PM**

  * `constraints.yaml` (DoD + límites)
  * `validate(score)->violations`
* **Músico**

  * `style_presets/8bit_strict.json`
  * `compose(window, context)->events`
* **Researcher**

  * `critic.py` (métricas + scoring)
  * `rerank(proposals)->best`
  * `telemetry.jsonl` (logging)

---

Si quieres, el siguiente paso lo dejo completamente cerrado con un **JSON contract adicional** para:

* `constraints.v1` (lo que define el PM)
* `critic_report.v1` (lo que emite el researcher)
* `proposal.v1` (lo que emite el músico por ventana con variantes)

Eso convierte el sistema en “API-driven” y listo para escalar a agentes adicionales.
