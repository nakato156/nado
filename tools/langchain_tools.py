"""
Definiciones de Tools para LangChain con Tool Calling
Wrapper para integrar las score_tools con el agente
"""
import sys
sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

import json
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool

from tools.score_tools import (
    validate_score_v1,
    score_v1_to_midi,
    midi_to_wav_fluidsynth,
    play_audio,
    score_v1_pipeline_listen,
)


# ============================================================================
# Schemas de entrada para las tools
# ============================================================================

class ValidateScoreInput(BaseModel):
    """Input para validate_score_v1"""
    score_json: Dict[str, Any] = Field(description="Score object siguiendo score.v1 contract")
    constraints_json: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Constraints.v1 opcional para validación adicional"
    )
    strict: bool = Field(
        default=True,
        description="Si True, warnings se tratan como errores"
    )


class ScoreToMidiInput(BaseModel):
    """Input para score_v1_to_midi"""
    score_json: Dict[str, Any] = Field(description="Score object siguiendo score.v1 contract")
    out_mid_path: str = Field(description="Ruta para escribir el archivo MIDI")
    overwrite: bool = Field(default=True, description="Sobrescribir si existe")
    midi_channel_map: Optional[Dict[str, int]] = Field(
        default=None,
        description="Mapeo opcional track_id -> canal MIDI [0..15]"
    )


class MidiToWavInput(BaseModel):
    """Input para midi_to_wav_fluidsynth"""
    mid_path: str = Field(description="Ruta al archivo MIDI de entrada")
    soundfont_path: str = Field(description="Ruta al archivo SoundFont .sf2")
    out_wav_path: str = Field(description="Ruta para el archivo WAV de salida")
    sample_rate: int = Field(default=44100, ge=8000, le=192000)
    gain: float = Field(default=0.7, ge=0.0, le=5.0)
    overwrite: bool = Field(default=True)


class PlayAudioInput(BaseModel):
    """Input para play_audio"""
    audio_path: str = Field(description="Ruta al archivo WAV/MP3/OGG")
    backend: str = Field(
        default="auto",
        description="Backend de reproducción: auto, ffplay, aplay, paplay, vlc"
    )
    blocking: bool = Field(
        default=False,
        description="Si True, espera a que termine la reproducción"
    )
    volume: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Volumen opcional"
    )


class PipelineListenInput(BaseModel):
    """Input para score_v1_pipeline_listen"""
    score_json: Dict[str, Any] = Field(description="Score object siguiendo score.v1 contract")
    soundfont_path: str = Field(description="Ruta al archivo SoundFont .sf2")
    out_mid_path: str = Field(default="./out.mid")
    out_wav_path: str = Field(default="./out.wav")
    sample_rate: int = Field(default=44100)
    backend: str = Field(default="auto")
    blocking: bool = Field(default=False)
    constraints_json: Optional[Dict[str, Any]] = Field(default=None)
    strict: bool = Field(default=True)


# ============================================================================
# Tools de LangChain
# ============================================================================

class ValidateScoreTool(BaseTool):
    """Tool para validar un score.v1"""
    name: str = "validate_score_v1"
    description: str = """Validates a score.v1 JSON against schema rules and hard constraints 
(timing bounds, monophony per track, pitch/velocity ranges). 
Returns violations with precise locations. Use this before converting to MIDI."""
    args_schema: Type[BaseModel] = ValidateScoreInput
    
    def _run(
        self,
        score_json: Dict[str, Any],
        constraints_json: Optional[Dict[str, Any]] = None,
        strict: bool = True,
    ) -> str:
        result = validate_score_v1(score_json, constraints_json, strict)
        return json.dumps(result, indent=2)


class ScoreToMidiTool(BaseTool):
    """Tool para convertir score.v1 a MIDI"""
    name: str = "score_v1_to_midi"
    description: str = """Converts a score.v1 JSON into a MIDI file. 
Uses tracks[].program as MIDI instrument program. 
Writes output to out_mid_path."""
    args_schema: Type[BaseModel] = ScoreToMidiInput
    
    def _run(
        self,
        score_json: Dict[str, Any],
        out_mid_path: str,
        overwrite: bool = True,
        midi_channel_map: Optional[Dict[str, int]] = None,
    ) -> str:
        result = score_v1_to_midi(score_json, out_mid_path, overwrite, midi_channel_map)
        return json.dumps(result, indent=2)


class MidiToWavTool(BaseTool):
    """Tool para renderizar MIDI a WAV"""
    name: str = "midi_to_wav_fluidsynth"
    description: str = """Renders a MIDI file to WAV using FluidSynth and a SoundFont (.sf2). 
Requires fluidsynth installed on the system."""
    args_schema: Type[BaseModel] = MidiToWavInput
    
    def _run(
        self,
        mid_path: str,
        soundfont_path: str,
        out_wav_path: str,
        sample_rate: int = 44100,
        gain: float = 0.7,
        overwrite: bool = True,
    ) -> str:
        result = midi_to_wav_fluidsynth(
            mid_path, soundfont_path, out_wav_path,
            sample_rate, gain, overwrite
        )
        return json.dumps(result, indent=2)


class PlayAudioTool(BaseTool):
    """Tool para reproducir audio"""
    name: str = "play_audio"
    description: str = """Plays an audio file on the local machine using an available 
backend (ffplay/aplay/paplay/vlc)."""
    args_schema: Type[BaseModel] = PlayAudioInput
    
    def _run(
        self,
        audio_path: str,
        backend: str = "auto",
        blocking: bool = False,
        volume: Optional[float] = None,
    ) -> str:
        result = play_audio(audio_path, backend, blocking, volume)
        return json.dumps(result, indent=2)


class PipelineListenTool(BaseTool):
    """Tool para pipeline end-to-end"""
    name: str = "score_v1_pipeline_listen"
    description: str = """End-to-end pipeline: validates score.v1, writes MIDI, 
renders WAV with FluidSynth, and plays it. 
Use this for rapid iteration - validates, converts, and plays in one call."""
    args_schema: Type[BaseModel] = PipelineListenInput
    
    def _run(
        self,
        score_json: Dict[str, Any],
        soundfont_path: str,
        out_mid_path: str = "./out.mid",
        out_wav_path: str = "./out.wav",
        sample_rate: int = 44100,
        backend: str = "auto",
        blocking: bool = False,
        constraints_json: Optional[Dict[str, Any]] = None,
        strict: bool = True,
    ) -> str:
        result = score_v1_pipeline_listen(
            score_json, soundfont_path, out_mid_path, out_wav_path,
            sample_rate, backend, blocking, constraints_json, strict
        )
        return json.dumps(result, indent=2)


# ============================================================================
# Lista de todas las tools disponibles
# ============================================================================

def get_all_score_tools():
    """Retorna lista de todas las tools de score"""
    return [
        ValidateScoreTool(),
        ScoreToMidiTool(),
        MidiToWavTool(),
        PlayAudioTool(),
        PipelineListenTool(),
    ]


def get_composition_tools():
    """Retorna tools útiles durante composición"""
    return [
        ValidateScoreTool(),
        PipelineListenTool(),
    ]


def get_export_tools():
    """Retorna tools para exportar y reproducir"""
    return [
        ScoreToMidiTool(),
        MidiToWavTool(),
        PlayAudioTool(),
    ]
