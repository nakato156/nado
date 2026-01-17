"""
Modelos Pydantic para Proposals del Musician Agent
"""
from typing import List, Literal
from pydantic import BaseModel, Field

from models.score import NoteEvent


class Window(BaseModel):
    """Ventana de tiempo para propuestas"""
    bar_index: int = Field(ge=0)
    start_step: int = Field(ge=0)
    end_step: int = Field(ge=1)


class AgentInfo(BaseModel):
    """Información del agente"""
    name: str
    version: str = "1.0.0"


class Variant(BaseModel):
    """Una variante de propuesta musical"""
    id: str
    tags: List[str] = Field(default_factory=list)
    events: List[NoteEvent] = Field(default_factory=list)


class ProposalV1(BaseModel):
    """Propuesta del Musician Agent v1"""
    schema_version: Literal["proposal.v1"] = "proposal.v1"
    window: Window
    agent: AgentInfo
    variants: List[Variant] = Field(min_length=1)
    
    def get_variant(self, variant_id: str) -> Variant | None:
        """Obtiene una variante por ID"""
        for v in self.variants:
            if v.id == variant_id:
                return v
        return None
    
    def get_best_variant_by_tag(self, tag: str) -> Variant | None:
        """Obtiene la primera variante que tenga un tag específico"""
        for v in self.variants:
            if tag in v.tags:
                return v
        return None
