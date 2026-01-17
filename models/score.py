"""
Modelos Pydantic para el Score v1
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ScoreMetadata(BaseModel):
    """Metadatos del score"""
    title: str
    tempo_bpm: int = Field(ge=1)
    time_signature: str = Field(pattern=r"^[0-9]+/[0-9]+$")
    key: str
    length_bars: int = Field(ge=1)


class Resolution(BaseModel):
    """Resolución temporal del score"""
    steps_per_beat: int = Field(ge=1, default=4)
    beats_per_bar: int = Field(ge=1, default=4)
    
    @property
    def steps_per_bar(self) -> int:
        return self.steps_per_beat * self.beats_per_bar


class Track(BaseModel):
    """Definición de una pista"""
    id: str
    role: Literal["melody", "harmony", "bass", "drums", "fx"]
    monophonic: bool = True
    program: Optional[int] = Field(default=0, ge=0, le=127)


class NoteEvent(BaseModel):
    """Evento de nota"""
    type: Literal["note"] = "note"
    track: str
    pitch: int = Field(ge=0, le=127)
    velocity: int = Field(ge=1, le=127)
    start_step: int = Field(ge=0)
    dur_steps: int = Field(ge=1)
    
    @property
    def end_step(self) -> int:
        return self.start_step + self.dur_steps


class ScoreV1(BaseModel):
    """Score completo v1"""
    schema_version: Literal["score.v1"] = "score.v1"
    metadata: ScoreMetadata
    resolution: Resolution
    tracks: List[Track]
    events: List[NoteEvent] = Field(default_factory=list)
    
    def get_track(self, track_id: str) -> Optional[Track]:
        """Obtiene un track por ID"""
        for track in self.tracks:
            if track.id == track_id:
                return track
        return None
    
    def get_events_for_track(self, track_id: str) -> List[NoteEvent]:
        """Obtiene eventos de un track específico"""
        return [e for e in self.events if e.track == track_id]
    
    def get_events_in_window(self, start_step: int, end_step: int) -> List[NoteEvent]:
        """Obtiene eventos en una ventana de tiempo"""
        return [
            e for e in self.events 
            if e.start_step >= start_step and e.start_step < end_step
        ]
    
    def add_events(self, events: List[NoteEvent]) -> None:
        """Agrega eventos al score"""
        self.events.extend(events)
    
    def total_steps(self) -> int:
        """Calcula el total de steps del score"""
        return self.metadata.length_bars * self.resolution.steps_per_bar
    
    @classmethod
    def create_empty(
        cls,
        title: str = "Untitled",
        tempo_bpm: int = 120,
        time_signature: str = "4/4",
        key: str = "C",
        length_bars: int = 8,
        steps_per_beat: int = 4,
    ) -> "ScoreV1":
        """Crea un score vacío con configuración por defecto para 8-bit"""
        beats_per_bar = int(time_signature.split("/")[0])
        
        return cls(
            metadata=ScoreMetadata(
                title=title,
                tempo_bpm=tempo_bpm,
                time_signature=time_signature,
                key=key,
                length_bars=length_bars,
            ),
            resolution=Resolution(
                steps_per_beat=steps_per_beat,
                beats_per_bar=beats_per_bar,
            ),
            tracks=[
                Track(id="pulse1", role="melody", monophonic=True, program=80),
                Track(id="pulse2", role="harmony", monophonic=True, program=80),
                Track(id="triangle", role="bass", monophonic=True, program=38),
                Track(id="noise", role="drums", monophonic=True, program=0),
            ],
            events=[],
        )
