"""
Modelos Pydantic para Critic Reports del Researcher Agent
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from models.proposal import Window, AgentInfo


class VariantRanking(BaseModel):
    """Ranking de una variante"""
    variant_id: str
    score: float
    passed_hard_constraints: bool
    reasons: List[str] = Field(default_factory=list)


class Metrics(BaseModel):
    """Métricas calculadas para una ventana"""
    density: float = Field(ge=0.0)
    repetition: float = Field(ge=0.0, le=1.0)
    rhythm_entropy: float = Field(ge=0.0)
    range_violations: int = Field(ge=0)
    polyphony_violations: int = Field(ge=0, default=0)
    style_compliance: float = Field(ge=0.0, le=1.0, default=1.0)
    
    class Config:
        extra = "allow"  # Permite métricas adicionales


class HintTarget(BaseModel):
    """Target específico para un hint"""
    track: str
    bar_index: Optional[int] = None
    start_step: Optional[int] = None
    end_step: Optional[int] = None


class Hint(BaseModel):
    """Sugerencia de mejora del critic"""
    priority: Literal["low", "medium", "high"]
    message: str
    target: HintTarget


class CriticReportV1(BaseModel):
    """Reporte del Researcher/Critic Agent v1"""
    schema_version: Literal["critic_report.v1"] = "critic_report.v1"
    window: Window
    agent: AgentInfo
    rankings: List[VariantRanking] = Field(min_length=1)
    metrics: Metrics
    hints: List[Hint] = Field(default_factory=list)
    
    def get_best_variant_id(self) -> str:
        """Obtiene el ID de la mejor variante (mayor score que pasa constraints)"""
        valid = [r for r in self.rankings if r.passed_hard_constraints]
        if not valid:
            # Si ninguna pasa, devolver la de mayor score
            return max(self.rankings, key=lambda r: r.score).variant_id
        return max(valid, key=lambda r: r.score).variant_id
    
    def get_high_priority_hints(self) -> List[Hint]:
        """Obtiene hints de alta prioridad"""
        return [h for h in self.hints if h.priority == "high"]
