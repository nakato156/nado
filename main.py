"""
NADO - Sistema de Composición Musical 8-bit con Agentes
Punto de entrada principal
"""
import sys
sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

import os
import json
import subprocess
from pathlib import Path

from agents.orchestrator import Orchestrator
from tools.score_tools import score_v1_to_midi, midi_to_wav_fluidsynth


# ============================================================================
# Configuración de salida
# ============================================================================
OUTPUT_DIR = Path("/home/chris/Documentos/Percep3/nado/out")

# SoundFonts conocidos (buscar en orden de preferencia)
SOUNDFONT_PATHS = [
    "/home/chris/Documentos/Percep3/nado/soundfonts/8bit.sf2",
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
    """Convierte WAV a MP3 usando ffmpeg"""
    if not os.path.exists(wav_path):
        return {"success": False, "error": f"WAV no encontrado: {wav_path}"}
    
    cmd = ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "2", mp3_path]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return {"success": False, "error": f"ffmpeg error: {result.stderr[:200]}"}
        return {"success": True, "path": mp3_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def export_full_pipeline(score_dict: dict, title: str, soundfont_path: str | None) -> dict:
    """Pipeline completo: Score → JSON → MIDI → WAV → MP3"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sanitizar nombre
    safe_title = "".join(c if c.isalnum() or c in "._- " else "_" for c in title)
    safe_title = safe_title.replace(" ", "_")
    
    results = {"json_path": None, "midi_path": None, "wav_path": None, "mp3_path": None, "errors": []}
    
    # 1. JSON
    json_path = OUTPUT_DIR / f"{safe_title}.json"
    print(f"\n📝 Guardando JSON: {json_path}")
    try:
        with open(json_path, "w") as f:
            json.dump(score_dict, f, indent=2)
        results["json_path"] = str(json_path)
        print("   ✅ JSON guardado")
    except Exception as e:
        results["errors"].append(f"Error JSON: {e}")
        print(f"   ❌ Error: {e}")
    
    # 2. MIDI
    midi_path = OUTPUT_DIR / f"{safe_title}.mid"
    print(f"\n🎹 Exportando MIDI: {midi_path}")
    midi_result = score_v1_to_midi(score_dict, str(midi_path), overwrite=True)
    if midi_result.get("success"):
        results["midi_path"] = str(midi_path)
        print("   ✅ MIDI exportado")
    else:
        results["errors"].append(f"Error MIDI: {midi_result.get('error')}")
        print(f"   ❌ Error: {midi_result.get('error')}")
        return results
    
    # 3. WAV (solo si hay soundfont)
    if not soundfont_path:
        results["errors"].append("SoundFont no disponible - sin audio")
        print("\n⚠️  SoundFont no disponible, saltando renderizado de audio")
        return results
    
    wav_path = OUTPUT_DIR / f"{safe_title}.wav"
    print(f"\n🔊 Renderizando WAV: {wav_path}")
    print(f"   SoundFont: {soundfont_path}")
    wav_result = midi_to_wav_fluidsynth(
        str(midi_path), soundfont_path, str(wav_path),
        sample_rate=44100, gain=0.8, overwrite=True
    )
    if wav_result.get("success"):
        results["wav_path"] = str(wav_path)
        print("   ✅ WAV renderizado")
    else:
        results["errors"].append(f"Error WAV: {wav_result.get('error')}")
        print(f"   ❌ Error: {wav_result.get('error')}")
        return results
    
    # 4. MP3
    mp3_path = OUTPUT_DIR / f"{safe_title}.mp3"
    print(f"\n🎧 Convirtiendo a MP3: {mp3_path}")
    mp3_result = wav_to_mp3(str(wav_path), str(mp3_path))
    if mp3_result.get("success"):
        results["mp3_path"] = str(mp3_path)
        print("   ✅ MP3 creado")
    else:
        results["errors"].append(f"Error MP3: {mp3_result.get('error')}")
        print(f"   ❌ Error: {mp3_result.get('error')}")
    
    return results


def main():
    """Función principal - Composición interactiva"""
    print("\n" + "=" * 60)
    print("🎮 NADO - Sistema de Composición Musical 8-bit")
    print("=" * 60)
    print("\nSistema multi-agente: PM, Musician, Researcher, Orchestrator")
    print("Wire Protocol: proposal.v1 → critic_report.v1 → score.v1\n")
    
    # Buscar soundfont al inicio
    soundfont_path = find_soundfont()
    if soundfont_path:
        print(f"🎸 SoundFont: {soundfont_path}")
    else:
        print("⚠️  SoundFont no encontrado - solo se generará JSON y MIDI")
    
    try:
        # Configuración
        print("\nConfiguración de composición:")
        print("-" * 40)
        
        title = input("Título [Adventure Theme]: ").strip() or "Adventure Theme"
        
        tempo_input = input("Tempo BPM [140]: ").strip()
        tempo = int(tempo_input) if tempo_input else 140
        
        key = input("Tonalidad [C]: ").strip() or "C"
        
        bars_input = input("Compases [8]: ").strip()
        bars = int(bars_input) if bars_input else 8
        
        use_llm_input = input("Usar LLM para composición? [s/N]: ").strip().lower()
        use_llm = use_llm_input in ['s', 'si', 'y', 'yes']
        
        print("\n" + "-" * 40)
        print(f"Título: {title}")
        print(f"Tempo: {tempo} BPM")
        print(f"Key: {key}")
        print(f"Compases: {bars}")
        print(f"LLM: {'Sí' if use_llm else 'No (algorítmico)'}")
        print("-" * 40 + "\n")
        
        confirm = input("¿Iniciar composición? [S/n]: ").strip().lower()
        if confirm in ['n', 'no']:
            print("Composición cancelada.")
            return
        
        # Inicializar orchestrator
        print("\n🎵 Inicializando sistema de agentes...")
        orchestrator = Orchestrator(use_llm=use_llm)
        
        # Componer
        print("🎹 Componiendo...\n")
        score = orchestrator.compose(
            title=title,
            tempo_bpm=tempo,
            key=key,
            length_bars=bars,
            num_variants=3,
        )
        
        # Resultados
        print("\n" + "=" * 60)
        print("📊 RESULTADO FINAL")
        print("=" * 60)
        print(f"Título: {score.metadata.title}")
        print(f"Tempo: {score.metadata.tempo_bpm} BPM")
        print(f"Key: {score.metadata.key}")
        print(f"Compases: {score.metadata.length_bars}")
        print(f"Total eventos: {len(score.events)}")
        
        # Distribución por track
        track_counts = {}
        for event in score.events:
            track_counts[event.track] = track_counts.get(event.track, 0) + 1
        
        print("\nEventos por track:")
        for track, count in sorted(track_counts.items()):
            print(f"  {track}: {count}")
        
        # Exportar
        print("\n" + "=" * 60)
        print("📦 EXPORTACIÓN")
        print("=" * 60)
        
        export_choice = input("¿Exportar archivos? [S/n]: ").strip().lower()
        if export_choice not in ['n', 'no']:
            # Convertir score a dict
            score_dict = orchestrator.export_to_dict()
            
            # Pipeline completo
            export_results = export_full_pipeline(score_dict, title, soundfont_path)
            
            # Resumen
            print("\n" + "=" * 60)
            print("📋 Archivos generados:")
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
                print(f"\n   🎉 ¡Escucha tu canción en: {export_results['mp3_path']}")
            
            if export_results.get("errors"):
                print("\n   ⚠️  Advertencias:")
                for err in export_results["errors"]:
                    print(f"      - {err}")
        
        print("\n" + "=" * 60)
        print("🎮 ¡Composición completada!")
        print("=" * 60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n👋 ¡Hasta luego!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\nAsegúrate de que:")
        print("1. Tienes configurada DEEPSEEK_API_KEY en .env")
        print("2. Las dependencias están instaladas (pip install -r requirements.txt)")
        print("3. fluidsynth y ffmpeg están instalados para audio")


if __name__ == "__main__":
    main()
