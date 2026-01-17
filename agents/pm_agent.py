"""
PM Agent - Product Constraints & Acceptance
Responsable de definir constraints y validar scores
"""
import sys
sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

from typing import List, Optional
from agents.base_agent import BaseAgent
from models.score import ScoreV1, NoteEvent
from models.constraints import (
    ConstraintsV1, 
    ConstraintViolation, 
    ValidationResult,
)
from models.proposal import ProposalV1, Variant
from src.agent import create_deepseek_llm


class PMAgent(BaseAgent):
    """
    PM Agent - Product Manager
    
    Responsabilidades:
    - Definir constraints verificables (hard/soft)
    - Validar propuestas contra constraints
    - Rechazar/aprobar commits de ventanas
    - Generar tickets de corrección
    """
    
    def __init__(
        self, 
        constraints: Optional[ConstraintsV1] = None,
        use_llm: bool = False,
    ):
        super().__init__(
            name="PM Agent",
            description="Product Constraints & Acceptance Agent"
        )
        self.constraints = constraints or ConstraintsV1.default_8bit()
        self.llm = create_deepseek_llm() if use_llm else None
    
    def run(self, query: str) -> str:
        """Ejecuta consulta general usando LLM si está disponible"""
        if self.llm:
            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=query),
            ]
            response = self.llm.invoke(messages)
            return response.content
        return "LLM no configurado para PM Agent"
    
    def _get_system_prompt(self) -> str:
        return """Eres el PM Agent de un sistema de composición musical 8-bit.
Tu rol es definir y validar constraints de producto.
Respondes sobre reglas de validación, límites de pistas, rangos de pitch, etc.
Constraints actuales:
- Tracks requeridos: pulse1, triangle, noise
- Todos los tracks son monofónicos
- Max eventos por compás: 32
- Velocity levels: 64, 100, 127 (3 niveles como NES)
"""
    
    def validate_score(self, score: ScoreV1) -> ValidationResult:
        """
        Valida un score completo contra los constraints
        
        Args:
            score: Score a validar
            
        Returns:
            ValidationResult con violaciones encontradas
        """
        violations: List[ConstraintViolation] = []
        
        # Validar tracks requeridos
        track_ids = {t.id for t in score.tracks}
        for req_track in self.constraints.hard.required_tracks:
            if req_track not in track_ids:
                violations.append(ConstraintViolation(
                    constraint_type="hard",
                    rule="required_tracks",
                    message=f"Track requerido '{req_track}' no encontrado",
                    track=req_track,
                ))
        
        # Validar eventos
        violations.extend(self._validate_events(score))
        
        is_valid = len([v for v in violations if v.constraint_type == "hard"]) == 0
        
        return ValidationResult(is_valid=is_valid, violations=violations)
    
    def validate_variant(
        self, 
        variant: Variant, 
        window_start: int,
        window_end: int,
    ) -> ValidationResult:
        """
        Valida una variante de propuesta
        
        Args:
            variant: Variante a validar
            window_start: Step de inicio de la ventana
            window_end: Step de fin de la ventana
            
        Returns:
            ValidationResult
        """
        violations: List[ConstraintViolation] = []
        
        # Verificar que eventos están dentro de la ventana
        for i, event in enumerate(variant.events):
            if event.start_step < window_start or event.start_step >= window_end:
                violations.append(ConstraintViolation(
                    constraint_type="hard",
                    rule="window_bounds",
                    message=f"Evento fuera de ventana [{window_start}, {window_end})",
                    event_index=i,
                ))
            
            # Validar pitch range
            if event.track in self.constraints.hard.pitch_ranges:
                pr = self.constraints.hard.pitch_ranges[event.track]
                if event.pitch < pr.min or event.pitch > pr.max:
                    violations.append(ConstraintViolation(
                        constraint_type="hard",
                        rule="pitch_range",
                        message=f"Pitch {event.pitch} fuera de rango [{pr.min}, {pr.max}] para {event.track}",
                        track=event.track,
                        event_index=i,
                    ))
            
            # Validar velocity levels
            if event.velocity not in self.constraints.hard.velocity_levels:
                # Soft violation - se puede cuantizar
                violations.append(ConstraintViolation(
                    constraint_type="soft",
                    rule="velocity_levels",
                    message=f"Velocity {event.velocity} no es un nivel válido",
                    event_index=i,
                ))
        
        # Validar monofonía
        violations.extend(self._check_polyphony(variant.events))
        
        is_valid = len([v for v in violations if v.constraint_type == "hard"]) == 0
        
        return ValidationResult(is_valid=is_valid, violations=violations)
    
    def _validate_events(self, score: ScoreV1) -> List[ConstraintViolation]:
        """Valida eventos individuales"""
        violations = []
        steps_per_bar = score.resolution.steps_per_bar
        
        # Agrupar eventos por compás
        events_per_bar: dict = {}
        for event in score.events:
            bar_idx = event.start_step // steps_per_bar
            if bar_idx not in events_per_bar:
                events_per_bar[bar_idx] = []
            events_per_bar[bar_idx].append(event)
        
        # Validar max eventos por compás
        for bar_idx, events in events_per_bar.items():
            if len(events) > self.constraints.hard.max_events_per_bar:
                violations.append(ConstraintViolation(
                    constraint_type="hard",
                    rule="max_events_per_bar",
                    message=f"Compás {bar_idx} tiene {len(events)} eventos (max: {self.constraints.hard.max_events_per_bar})",
                    bar_index=bar_idx,
                ))
        
        # Validar pitch ranges y monofonía
        violations.extend(self._check_polyphony(score.events))
        
        for i, event in enumerate(score.events):
            if event.track in self.constraints.hard.pitch_ranges:
                pr = self.constraints.hard.pitch_ranges[event.track]
                if event.pitch < pr.min or event.pitch > pr.max:
                    violations.append(ConstraintViolation(
                        constraint_type="hard",
                        rule="pitch_range",
                        message=f"Pitch {event.pitch} fuera de rango para {event.track}",
                        track=event.track,
                        event_index=i,
                    ))
        
        return violations
    
    def _check_polyphony(self, events: List[NoteEvent]) -> List[ConstraintViolation]:
        """Verifica violaciones de monofonía"""
        violations = []
        
        # Agrupar por track
        by_track: dict = {}
        for event in events:
            if event.track not in by_track:
                by_track[event.track] = []
            by_track[event.track].append(event)
        
        # Verificar overlaps en tracks monofónicos
        for track_id in self.constraints.hard.monophonic_tracks:
            if track_id not in by_track:
                continue
            
            track_events = sorted(by_track[track_id], key=lambda e: e.start_step)
            
            for i in range(len(track_events) - 1):
                current = track_events[i]
                next_event = track_events[i + 1]
                
                if current.end_step > next_event.start_step:
                    violations.append(ConstraintViolation(
                        constraint_type="hard",
                        rule="monophonic",
                        message=f"Overlap detectado en track monofónico {track_id}",
                        track=track_id,
                    ))
        
        return violations
    
    def quantize_velocity(self, velocity: int) -> int:
        """Cuantiza velocity al nivel más cercano permitido"""
        levels = self.constraints.hard.velocity_levels
        return min(levels, key=lambda x: abs(x - velocity))
    
    def get_constraints_summary(self) -> str:
        """Genera un resumen legible de los constraints"""
        c = self.constraints
        lines = [
            "=== Constraints Activos ===",
            f"Tracks requeridos: {', '.join(c.hard.required_tracks)}",
            f"Tracks monofónicos: {', '.join(c.hard.monophonic_tracks)}",
            f"Max eventos/compás: {c.hard.max_events_per_bar}",
            f"Niveles velocity: {c.hard.velocity_levels}",
            "",
            "Pitch ranges:",
        ]
        for track, pr in c.hard.pitch_ranges.items():
            lines.append(f"  {track}: {pr.min}-{pr.max}")
        
        lines.extend([
            "",
            "Soft constraints:",
            f"  Densidad objetivo: {c.soft.target_density_per_bar}/compás",
            f"  Repetición objetivo: {c.soft.target_repetition:.0%}",
            f"  Grid preferido: {c.soft.prefer_step_grid} steps",
            f"  Tags estilo: {', '.join(c.soft.style_tags)}",
        ])
        
        return "\n".join(lines)
