"""
Punto de entrada principal de la aplicación
"""
import sys
sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

from agents.deepseek_agent import DeepseekAgent


def main():
    """Función principal"""
    print("\n" + "="*60)
    print("Proyecto de Agentes con LangChain y DeepSeek")
    print("="*60 + "\n")
    
    try:
        # Crear agente
        print("Inicializando agente...")
        agent = DeepseekAgent(
            name="Asistente Inteligente",
            description="Agente potenciado por DeepSeek"
        )
        print(f"✓ Agente creado: {agent.name}")
        print(f"  Descripción: {agent.description}\n")
        
        # Ejemplo interactivo
        print("Escribe 'salir' para terminar\n")
        
        while True:
            query = input("Tu pregunta: ").strip()
            
            if query.lower() in ['salir', 'exit', 'quit']:
                print("\n¡Hasta luego!")
                break
            
            if not query:
                continue
            
            print("\nProcesando...")
            try:
                response = agent.run(query)
                print(f"\nRespuesta:\n{response}\n")
            except Exception as e:
                print(f"Error al procesar: {e}\n")
    
    except Exception as e:
        print(f"Error al inicializar: {e}")
        print("\nAsegúrate de que:")
        print("1. Tienes una API key de DeepSeek válida")
        print("2. La variable DEEPSEEK_API_KEY está configurada en .env")


if __name__ == "__main__":
    main()
