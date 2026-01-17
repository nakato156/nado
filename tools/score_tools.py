"""
Implementación de Tools para el sistema NADO
Convierte scores a MIDI, renderiza audio, valida, etc.
"""
import subprocess
import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path


def validate_score_v1(
    score_json: Dict[str, Any],
    constraints_json: Optional[Dict[str, Any]] = None,
    strict: bool = True,
) -> Dict[str, Any]:
    """
    Valida un score.v1 JSON contra schema y constraints
    
    Args:
        score_json: Score objeto siguiendo score.v1
        constraints_json: Constraints.v1 opcional
        strict: Si True, warnings son errores
        
    Returns:
        Dict con 'valid', 'errors', 'warnings'
    """
    errors = []
    warnings = []
    
    # Validar estructura básica
    required_fields = ["schema_version", "metadata", "resolution", "tracks", "events"]
    for field in required_fields:
        if field not in score_json:
            errors.append(f"Campo requerido faltante: {field}")
    
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}
    
    # Validar metadata
    metadata = score_json.get("metadata", {})
    for field in ["title", "tempo_bpm", "time_signature", "key", "length_bars"]:
        if field not in metadata:
            errors.append(f"metadata.{field} faltante")
    
    # Validar resolution
    resolution = score_json.get("resolution", {})
    steps_per_beat = resolution.get("steps_per_beat", 4)
    beats_per_bar = resolution.get("beats_per_bar", 4)
    steps_per_bar = steps_per_beat * beats_per_bar
    
    # Validar tracks
    track_ids = set()
    monophonic_tracks = set()
    for track in score_json.get("tracks", []):
        track_ids.add(track.get("id"))
        if track.get("monophonic", False):
            monophonic_tracks.add(track.get("id"))
    
    # Validar eventos
    events = score_json.get("events", [])
    length_bars = metadata.get("length_bars", 1)
    max_step = length_bars * steps_per_bar
    
    # Agrupar eventos por track para verificar monofonía
    events_by_track: Dict[str, List[Dict]] = {}
    
    for i, event in enumerate(events):
        track_id = event.get("track")
        
        # Track existe
        if track_id not in track_ids:
            errors.append(f"Evento {i}: track '{track_id}' no definido")
            continue
        
        # Bounds
        start = event.get("start_step", 0)
        dur = event.get("dur_steps", 1)
        
        if start < 0:
            errors.append(f"Evento {i}: start_step negativo")
        if start >= max_step:
            errors.append(f"Evento {i}: start_step {start} >= max {max_step}")
        if dur < 1:
            errors.append(f"Evento {i}: dur_steps < 1")
        
        # Pitch y velocity
        pitch = event.get("pitch", 0)
        velocity = event.get("velocity", 100)
        
        if pitch < 0 or pitch > 127:
            errors.append(f"Evento {i}: pitch {pitch} fuera de rango [0, 127]")
        if velocity < 1 or velocity > 127:
            errors.append(f"Evento {i}: velocity {velocity} fuera de rango [1, 127]")
        
        # Acumular para monofonía
        if track_id not in events_by_track:
            events_by_track[track_id] = []
        events_by_track[track_id].append(event)
    
    # Verificar monofonía
    for track_id in monophonic_tracks:
        if track_id not in events_by_track:
            continue
        
        track_events = sorted(events_by_track[track_id], key=lambda e: e.get("start_step", 0))
        
        for i in range(len(track_events) - 1):
            current = track_events[i]
            next_event = track_events[i + 1]
            
            end_step = current.get("start_step", 0) + current.get("dur_steps", 1)
            next_start = next_event.get("start_step", 0)
            
            if end_step > next_start:
                errors.append(
                    f"Overlap en track monofónico '{track_id}': "
                    f"evento termina en step {end_step}, siguiente inicia en {next_start}"
                )
    
    # Validar contra constraints si se proporcionan
    if constraints_json:
        hard = constraints_json.get("hard", {})
        
        # Required tracks
        required_tracks = hard.get("required_tracks", [])
        for rt in required_tracks:
            if rt not in track_ids:
                errors.append(f"Track requerido '{rt}' no encontrado")
        
        # Pitch ranges
        pitch_ranges = hard.get("pitch_ranges", {})
        for event in events:
            track_id = event.get("track")
            if track_id in pitch_ranges:
                pr = pitch_ranges[track_id]
                pitch = event.get("pitch", 0)
                if pitch < pr.get("min", 0) or pitch > pr.get("max", 127):
                    errors.append(
                        f"Pitch {pitch} fuera de rango para '{track_id}' "
                        f"[{pr.get('min')}, {pr.get('max')}]"
                    )
        
        # Velocity levels
        velocity_levels = hard.get("velocity_levels", [])
        if velocity_levels:
            for event in events:
                vel = event.get("velocity", 100)
                if vel not in velocity_levels:
                    warnings.append(f"Velocity {vel} no es un nivel estándar")
    
    valid = len(errors) == 0
    if strict and warnings:
        valid = False
        errors.extend(warnings)
        warnings = []
    
    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
    }


def score_v1_to_midi(
    score_json: Dict[str, Any],
    out_mid_path: str,
    overwrite: bool = True,
    midi_channel_map: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Convierte un score.v1 JSON a archivo MIDI
    
    Args:
        score_json: Score objeto
        out_mid_path: Ruta de salida del MIDI
        overwrite: Sobrescribir si existe
        midi_channel_map: Mapeo track_id -> canal MIDI
        
    Returns:
        Dict con 'success', 'path', 'error'
    """
    try:
        from midiutil import MIDIFile
    except ImportError:
        return {
            "success": False,
            "path": None,
            "error": "midiutil no instalado. Ejecuta: pip install MIDIUtil"
        }
    
    # Verificar si existe
    if os.path.exists(out_mid_path) and not overwrite:
        return {
            "success": False,
            "path": None,
            "error": f"Archivo existe y overwrite=False: {out_mid_path}"
        }
    
    # Extraer metadata
    metadata = score_json.get("metadata", {})
    tempo_bpm = metadata.get("tempo_bpm", 120)
    
    resolution = score_json.get("resolution", {})
    steps_per_beat = resolution.get("steps_per_beat", 4)
    
    tracks = score_json.get("tracks", [])
    events = score_json.get("events", [])
    
    # Crear mapeo de tracks a canales MIDI
    if midi_channel_map is None:
        midi_channel_map = {}
        for i, track in enumerate(tracks):
            track_id = track.get("id")
            # Canal 9 (10 en 1-indexed) es para drums
            if track.get("role") == "drums":
                midi_channel_map[track_id] = 9
            else:
                channel = i if i < 9 else i + 1  # Saltar canal 9
                midi_channel_map[track_id] = min(channel, 15)
    
    # Crear MIDI
    midi = MIDIFile(len(tracks))
    
    # Configurar tracks
    track_to_index = {}
    for i, track in enumerate(tracks):
        track_id = track.get("id")
        track_to_index[track_id] = i
        
        midi.addTempo(i, 0, tempo_bpm)
        midi.addTrackName(i, 0, track_id)
        
        program = track.get("program", 0)
        channel = midi_channel_map.get(track_id, i)
        midi.addProgramChange(i, channel, 0, program)
    
    # Agregar eventos
    for event in events:
        track_id = event.get("track")
        if track_id not in track_to_index:
            continue
        
        track_index = track_to_index[track_id]
        channel = midi_channel_map.get(track_id, 0)
        
        pitch = event.get("pitch", 60)
        velocity = event.get("velocity", 100)
        start_step = event.get("start_step", 0)
        dur_steps = event.get("dur_steps", 1)
        
        # Convertir steps a beats
        time_beats = start_step / steps_per_beat
        duration_beats = dur_steps / steps_per_beat
        
        midi.addNote(
            track=track_index,
            channel=channel,
            pitch=pitch,
            time=time_beats,
            duration=duration_beats,
            volume=velocity,
        )
    
    # Escribir archivo
    try:
        os.makedirs(os.path.dirname(out_mid_path) or ".", exist_ok=True)
        with open(out_mid_path, "wb") as f:
            midi.writeFile(f)
        
        return {
            "success": True,
            "path": out_mid_path,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "path": None,
            "error": str(e),
        }


def midi_to_wav_fluidsynth(
    mid_path: str,
    soundfont_path: str,
    out_wav_path: str,
    sample_rate: int = 44100,
    gain: float = 0.7,
    overwrite: bool = True,
) -> Dict[str, Any]:
    """
    Renderiza MIDI a WAV usando FluidSynth
    
    Args:
        mid_path: Ruta del archivo MIDI
        soundfont_path: Ruta del SoundFont .sf2
        out_wav_path: Ruta de salida WAV
        sample_rate: Tasa de muestreo
        gain: Ganancia (0.0 - 5.0)
        overwrite: Sobrescribir si existe
        
    Returns:
        Dict con 'success', 'path', 'error'
    """
    # Verificar archivos
    if not os.path.exists(mid_path):
        return {"success": False, "path": None, "error": f"MIDI no encontrado: {mid_path}"}
    
    if not os.path.exists(soundfont_path):
        return {"success": False, "path": None, "error": f"SoundFont no encontrado: {soundfont_path}"}
    
    if os.path.exists(out_wav_path) and not overwrite:
        return {"success": False, "path": None, "error": f"Archivo existe: {out_wav_path}"}
    
    # Verificar fluidsynth
    try:
        result = subprocess.run(
            ["which", "fluidsynth"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return {"success": False, "path": None, "error": "fluidsynth no instalado"}
    except Exception:
        return {"success": False, "path": None, "error": "No se puede verificar fluidsynth"}
    
    # Ejecutar fluidsynth
    cmd = [
        "fluidsynth",
        "-ni",
        "-g", str(gain),
        "-r", str(sample_rate),
        "-F", out_wav_path,
        soundfont_path,
        mid_path,
    ]
    
    try:
        os.makedirs(os.path.dirname(out_wav_path) or ".", exist_ok=True)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "path": None,
                "error": f"fluidsynth error: {result.stderr}",
            }
        
        return {
            "success": True,
            "path": out_wav_path,
            "error": None,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "path": None, "error": "Timeout renderizando audio"}
    except Exception as e:
        return {"success": False, "path": None, "error": str(e)}


def play_audio(
    audio_path: str,
    backend: str = "auto",
    blocking: bool = False,
    volume: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Reproduce un archivo de audio
    
    Args:
        audio_path: Ruta al archivo WAV/MP3/OGG
        backend: Backend a usar (auto, ffplay, aplay, paplay, vlc)
        blocking: Si esperar a que termine
        volume: Volumen opcional
        
    Returns:
        Dict con 'success', 'backend_used', 'error'
    """
    if not os.path.exists(audio_path):
        return {"success": False, "backend_used": None, "error": f"Archivo no encontrado: {audio_path}"}
    
    backends = ["ffplay", "paplay", "aplay", "vlc"] if backend == "auto" else [backend]
    
    for be in backends:
        try:
            result = subprocess.run(["which", be], capture_output=True)
            if result.returncode != 0:
                continue
            
            # Construir comando
            if be == "ffplay":
                cmd = ["ffplay", "-nodisp", "-autoexit", audio_path]
                if volume is not None:
                    cmd.extend(["-volume", str(int(volume * 100))])
            elif be == "paplay":
                cmd = ["paplay", audio_path]
                if volume is not None:
                    cmd.extend(["--volume", str(int(volume * 65536))])
            elif be == "aplay":
                cmd = ["aplay", audio_path]
            elif be == "vlc":
                cmd = ["cvlc", "--play-and-exit", audio_path]
            else:
                continue
            
            if blocking:
                result = subprocess.run(cmd, capture_output=True)
            else:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            return {
                "success": True,
                "backend_used": be,
                "error": None,
            }
        except Exception as e:
            continue
    
    return {
        "success": False,
        "backend_used": None,
        "error": f"Ningún backend disponible: {backends}",
    }


def score_v1_pipeline_listen(
    score_json: Dict[str, Any],
    soundfont_path: str,
    out_mid_path: str = "./out.mid",
    out_wav_path: str = "./out.wav",
    sample_rate: int = 44100,
    backend: str = "auto",
    blocking: bool = False,
    constraints_json: Optional[Dict[str, Any]] = None,
    strict: bool = True,
) -> Dict[str, Any]:
    """
    Pipeline end-to-end: valida, MIDI, WAV, reproduce
    
    Args:
        score_json: Score v1
        soundfont_path: Ruta al SoundFont
        out_mid_path: Ruta MIDI salida
        out_wav_path: Ruta WAV salida
        sample_rate: Tasa de muestreo
        backend: Backend de audio
        blocking: Esperar reproducción
        constraints_json: Constraints opcional
        strict: Modo estricto
        
    Returns:
        Dict con resultado de cada paso
    """
    result = {
        "validation": None,
        "midi": None,
        "wav": None,
        "playback": None,
        "success": False,
    }
    
    # 1. Validar
    validation = validate_score_v1(score_json, constraints_json, strict)
    result["validation"] = validation
    
    if not validation["valid"]:
        return result
    
    # 2. Convertir a MIDI
    midi_result = score_v1_to_midi(score_json, out_mid_path)
    result["midi"] = midi_result
    
    if not midi_result["success"]:
        return result
    
    # 3. Renderizar WAV
    wav_result = midi_to_wav_fluidsynth(
        out_mid_path, soundfont_path, out_wav_path, sample_rate
    )
    result["wav"] = wav_result
    
    if not wav_result["success"]:
        return result
    
    # 4. Reproducir
    play_result = play_audio(out_wav_path, backend, blocking)
    result["playback"] = play_result
    result["success"] = play_result["success"]
    
    return result
