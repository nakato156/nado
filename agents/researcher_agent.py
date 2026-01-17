"""
Researcher Agent - Evaluator / Critic & Optimization
Responsable de medir, puntuar y dirigir mejora iterativa
"""
import sys
sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

import math
from typing import List, Optional, Dict, Any
from collections import Counter
from agents.base_agent import BaseAgent
from models.score import ScoreV1, NoteEvent
from models.proposal import ProposalV1, Variant, Window
from models.critic_report import (
    CriticReportV1, 
    VariantRanking, 
    Metrics, 
    Hint, 
    HintTarget,
    AgentInfo,
)
from models.constraints import ConstraintsV1
from src.agent import create_deepseek_llm


class ResearcherAgent(BaseAgent):
    """
    Researcher Agent - Critic & Optimization
    
    Responsabilidades:
    - Calcular métricas por ventana y globales
    - Puntuar y rankear variantes
    - Sugerir mejoras (hints)
    - Preparar datos para ML futuro
    """
    
    VERSION = "1.0.0"
    
    def __init__(
        self,
        constraints: Optional[ConstraintsV1] = None,
        use_llm: bool = False,
    ):
        super().__init__(
            name="Researcher Agent",
            description="Evaluator / Critic & Optimization Agent"
        )
        self.constraints = constraints or ConstraintsV1.default_8bit()
        self.llm = create_deepseek_llm() if use_llm else None
        self.history: List[Dict[str, Any]] = []
    
    def run(self, query: str) -> str:
        """Ejecuta consulta general usando LLM"""
        if self.llm:
            from langchain_core.messages import HumanMessage, SystemMessage
            messages = [
                SystemMessage(content=self._get_system_prompt()),
                HumanMessage(content=query),
            ]
            response = self.llm.invoke(messages)
            return response.content
        return "LLM no configurado para Researcher Agent"
    
    def _get_system_prompt(self) -> str:
        return """Eres el Researcher Agent de un sistema de composición musical 8-bit.
Tu rol es evaluar y mejorar la calidad musical.

Métricas que consideras:
- Densidad: eventos por compás
- Repetición: uso de motivos recurrentes
- Entropía rítmica: variedad en los onsets
- Violaciones de rango: notas fuera de rango permitido
- Cumplimiento de estilo: adherencia a características 8-bit

Cuando evalúas, piensas en:
- ¿Suena como música de NES?
- ¿Hay coherencia melódica?
- ¿El ritmo es interesante pero no caótico?
- ¿Hay balance entre repetición y variedad?
"""
    
    def evaluate_proposal(
        self,
        proposal: ProposalV1,
        score: Optional[ScoreV1] = None,
    ) -> CriticReportV1:
        """
        Evalúa una propuesta y genera reporte
        
        Args:
            proposal: Propuesta del Musician
            score: Score actual para contexto
            
        Returns:
            CriticReportV1 con rankings, métricas y hints
        """
        rankings = []
        all_metrics = []
        
        for variant in proposal.variants:
            metrics = self._calculate_metrics(variant, proposal.window)
            all_metrics.append(metrics)
            
            score_value = self._calculate_score(metrics, variant)
            passed = self._check_hard_constraints(variant, proposal.window)
            reasons = self._generate_reasons(metrics, passed)
            
            rankings.append(VariantRanking(
                variant_id=variant.id,
                score=score_value,
                passed_hard_constraints=passed,
                reasons=reasons,
            ))
        
        # Ordenar por score descendente
        rankings.sort(key=lambda r: r.score, reverse=True)
        
        # Calcular métricas agregadas
        avg_metrics = self._aggregate_metrics(all_metrics)
        
        # Generar hints
        hints = self._generate_hints(proposal, rankings, avg_metrics)
        
        report = CriticReportV1(
            window=proposal.window,
            agent=AgentInfo(name=self.name, version=self.VERSION),
            rankings=rankings,
            metrics=avg_metrics,
            hints=hints,
        )
        
        # Guardar en historial
        self.history.append({
            "window": proposal.window.model_dump(),
            "best_variant": rankings[0].variant_id if rankings else None,
            "best_score": rankings[0].score if rankings else 0,
            "metrics": avg_metrics.model_dump(),
        })
        
        return report
    
    def _calculate_metrics(self, variant: Variant, window: Window) -> Metrics:
        """Calcula métricas para una variante"""
        events = variant.events
        window_size = window.end_step - window.start_step
        
        # Densidad: eventos por step
        density = len(events) / window_size if window_size > 0 else 0
        
        # Repetición: ratio de pitches repetidos
        repetition = self._calculate_repetition(events)
        
        # Entropía rítmica
        rhythm_entropy = self._calculate_rhythm_entropy(events, window_size)
        
        # Violaciones de rango
        range_violations = self._count_range_violations(events)
        
        # Violaciones de polifonía
        polyphony_violations = self._count_polyphony_violations(events)
        
        # Cumplimiento de estilo
        style_compliance = self._calculate_style_compliance(events, window)
        
        return Metrics(
            density=density,
            repetition=repetition,
            rhythm_entropy=rhythm_entropy,
            range_violations=range_violations,
            polyphony_violations=polyphony_violations,
            style_compliance=style_compliance,
        )
    
    def _calculate_repetition(self, events: List[NoteEvent]) -> float:
        """Calcula ratio de repetición de pitches"""
        if len(events) < 2:
            return 0.0
        
        pitches = [e.pitch for e in events]
        pitch_counts = Counter(pitches)
        
        # Repetidos = pitches que aparecen más de una vez
        repeated = sum(count - 1 for count in pitch_counts.values() if count > 1)
        
        return min(1.0, repeated / len(pitches))
    
    def _calculate_rhythm_entropy(self, events: List[NoteEvent], window_size: int) -> float:
        """Calcula entropía de los onsets (variedad rítmica)"""
        if not events or window_size == 0:
            return 0.0
        
        # Normalizar onsets a posiciones relativas
        onsets = [(e.start_step % window_size) for e in events]
        onset_counts = Counter(onsets)
        
        total = len(onsets)
        entropy = 0.0
        
        for count in onset_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        
        # Normalizar por entropía máxima posible
        max_entropy = math.log2(total) if total > 1 else 1
        
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def _count_range_violations(self, events: List[NoteEvent]) -> int:
        """Cuenta violaciones de rango de pitch"""
        violations = 0
        
        for event in events:
            if event.track in self.constraints.hard.pitch_ranges:
                pr = self.constraints.hard.pitch_ranges[event.track]
                if event.pitch < pr.min or event.pitch > pr.max:
                    violations += 1
        
        return violations
    
    def _count_polyphony_violations(self, events: List[NoteEvent]) -> int:
        """Cuenta violaciones de monofonía"""
        violations = 0
        
        # Agrupar por track
        by_track: Dict[str, List[NoteEvent]] = {}
        for event in events:
            if event.track not in by_track:
                by_track[event.track] = []
            by_track[event.track].append(event)
        
        # Verificar overlaps
        for track_id in self.constraints.hard.monophonic_tracks:
            if track_id not in by_track:
                continue
            
            track_events = sorted(by_track[track_id], key=lambda e: e.start_step)
            
            for i in range(len(track_events) - 1):
                if track_events[i].end_step > track_events[i + 1].start_step:
                    violations += 1
        
        return violations
    
    def _calculate_style_compliance(self, events: List[NoteEvent], window: Window) -> float:
        """Calcula cumplimiento de estilo 8-bit"""
        if not events:
            return 0.5
        
        score = 1.0
        
        # Verificar que velocities sean de los niveles permitidos
        valid_velocities = set(self.constraints.hard.velocity_levels)
        invalid_vel = sum(1 for e in events if e.velocity not in valid_velocities)
        if invalid_vel > 0:
            score -= 0.1 * (invalid_vel / len(events))
        
        # Verificar grid (preferir step_grid)
        grid = self.constraints.soft.prefer_step_grid
        off_grid = sum(1 for e in events if e.start_step % grid != 0)
        if off_grid > 0:
            score -= 0.05 * (off_grid / len(events))
        
        # Densidad cercana al objetivo
        density = len(events) / (window.end_step - window.start_step)
        target_density = self.constraints.soft.target_density_per_bar / 16  # Normalizar
        density_diff = abs(density - target_density)
        score -= 0.1 * min(1.0, density_diff)
        
        return max(0.0, min(1.0, score))
    
    def _calculate_score(self, metrics: Metrics, variant: Variant) -> float:
        """Calcula score total para una variante"""
        score = 50.0  # Base
        
        # Penalizar violaciones duras
        score -= metrics.range_violations * 10
        score -= metrics.polyphony_violations * 15
        
        # Bonificar cumplimiento de estilo
        score += metrics.style_compliance * 20
        
        # Bonificar repetición controlada (0.2-0.4 es ideal)
        if 0.2 <= metrics.repetition <= 0.4:
            score += 10
        elif metrics.repetition > 0.6:
            score -= 5  # Muy repetitivo
        
        # Bonificar variedad rítmica
        score += metrics.rhythm_entropy * 10
        
        # Bonificar densidad apropiada
        target = self.constraints.soft.target_density_per_bar / 16
        if abs(metrics.density - target) < 0.2:
            score += 5
        
        # Bonificar por tener eventos en múltiples tracks
        tracks_used = len(set(e.track for e in variant.events))
        score += tracks_used * 3
        
        return max(0.0, min(100.0, score))
    
    def _check_hard_constraints(self, variant: Variant, window: Window) -> bool:
        """Verifica si la variante pasa constraints duros"""
        # Verificar rango
        for event in variant.events:
            if event.track in self.constraints.hard.pitch_ranges:
                pr = self.constraints.hard.pitch_ranges[event.track]
                if event.pitch < pr.min or event.pitch > pr.max:
                    return False
            
            # Verificar bounds de ventana
            if event.start_step < window.start_step or event.start_step >= window.end_step:
                return False
        
        # Verificar monofonía
        by_track: Dict[str, List[NoteEvent]] = {}
        for event in variant.events:
            if event.track not in by_track:
                by_track[event.track] = []
            by_track[event.track].append(event)
        
        for track_id in self.constraints.hard.monophonic_tracks:
            if track_id not in by_track:
                continue
            
            track_events = sorted(by_track[track_id], key=lambda e: e.start_step)
            for i in range(len(track_events) - 1):
                if track_events[i].end_step > track_events[i + 1].start_step:
                    return False
        
        return True
    
    def _generate_reasons(self, metrics: Metrics, passed: bool) -> List[str]:
        """Genera razones para el ranking"""
        reasons = []
        
        if not passed:
            if metrics.range_violations > 0:
                reasons.append(f"{metrics.range_violations} violaciones de rango")
            if metrics.polyphony_violations > 0:
                reasons.append(f"{metrics.polyphony_violations} violaciones de monofonía")
        
        if metrics.style_compliance >= 0.8:
            reasons.append("Excelente cumplimiento de estilo 8-bit")
        elif metrics.style_compliance < 0.5:
            reasons.append("Bajo cumplimiento de estilo")
        
        if 0.2 <= metrics.repetition <= 0.4:
            reasons.append("Buena repetición de motivos")
        
        if metrics.rhythm_entropy > 0.7:
            reasons.append("Alta variedad rítmica")
        
        return reasons
    
    def _generate_hints(
        self,
        proposal: ProposalV1,
        rankings: List[VariantRanking],
        metrics: Metrics,
    ) -> List[Hint]:
        """Genera hints de mejora"""
        hints = []
        
        # Hints basados en métricas
        if metrics.density > 1.0:
            hints.append(Hint(
                priority="medium",
                message="Reducir densidad de eventos",
                target=HintTarget(track="all", bar_index=proposal.window.bar_index),
            ))
        elif metrics.density < 0.2:
            hints.append(Hint(
                priority="low",
                message="Considerar añadir más eventos",
                target=HintTarget(track="all", bar_index=proposal.window.bar_index),
            ))
        
        if metrics.repetition > 0.6:
            hints.append(Hint(
                priority="medium",
                message="Añadir más variedad melódica",
                target=HintTarget(track="pulse1", bar_index=proposal.window.bar_index),
            ))
        elif metrics.repetition < 0.1:
            hints.append(Hint(
                priority="low",
                message="Considerar repetir algunos motivos",
                target=HintTarget(track="pulse1", bar_index=proposal.window.bar_index),
            ))
        
        if metrics.range_violations > 0:
            hints.append(Hint(
                priority="high",
                message=f"Corregir {metrics.range_violations} notas fuera de rango",
                target=HintTarget(track="all", bar_index=proposal.window.bar_index),
            ))
        
        if metrics.polyphony_violations > 0:
            hints.append(Hint(
                priority="high",
                message=f"Resolver {metrics.polyphony_violations} overlaps",
                target=HintTarget(track="all", bar_index=proposal.window.bar_index),
            ))
        
        if metrics.style_compliance < 0.6:
            hints.append(Hint(
                priority="medium",
                message="Ajustar velocities a niveles 8-bit (64, 100, 127)",
                target=HintTarget(track="all"),
            ))
        
        return hints
    
    def _aggregate_metrics(self, metrics_list: List[Metrics]) -> Metrics:
        """Agrega métricas de múltiples variantes"""
        if not metrics_list:
            return Metrics(
                density=0, repetition=0, rhythm_entropy=0, 
                range_violations=0, polyphony_violations=0, style_compliance=0
            )
        
        n = len(metrics_list)
        return Metrics(
            density=sum(m.density for m in metrics_list) / n,
            repetition=sum(m.repetition for m in metrics_list) / n,
            rhythm_entropy=sum(m.rhythm_entropy for m in metrics_list) / n,
            range_violations=sum(m.range_violations for m in metrics_list),
            polyphony_violations=sum(m.polyphony_violations for m in metrics_list),
            style_compliance=sum(m.style_compliance for m in metrics_list) / n,
        )
    
    def rerank_proposals(
        self,
        proposals: List[ProposalV1],
        score: Optional[ScoreV1] = None,
    ) -> List[tuple]:
        """
        Re-rankea múltiples propuestas
        
        Returns:
            Lista de (proposal_index, variant_id, score) ordenados
        """
        all_rankings = []
        
        for i, proposal in enumerate(proposals):
            report = self.evaluate_proposal(proposal, score)
            for ranking in report.rankings:
                all_rankings.append((i, ranking.variant_id, ranking.score))
        
        all_rankings.sort(key=lambda x: x[2], reverse=True)
        return all_rankings
    
    def get_improvement_delta(self) -> float:
        """Calcula mejora entre últimas iteraciones"""
        if len(self.history) < 2:
            return 0.0
        
        recent = self.history[-1]["best_score"]
        previous = self.history[-2]["best_score"]
        
        return recent - previous
