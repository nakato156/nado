#!/usr/bin/env python3
"""
Demo del Composer Agent con Tool Calling
Genera música 8-bit, exporta MIDI y convierte a MP3
"""
import sys
sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

import json
import os
import subprocess
from pathlib import Path
from agents.composer_agent import ComposerAgent
from models.constraints import ConstraintsV1
from tools.score_tools import score_v1_to_midi, midi_to_wav_fluidsynth


# ============================================================================
# Configuración
# ============================================================================
OUTPUT_DIR = Path("/home/chris/Documentos/Percep3/nado/out")

# SoundFonts conocidos (buscar en orden de preferencia)
SOUNDFONT_PATHS = [
    "/home/chris/Documentos/Percep3/nado/soundfonts/8bit.sf2",  # Custom 8-bit
    "/snap/libreoffice/365/usr/share/sounds/sf2/TimGM6mb.sf2",
    "/snap/libreoffice/362/usr/share/sounds/sf2/TimGM6mb.sf2",
    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    "/usr/share/soundfonts/FluidR3_GM.sf2",
]


def find_soundfont() -> str | None:
    """Busca un soundfont disponible en el sistema"""
    for sf_path in SOUNDFONT_PATHS:
        if os.path.exists(sf_path):
            return sf_path
    return None


def wav_to_mp3(wav_path: str, mp3_path: str) -> dict:
    """
    Convierte WAV a MP3 usando ffmpeg
    
    Args:
        wav_path: Ruta del archivo WAV
        mp3_path: Ruta de salida MP3
        
    Returns:
        Dict con 'success', 'path', 'error'
    """
    print(f"   🔄 Convirtiendo WAV → MP3...")
    
    if not os.path.exists(wav_path):
        return {"success": False, "path": None, "error": f"WAV no encontrado: {wav_path}"}
    
    # Verificar ffmpeg
    try:
        result = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
        if result.returncode != 0:
            return {"success": False, "path": None, "error": "ffmpeg no instalado. Ejecuta: sudo apt install ffmpeg"}
    except Exception:
        return {"success": False, "path": None, "error": "No se puede verificar ffmpeg"}
    
    # Convertir con ffmpeg
    cmd = [
        "ffmpeg",
        "-y",  # Sobrescribir
        "-i", wav_path,
        "-codec:a", "libmp3lame",
        "-qscale:a", "2",  # Alta calidad
        mp3_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            return {"success": False, "path": None, "error": f"ffmpeg falló: {result.stderr[:200]}"}
        
        return {"success": True, "path": mp3_path, "error": None}
        
    except subprocess.TimeoutExpired:
        return {"success": False, "path": None, "error": "Timeout al convertir a MP3"}
    except Exception as e:
        return {"success": False, "path": None, "error": str(e)}


def export_full_pipeline(score: dict, title: str, soundfont_path: str) -> dict:
    """
    Pipeline completo: Score → MIDI → WAV → MP3
    
    Args:
        score: Score JSON
        title: Nombre base para los archivos
        soundfont_path: Ruta al soundfont
        
    Returns:
        Dict con rutas de los archivos generados
    """
    # Crear directorio de salida
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sanitizar nombre
    safe_title = "".join(c if c.isalnum() or c in "._- " else "_" for c in title)
    safe_title = safe_title.replace(" ", "_")
    
    results = {
        "json_path": None,
        "midi_path": None,
        "wav_path": None,
        "mp3_path": None,
        "errors": []
    }
    
    # 1. Guardar JSON
    json_path = OUTPUT_DIR / f"{safe_title}.json"
    print(f"\n📝 Guardando JSON: {json_path}")
    try:
        with open(json_path, "w") as f:
            json.dump(score, f, indent=2)
        results["json_path"] = str(json_path)
        print(f"   ✅ JSON guardado")
    except Exception as e:
        results["errors"].append(f"Error guardando JSON: {e}")
        print(f"   ❌ Error: {e}")
    
    # 2. Exportar MIDI
    midi_path = OUTPUT_DIR / f"{safe_title}.mid"
    print(f"\n🎹 Exportando MIDI: {midi_path}")
    midi_result = score_v1_to_midi(score, str(midi_path), overwrite=True)
    if midi_result.get("success"):
        results["midi_path"] = str(midi_path)
        print(f"   ✅ MIDI exportado")
    else:
        results["errors"].append(f"Error MIDI: {midi_result.get('error')}")
        print(f"   ❌ Error: {midi_result.get('error')}")
        return results  # No podemos continuar sin MIDI
    
    # 3. Renderizar WAV
    wav_path = OUTPUT_DIR / f"{safe_title}.wav"
    print(f"\n🔊 Renderizando WAV: {wav_path}")
    print(f"   SoundFont: {soundfont_path}")
    wav_result = midi_to_wav_fluidsynth(
        str(midi_path),
        soundfont_path,
        str(wav_path),
        sample_rate=44100,
        gain=0.8,
        overwrite=True
    )
    if wav_result.get("success"):
        results["wav_path"] = str(wav_path)
        print(f"   ✅ WAV renderizado")
    else:
        results["errors"].append(f"Error WAV: {wav_result.get('error')}")
        print(f"   ❌ Error: {wav_result.get('error')}")
        return results  # No podemos continuar sin WAV
    
    # 4. Convertir a MP3
    mp3_path = OUTPUT_DIR / f"{safe_title}.mp3"
    print(f"\n🎧 Convirtiendo a MP3: {mp3_path}")
    mp3_result = wav_to_mp3(str(wav_path), str(mp3_path))
    if mp3_result.get("success"):
        results["mp3_path"] = str(mp3_path)
        print(f"   ✅ MP3 creado")
    else:
        results["errors"].append(f"Error MP3: {mp3_result.get('error')}")
        print(f"   ❌ Error: {mp3_result.get('error')}")
    
    return results


def main():
    print("=" * 60)
    print("🎵 Demo: Composer Agent con Tool Calling")
    print("=" * 60)
    
    # Buscar soundfont
    soundfont_path = find_soundfont()
    if soundfont_path:
        print(f"\n🎸 SoundFont encontrado: {soundfont_path}")
    else:
        print("\n⚠️  No se encontró SoundFont. Solo se generará JSON y MIDI.")
        print("   Para audio, instala un soundfont o coloca uno en soundfonts/8bit.sf2")
    
    # Crear constraints 8-bit
    constraints = ConstraintsV1.default_8bit()
    
    # Crear composer
    composer = ComposerAgent(
        soundfont_path=soundfont_path,
        constraints=constraints,
        enable_tools=True,
        verbose=True,
    )
    
    print("\n📝 Solicitando composición...\n")
    
    # Pedir una composición simple
    score = composer.compose(
        description="Una melodía alegre y energética estilo 8-bit NES con ritmo pegajoso",
        title="Demo_8bit_Song",
        tempo_bpm=140,
        key="C",
        length_bars=4,
        auto_validate=True,
        auto_listen=False,
    )
    
    if score:
        print("\n" + "=" * 60)
        print("✅ Score generado:")
        print("-" * 40)
        title = score.get('metadata', {}).get('title', 'Demo_8bit_Song')
        print(f"  Title: {title}")
        print(f"  Tempo: {score.get('metadata', {}).get('tempo_bpm', '?')} BPM")
        print(f"  Tracks: {len(score.get('tracks', []))}")
        print(f"  Events: {len(score.get('events', []))}")
        
        # Validar manualmente
        print("\n🔍 Validación:")
        result = composer.validate_current()
        if result.get("valid"):
            print("  ✅ Score válido!")
        else:
            print("  ❌ Errores:")
            for err in result.get("errors", []):
                print(f"     - {err}")
        
        # Pipeline de exportación completo
        print("\n" + "=" * 60)
        print("📦 Exportando archivos...")
        print("=" * 60)
        
        if soundfont_path:
            export_results = export_full_pipeline(score, title, soundfont_path)
        else:
            # Solo JSON y MIDI si no hay soundfont
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            safe_title = title.replace(" ", "_")
            
            # JSON
            json_path = OUTPUT_DIR / f"{safe_title}.json"
            with open(json_path, "w") as f:
                json.dump(score, f, indent=2)
            print(f"\n📝 JSON: {json_path}")
            
            # MIDI
            midi_path = OUTPUT_DIR / f"{safe_title}.mid"
            midi_result = score_v1_to_midi(score, str(midi_path), overwrite=True)
            if midi_result.get("success"):
                print(f"🎹 MIDI: {midi_path}")
            
            export_results = {
                "json_path": str(json_path),
                "midi_path": str(midi_path) if midi_result.get("success") else None,
                "wav_path": None,
                "mp3_path": None,
                "errors": ["SoundFont no disponible para renderizar audio"]
            }
        
        # Resumen final
        print("\n" + "=" * 60)
        print("📋 Resumen de archivos generados:")
        print("=" * 60)
        print(f"   📁 Directorio: {OUTPUT_DIR}")
        if export_results.get("json_path"):
            print(f"   📄 JSON: {Path(export_results['json_path']).name}")
        if export_results.get("midi_path"):
            print(f"   🎹 MIDI: {Path(export_results['midi_path']).name}")
        if export_results.get("wav_path"):
            print(f"   🔊 WAV:  {Path(export_results['wav_path']).name}")
        if export_results.get("mp3_path"):
            print(f"   🎧 MP3:  {Path(export_results['mp3_path']).name}")
            print(f"\n   🎉 ¡Puedes escuchar tu canción en: {export_results['mp3_path']}")
        
        if export_results.get("errors"):
            print("\n   ⚠️  Advertencias:")
            for err in export_results["errors"]:
                print(f"      - {err}")
    else:
        print("\n❌ No se pudo generar el score")
        print("   Última respuesta del agente:")
        if composer.messages:
            last = composer.messages[-1]
            print(f"   {last.content[:500] if hasattr(last, 'content') else str(last)[:500]}")


def demo_interactive():
    """Demo interactivo con el compositor"""
    print("=" * 60)
    print("🎮 Modo Interactivo - Composer Agent")
    print("=" * 60)
    print("Comandos: 'exit' para salir, 'clear' para limpiar")
    print()
    
    composer = ComposerAgent(
        constraints=ConstraintsV1.default_8bit(),
        enable_tools=True,
        verbose=True,
    )
    
    while True:
        try:
            user_input = input("🎹 Tú: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'exit':
                print("👋 ¡Hasta luego!")
                break
            
            if user_input.lower() == 'clear':
                composer.clear_history()
                print("🧹 Historial limpiado")
                continue
            
            print("\n🤖 Compositor:")
            response = composer.run(user_input)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Modo interactivo")
    args = parser.parse_args()
    
    if args.interactive:
        demo_interactive()
    else:
        main()
