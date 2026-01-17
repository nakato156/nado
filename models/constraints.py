"""
Modelos Pydantic para Constraints del PM Agent
"""
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class PitchRange(BaseModel):
    """Rango de pitch permitido para un track"""
    min: int = Field(ge=0, le=127)
    max: int = Field(ge=0, le=127)


class HardConstraints(BaseModel):
    """Constraints duros - violación causa rechazo"""
    required_tracks: List[str] = Field(min_length=1)
    monophonic_tracks: List[str] = Field(default_factory=list)
    max_events_per_bar: int = Field(ge=1, default=32)
    pitch_ranges: Dict[str, PitchRange] = Field(default_factory=dict)
    velocity_levels: List[int] = Field(default_factory=lambda: [64, 100, 127])
    forbid_overflow: bool = True


class SoftConstraints(BaseModel):
    """Constraints suaves - afectan scoring pero no rechazan"""
    target_density_per_bar: float = Field(ge=0.0, default=8.0)
    target_repetition: float = Field(ge=0.0, le=1.0, default=0.3)
    prefer_step_grid: int = Field(ge=1, default=4)
    style_tags: List[str] = Field(default_factory=lambda: ["8bit", "nes"])


class ConstraintsV1(BaseModel):
    """Constraints del PM Agent v1"""
    schema_version: Literal["constraints.v1"] = "constraints.v1"
    hard: HardConstraints
    soft: SoftConstraints
    
    @classmethod
    def default_8bit(cls) -> "ConstraintsV1":
        """Crea constraints por defecto para estilo 8-bit NES"""
        return cls(
            hard=HardConstraints(
                required_tracks=["pulse1", "triangle", "noise"],
                monophonic_tracks=["pulse1", "pulse2", "triangle", "noise"],
                max_events_per_bar=32,
                pitch_ranges={
                    "pulse1": PitchRange(min=48, max=96),  # C3-C7
                    "pulse2": PitchRange(min=48, max=96),  # C3-C7
                    "triangle": PitchRange(min=24, max=60),  # C1-C4
                    "noise": PitchRange(min=0, max=127),  # Sin restricción
                },
                velocity_levels=[64, 100, 127],  # Solo 3 niveles como NES
                forbid_overflow=True,
            ),
            soft=SoftConstraints(
                target_density_per_bar=8.0,
                target_repetition=0.3,
                prefer_step_grid=4,
                style_tags=["8bit", "nes", "chiptune"],
            ),
        )


class ConstraintViolation(BaseModel):
    """Violación de constraint detectada"""
    constraint_type: Literal["hard", "soft"]
    rule: str
    message: str
    track: Optional[str] = None
    bar_index: Optional[int] = None
    event_index: Optional[int] = None


class ValidationResult(BaseModel):
    """Resultado de validación del PM"""
    is_valid: bool
    violations: List[ConstraintViolation] = Field(default_factory=list)
    
    @property
    def hard_violations(self) -> List[ConstraintViolation]:
        return [v for v in self.violations if v.constraint_type == "hard"]
    
    @property
    def soft_violations(self) -> List[ConstraintViolation]:
        return [v for v in self.violations if v.constraint_type == "soft"]
