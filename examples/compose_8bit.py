"""
Ejemplo de composición usando el sistema de agentes
"""
import sys
import json
sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

from agents.orchestrator import Orchestrator


def main():
    """Ejemplo de composición 8-bit"""
    print("\n" + "=" * 60)
    print("🎮 NADO - Sistema de Composición Musical 8-bit con Agentes")
    print("=" * 60 + "\n")
    
    # Crear orchestrator
    print("Inicializando sistema de agentes...")
    orchestrator = Orchestrator(use_llm=True)
    
    # Componer
    print("\n🎵 Iniciando composición...\n")
    
    score = orchestrator.compose(
        title="Adventure Theme",
        tempo_bpm=140,
        key="C",
        length_bars=4,  # Empezar con 4 compases para demo
        num_variants=3,
    )
    
    # Mostrar resultados
    print("\n📊 Score generado:")
    print(f"   Título: {score.metadata.title}")
    print(f"   Tempo: {score.metadata.tempo_bpm} BPM")
    print(f"   Key: {score.metadata.key}")
    print(f"   Compases: {score.metadata.length_bars}")
    print(f"   Total eventos: {len(score.events)}")
    
    # Mostrar algunos eventos
    print("\n🎹 Primeros eventos:")
    for event in score.events[:10]:
        print(f"   [{event.track}] pitch={event.pitch}, vel={event.velocity}, "
              f"step={event.start_step}, dur={event.dur_steps}")
    
    if len(score.events) > 10:
        print(f"   ... y {len(score.events) - 10} eventos más")
    
    # Exportar a JSON
    output_path = "/home/chris/Documentos/Percep3/nado/output_score.json"
    orchestrator.export_to_json(output_path)
    print(f"\n💾 Score exportado a: {output_path}")
    
    print("\n" + "=" * 60)
    print("✅ Composición completada")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
