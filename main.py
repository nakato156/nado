"""
NADO - Sistema de Composición Musical 8-bit con Agentes
Punto de entrada principal
"""
import sys
sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

from agents.orchestrator import Orchestrator


def main():
    """Función principal - Composición interactiva"""
    print("\n" + "=" * 60)
    print("🎮 NADO - Sistema de Composición Musical 8-bit")
    print("=" * 60)
    print("\nSistema multi-agente: PM, Musician, Researcher, Orchestrator")
    print("Wire Protocol: proposal.v1 → critic_report.v1 → score.v1\n")
    
    try:
        # Configuración
        print("Configuración de composición:")
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
        print("\n" + "-" * 40)
        export = input("¿Exportar a JSON? [S/n]: ").strip().lower()
        if export not in ['n', 'no']:
            filename = input(f"Nombre archivo [{title.replace(' ', '_')}.json]: ").strip()
            if not filename:
                filename = f"{title.replace(' ', '_')}.json"
            if not filename.endswith('.json'):
                filename += '.json'
            
            filepath = f"/home/chris/Documentos/Percep3/nado/{filename}"
            orchestrator.export_to_json(filepath)
            print(f"✅ Exportado: {filepath}")
        
        print("\n" + "=" * 60)
        print("🎮 ¡Composición completada!")
        print("=" * 60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n👋 ¡Hasta luego!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nAsegúrate de que:")
        print("1. Tienes configurada DEEPSEEK_API_KEY en .env")
        print("2. Las dependencias están instaladas")


if __name__ == "__main__":
    main()
