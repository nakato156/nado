"""
Orchestrator - Conductor Central
Coordina agentes, aplica passes y gestiona el score final
"""
import sys
sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from models.score import ScoreV1, NoteEvent
from models.proposal import ProposalV1, Variant
from models.critic_report import CriticReportV1, Hint
from models.constraints import ConstraintsV1, ValidationResult
from agents.pm_agent import PMAgent
from agents.musician_agent import MusicianAgent
from agents.researcher_agent import ResearcherAgent


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Orchestrator")


@dataclass
class IterationResult:
    """Resultado de una iteración por ventana"""
    bar_index: int
    selected_variant_id: str
    score_before_passes: float
    score_after_validation: float
    events_added: int
    hints: List[Hint]
    passed_validation: bool


@dataclass
class CompositionSession:
    """Sesión de composición completa"""
    score: ScoreV1
    iterations: List[IterationResult] = field(default_factory=list)
    total_events: int = 0
    validation_passes: int = 0
    validation_failures: int = 0


class Orchestrator:
    """
    Orchestrator - Conductor Central
    
    Responsabilidades:
    - Coordinar iteraciones entre agentes
    - Evitar conflictos entre propuestas
    - Aplicar passes (monofonía, velocity buckets)
    - Validar con PM antes de commit
    - Logging de métricas por iteración
    """
    
    def __init__(
        self,
        constraints: Optional[ConstraintsV1] = None,
        use_llm: bool = True,
    ):
        self.constraints = constraints or ConstraintsV1.default_8bit()
        
        # Inicializar agentes
        self.pm = PMAgent(constraints=self.constraints, use_llm=False)
        self.musician = MusicianAgent(style="8bit", use_llm=use_llm)
        self.researcher = ResearcherAgent(constraints=self.constraints, use_llm=False)
        
        self.session: Optional[CompositionSession] = None
        
        logger.info("Orchestrator inicializado")
        logger.info(f"Constraints: {self.constraints.soft.style_tags}")
    
    def compose(
        self,
        title: str = "Untitled 8-bit Track",
        tempo_bpm: int = 140,
        key: str = "C",
        length_bars: int = 8,
        num_variants: int = 3,
    ) -> ScoreV1:
        """
        Compone un score completo
        
        Args:
            title: Título del track
            tempo_bpm: Tempo en BPM
            key: Tonalidad
            length_bars: Longitud en compases
            num_variants: Variantes a generar por compás
            
        Returns:
            ScoreV1 completado
        """
        # Crear score vacío
        score = ScoreV1.create_empty(
            title=title,
            tempo_bpm=tempo_bpm,
            key=key,
            length_bars=length_bars,
        )
        
        self.session = CompositionSession(score=score)
        
        logger.info(f"Iniciando composición: {title}")
        logger.info(f"  Tempo: {tempo_bpm} BPM, Key: {key}, Bars: {length_bars}")
        
        # Iterar por cada compás
        hints: List[Hint] = []
        
        for bar_index in range(length_bars):
            result = self._compose_bar(bar_index, hints, num_variants)
            self.session.iterations.append(result)
            
            # Actualizar hints para siguiente iteración
            hints = result.hints
            
            logger.info(
                f"Bar {bar_index}: +{result.events_added} eventos, "
                f"score={result.score_after_validation:.1f}, "
                f"valid={result.passed_validation}"
            )
        
        # Resumen final
        self._log_session_summary()
        
        return self.session.score
    
    def _compose_bar(
        self,
        bar_index: int,
        prev_hints: List[Hint],
        num_variants: int,
    ) -> IterationResult:
        """Compone un solo compás"""
        score = self.session.score
        
        # 1. Musician genera propuestas
        proposal = self.musician.compose_window(
            score=score,
            bar_index=bar_index,
            hints=prev_hints,
            num_variants=num_variants,
        )
        
        logger.debug(f"  Musician generó {len(proposal.variants)} variantes")
        
        # 2. Researcher evalúa y rankea
        critic_report = self.researcher.evaluate_proposal(proposal, score)
        
        best_variant_id = critic_report.get_best_variant_id()
        best_ranking = next(
            (r for r in critic_report.rankings if r.variant_id == best_variant_id),
            None
        )
        
        logger.debug(f"  Researcher seleccionó: {best_variant_id}")
        
        # 3. Obtener variante seleccionada
        selected_variant = proposal.get_variant(best_variant_id)
        if not selected_variant:
            selected_variant = proposal.variants[0]
        
        # 4. Aplicar passes
        processed_events = self._apply_passes(selected_variant.events)
        
        # 5. PM valida
        temp_variant = Variant(
            id=selected_variant.id,
            tags=selected_variant.tags,
            events=processed_events,
        )
        
        validation = self.pm.validate_variant(
            temp_variant,
            proposal.window.start_step,
            proposal.window.end_step,
        )
        
        # 6. Si pasa validación, agregar al score
        if validation.is_valid:
            score.add_events(processed_events)
            self.session.validation_passes += 1
            self.session.total_events += len(processed_events)
        else:
            # Intentar auto-corrección
            corrected_events = self._auto_correct(processed_events, validation)
            if corrected_events:
                score.add_events(corrected_events)
                self.session.validation_passes += 1
                self.session.total_events += len(corrected_events)
                processed_events = corrected_events
            else:
                logger.warning(f"  Bar {bar_index} falló validación: {validation.violations}")
                self.session.validation_failures += 1
        
        return IterationResult(
            bar_index=bar_index,
            selected_variant_id=best_variant_id,
            score_before_passes=best_ranking.score if best_ranking else 0,
            score_after_validation=best_ranking.score if best_ranking and validation.is_valid else 0,
            events_added=len(processed_events) if validation.is_valid else 0,
            hints=critic_report.hints,
            passed_validation=validation.is_valid,
        )
    
    def _apply_passes(self, events: List[NoteEvent]) -> List[NoteEvent]:
        """Aplica passes de post-procesamiento"""
        processed = []
        
        for event in events:
            # Pass 1: Cuantizar velocity
            quantized_velocity = self.pm.quantize_velocity(event.velocity)
            
            # Pass 2: Asegurar duración mínima
            dur = max(1, event.dur_steps)
            
            processed.append(NoteEvent(
                type="note",
                track=event.track,
                pitch=event.pitch,
                velocity=quantized_velocity,
                start_step=event.start_step,
                dur_steps=dur,
            ))
        
        # Pass 3: Resolver overlaps por track
        processed = self._resolve_overlaps(processed)
        
        return processed
    
    def _resolve_overlaps(self, events: List[NoteEvent]) -> List[NoteEvent]:
        """Resuelve overlaps en tracks monofónicos"""
        by_track: Dict[str, List[NoteEvent]] = {}
        
        for event in events:
            if event.track not in by_track:
                by_track[event.track] = []
            by_track[event.track].append(event)
        
        result = []
        
        for track_id, track_events in by_track.items():
            if track_id in self.constraints.hard.monophonic_tracks:
                # Ordenar por start_step
                track_events = sorted(track_events, key=lambda e: e.start_step)
                
                cleaned = []
                for event in track_events:
                    if not cleaned:
                        cleaned.append(event)
                    else:
                        last = cleaned[-1]
                        if event.start_step >= last.end_step:
                            cleaned.append(event)
                        else:
                            # Truncar nota anterior
                            new_dur = event.start_step - last.start_step
                            if new_dur > 0:
                                cleaned[-1] = NoteEvent(
                                    type="note",
                                    track=last.track,
                                    pitch=last.pitch,
                                    velocity=last.velocity,
                                    start_step=last.start_step,
                                    dur_steps=new_dur,
                                )
                            cleaned.append(event)
                
                result.extend(cleaned)
            else:
                result.extend(track_events)
        
        return result
    
    def _auto_correct(
        self,
        events: List[NoteEvent],
        validation: ValidationResult,
    ) -> Optional[List[NoteEvent]]:
        """Intenta auto-corregir violaciones"""
        corrected = list(events)
        
        for violation in validation.hard_violations:
            if violation.rule == "pitch_range" and violation.event_index is not None:
                # Corregir pitch fuera de rango
                event = corrected[violation.event_index]
                track = event.track
                
                if track in self.constraints.hard.pitch_ranges:
                    pr = self.constraints.hard.pitch_ranges[track]
                    new_pitch = max(pr.min, min(pr.max, event.pitch))
                    
                    corrected[violation.event_index] = NoteEvent(
                        type="note",
                        track=event.track,
                        pitch=new_pitch,
                        velocity=event.velocity,
                        start_step=event.start_step,
                        dur_steps=event.dur_steps,
                    )
        
        # Re-resolver overlaps después de correcciones
        corrected = self._resolve_overlaps(corrected)
        
        # Re-validar
        from models.proposal import Variant, Window
        temp_variant = Variant(id="corrected", tags=["auto_corrected"], events=corrected)
        
        if events:
            min_step = min(e.start_step for e in events)
            max_step = max(e.start_step for e in events) + 16
            re_validation = self.pm.validate_variant(temp_variant, min_step, max_step)
            
            if re_validation.is_valid:
                return corrected
        
        return None
    
    def _log_session_summary(self) -> None:
        """Registra resumen de la sesión"""
        if not self.session:
            return
        
        logger.info("\n" + "=" * 50)
        logger.info("RESUMEN DE COMPOSICIÓN")
        logger.info("=" * 50)
        logger.info(f"Título: {self.session.score.metadata.title}")
        logger.info(f"Total eventos: {self.session.total_events}")
        logger.info(f"Compases procesados: {len(self.session.iterations)}")
        logger.info(f"Validaciones OK: {self.session.validation_passes}")
        logger.info(f"Validaciones fallidas: {self.session.validation_failures}")
        
        # Distribución por track
        track_counts: Dict[str, int] = {}
        for event in self.session.score.events:
            track_counts[event.track] = track_counts.get(event.track, 0) + 1
        
        logger.info("\nEventos por track:")
        for track, count in sorted(track_counts.items()):
            logger.info(f"  {track}: {count}")
        
        # Score promedio
        if self.session.iterations:
            avg_score = sum(
                it.score_after_validation for it in self.session.iterations
            ) / len(self.session.iterations)
            logger.info(f"\nScore promedio: {avg_score:.1f}")
        
        logger.info("=" * 50 + "\n")
    
    def get_score(self) -> Optional[ScoreV1]:
        """Obtiene el score actual"""
        return self.session.score if self.session else None
    
    def export_to_dict(self) -> Dict[str, Any]:
        """Exporta score a diccionario"""
        if not self.session:
            return {}
        return self.session.score.model_dump()
    
    def export_to_json(self, filepath: str) -> None:
        """Exporta score a archivo JSON"""
        import json
        
        if not self.session:
            raise ValueError("No hay sesión activa")
        
        with open(filepath, "w") as f:
            json.dump(self.session.score.model_dump(), f, indent=2)
        
        logger.info(f"Score exportado a: {filepath}")
