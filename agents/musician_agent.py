"""
Musician Agent - Composer / Motif & Arrangement
Responsable de generar contenido musical coherente
"""
import sys
sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

import json
import random
from typing import List, Optional, Dict, Any
from agents.base_agent import BaseAgent
from models.score import ScoreV1, NoteEvent
from models.proposal import ProposalV1, Variant, Window, AgentInfo
from models.critic_report import Hint
from src.agent import create_deepseek_llm
from langchain_core.messages import HumanMessage, SystemMessage


# Escalas musicales comunes
SCALES = {
    "C": [0, 2, 4, 5, 7, 9, 11],  # C major
    "Cm": [0, 2, 3, 5, 7, 8, 10],  # C minor
    "C_penta": [0, 2, 4, 7, 9],  # C pentatonic
    "Cm_penta": [0, 3, 5, 7, 10],  # C minor pentatonic
}

# Patrones rítmicos de bajo típicos de 8-bit
BASS_PATTERNS = [
    [0, 4, 8, 12],  # Cada beat
    [0, 8],  # Cada 2 beats
    [0, 4, 6, 8, 12, 14],  # Sincopado
    [0, 2, 4, 6, 8, 10, 12, 14],  # Octavos
]

# Patrones de batería 8-bit
DRUM_PATTERNS = {
    "kick": [0, 8],  # Bombo
    "snare": [4, 12],  # Caja
    "hihat": [0, 2, 4, 6, 8, 10, 12, 14],  # Hi-hat
}


class MusicianAgent(BaseAgent):
    """
    Musician Agent - Compositor
    
    Responsabilidades:
    - Proponer notas para tracks musicales
    - Mantener continuidad (motivos, cadencias)
    - Respetar constraints del PM
    - Incorporar feedback del critic
    """
    
    VERSION = "1.0.0"
    
    def __init__(
        self,
        style: str = "8bit",
        use_llm: bool = True,
    ):
        super().__init__(
            name="Musician Agent",
            description="Composer / Motif & Arrangement Agent"
        )
        self.style = style
        self.llm = create_deepseek_llm() if use_llm else None
        self.context_memory: List[Dict[str, Any]] = []
    
    def run(self, query: str) -> str:
        """Ejecuta consulta general usando LLM"""
        if self.llm:
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=query),
            ]
            response = self.llm.invoke(messages)
            return response.content
        return "LLM no configurado para Musician Agent"
    
    def _get_system_prompt(self) -> str:
        return """Eres el Musician Agent de un sistema de composición musical 8-bit estilo NES.
Tu rol es generar contenido musical coherente y estilísticamente consistente.

Tracks disponibles:
- pulse1: Melodía principal (monofónico)
- pulse2: Armonía/arpegios (monofónico)  
- triangle: Bajo (monofónico)
- noise: Batería (monofónico)

Características del estilo 8-bit:
- Melodías pentatónicas o diatónicas simples
- Arpegios rápidos
- Líneas de bajo simples pero groovy
- Ritmos sincopados
- Solo 3 niveles de velocity (64, 100, 127)

Cuando generes música, piensa en juegos clásicos de NES como:
- Mega Man, Castlevania, Mario Bros, Zelda
"""
    
    def compose_window(
        self,
        score: ScoreV1,
        bar_index: int,
        hints: Optional[List[Hint]] = None,
        num_variants: int = 3,
    ) -> ProposalV1:
        """
        Compone propuestas para una ventana (compás)
        
        Args:
            score: Score actual para contexto
            bar_index: Índice del compás a componer
            hints: Sugerencias del critic
            num_variants: Número de variantes a generar
            
        Returns:
            ProposalV1 con variantes
        """
        steps_per_bar = score.resolution.steps_per_bar
        start_step = bar_index * steps_per_bar
        end_step = start_step + steps_per_bar
        
        window = Window(
            bar_index=bar_index,
            start_step=start_step,
            end_step=end_step,
        )
        
        # Obtener contexto del compás anterior
        prev_events = []
        if bar_index > 0:
            prev_start = (bar_index - 1) * steps_per_bar
            prev_events = score.get_events_in_window(prev_start, start_step)
        
        variants = []
        
        if self.llm:
            # Usar LLM para generar variantes más creativas
            variants = self._compose_with_llm(
                score, window, prev_events, hints, num_variants
            )
        
        # Si LLM falló o no hay suficientes variantes, generar algorítmicamente
        while len(variants) < num_variants:
            variant = self._compose_algorithmic(
                score, window, prev_events, len(variants)
            )
            variants.append(variant)
        
        return ProposalV1(
            window=window,
            agent=AgentInfo(name=self.name, version=self.VERSION),
            variants=variants,
        )
    
    def _compose_with_llm(
        self,
        score: ScoreV1,
        window: Window,
        prev_events: List[NoteEvent],
        hints: Optional[List[Hint]],
        num_variants: int,
    ) -> List[Variant]:
        """Genera variantes usando el LLM"""
        variants = []
        
        # Construir contexto para el LLM
        context = self._build_composition_context(score, window, prev_events, hints)
        
        prompt = f"""Genera {num_variants} variantes musicales para el compás {window.bar_index}.

{context}

Responde SOLO con un JSON válido con esta estructura:
{{
  "variants": [
    {{
      "id": "v1",
      "tags": ["melodic", "energetic"],
      "events": [
        {{"track": "pulse1", "pitch": 60, "velocity": 100, "start_step": 0, "dur_steps": 4}},
        ...
      ]
    }}
  ]
}}

Reglas:
- start_step debe estar entre {window.start_step} y {window.end_step - 1}
- pitch para pulse1/pulse2: 48-96, triangle: 24-60
- velocity: solo 64, 100, o 127
- dur_steps mínimo: 1
- Cada track es monofónico (sin overlaps)
"""

        try:
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=prompt),
            ]
            response = self.llm.invoke(messages)
            
            # Extraer JSON de la respuesta
            content = response.content
            # Buscar el JSON en la respuesta
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                data = json.loads(json_str)
                
                for v_data in data.get("variants", []):
                    events = []
                    for e in v_data.get("events", []):
                        events.append(NoteEvent(
                            type="note",
                            track=e["track"],
                            pitch=e["pitch"],
                            velocity=e["velocity"],
                            start_step=e["start_step"],
                            dur_steps=e["dur_steps"],
                        ))
                    
                    variants.append(Variant(
                        id=v_data.get("id", f"llm_v{len(variants)}"),
                        tags=v_data.get("tags", ["llm_generated"]),
                        events=events,
                    ))
        except Exception as e:
            print(f"Error al parsear respuesta LLM: {e}")
        
        return variants
    
    def _build_composition_context(
        self,
        score: ScoreV1,
        window: Window,
        prev_events: List[NoteEvent],
        hints: Optional[List[Hint]],
    ) -> str:
        """Construye contexto para el LLM"""
        lines = [
            f"Título: {score.metadata.title}",
            f"Tempo: {score.metadata.tempo_bpm} BPM",
            f"Key: {score.metadata.key}",
            f"Time Signature: {score.metadata.time_signature}",
            f"Steps por compás: {score.resolution.steps_per_bar}",
            "",
        ]
        
        if prev_events:
            lines.append("Eventos del compás anterior (para continuidad):")
            for e in prev_events[:8]:  # Limitar para no saturar
                lines.append(f"  {e.track}: pitch={e.pitch}, step={e.start_step}")
            lines.append("")
        
        if hints:
            lines.append("Sugerencias del crítico:")
            for h in hints:
                lines.append(f"  [{h.priority}] {h.message}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _compose_algorithmic(
        self,
        score: ScoreV1,
        window: Window,
        prev_events: List[NoteEvent],
        variant_index: int,
    ) -> Variant:
        """Genera una variante algorítmicamente"""
        events = []
        key = score.metadata.key
        
        # Determinar escala base
        scale = SCALES.get(key, SCALES.get("C_penta", [0, 2, 4, 7, 9]))
        
        # Generar melodía (pulse1)
        events.extend(self._generate_melody(
            window, scale, variant_index
        ))
        
        # Generar bajo (triangle)
        events.extend(self._generate_bass(
            window, scale, variant_index
        ))
        
        # Generar batería (noise)
        events.extend(self._generate_drums(
            window, variant_index
        ))
        
        tags = ["algorithmic", f"variant_{variant_index}"]
        if variant_index == 0:
            tags.append("conservative")
        elif variant_index == 1:
            tags.append("melodic")
        else:
            tags.append("experimental")
        
        return Variant(
            id=f"algo_v{variant_index}",
            tags=tags,
            events=events,
        )
    
    def _generate_melody(
        self,
        window: Window,
        scale: List[int],
        variant_index: int,
    ) -> List[NoteEvent]:
        """Genera línea melódica"""
        events = []
        base_octave = 60  # C4
        
        # Diferentes densidades según variante
        if variant_index == 0:
            steps = [0, 4, 8, 12]  # Negras
        elif variant_index == 1:
            steps = [0, 2, 4, 6, 8, 10, 12, 14]  # Octavos
        else:
            steps = [0, 3, 6, 8, 11, 14]  # Sincopado
        
        for rel_step in steps:
            step = window.start_step + rel_step
            if step >= window.end_step:
                break
            
            # Elegir nota de la escala
            degree = random.choice(scale)
            pitch = base_octave + degree + random.choice([0, 12])  # Octava aleatoria
            
            # Asegurar rango válido
            pitch = max(48, min(96, pitch))
            
            # Calcular duración (no exceder ventana)
            dur = min(4, window.end_step - step)
            
            events.append(NoteEvent(
                track="pulse1",
                pitch=pitch,
                velocity=random.choice([64, 100, 127]),
                start_step=step,
                dur_steps=dur,
            ))
        
        return events
    
    def _generate_bass(
        self,
        window: Window,
        scale: List[int],
        variant_index: int,
    ) -> List[NoteEvent]:
        """Genera línea de bajo"""
        events = []
        base_octave = 36  # C2
        
        pattern = BASS_PATTERNS[variant_index % len(BASS_PATTERNS)]
        
        for rel_step in pattern:
            step = window.start_step + rel_step
            if step >= window.end_step:
                break
            
            # Bajo típicamente usa raíz y quinta
            degree = random.choice([scale[0], scale[4] if len(scale) > 4 else scale[0]])
            pitch = base_octave + degree
            pitch = max(24, min(60, pitch))
            
            dur = min(4, window.end_step - step)
            
            events.append(NoteEvent(
                track="triangle",
                pitch=pitch,
                velocity=100,
                start_step=step,
                dur_steps=dur,
            ))
        
        return events
    
    def _generate_drums(
        self,
        window: Window,
        variant_index: int,
    ) -> List[NoteEvent]:
        """Genera patrón de batería"""
        events = []
        
        # En 8-bit, el noise channel usa pitch para diferentes sonidos
        kick_pitch = 36
        snare_pitch = 38
        hihat_pitch = 42
        
        # Kick
        for rel_step in DRUM_PATTERNS["kick"]:
            step = window.start_step + rel_step
            if step < window.end_step:
                events.append(NoteEvent(
                    track="noise",
                    pitch=kick_pitch,
                    velocity=127,
                    start_step=step,
                    dur_steps=2,
                ))
        
        # Snare
        for rel_step in DRUM_PATTERNS["snare"]:
            step = window.start_step + rel_step
            if step < window.end_step:
                events.append(NoteEvent(
                    track="noise",
                    pitch=snare_pitch,
                    velocity=100,
                    start_step=step,
                    dur_steps=2,
                ))
        
        # Hi-hat (solo en algunas variantes)
        if variant_index > 0:
            for rel_step in DRUM_PATTERNS["hihat"][::2]:  # Solo algunos
                step = window.start_step + rel_step
                if step < window.end_step:
                    events.append(NoteEvent(
                        track="noise",
                        pitch=hihat_pitch,
                        velocity=64,
                        start_step=step,
                        dur_steps=1,
                    ))
        
        # Filtrar overlaps (noise es monofónico)
        events = self._remove_overlaps(events)
        
        return events
    
    def _remove_overlaps(self, events: List[NoteEvent]) -> List[NoteEvent]:
        """Remueve overlaps manteniendo el primer evento"""
        if not events:
            return events
        
        events = sorted(events, key=lambda e: (e.start_step, -e.velocity))
        result = [events[0]]
        
        for event in events[1:]:
            last = result[-1]
            if event.start_step >= last.end_step:
                result.append(event)
        
        return result
