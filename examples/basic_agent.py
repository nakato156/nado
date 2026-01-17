"""
Ejemplo básico de uso de un agente con DeepSeek
"""
import sys
sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

from agents.deepseek_agent import DeepseekAgent
from tools.custom_tools import search_tool, weather_tool


def main():
    """Función principal"""
    
    # Crear un agente
    agent = DeepseekAgent(
        name="Asistente Principal",
        description="Asistente inteligente con DeepSeek"
    )
    
    # Agregar herramientas (opcional)
    # agent.add_tool(search_tool)
    # agent.add_tool(weather_tool)
    
    # Ejecutar una consulta
    print("=" * 50)
    print("Agente DeepSeek - Ejemplo Básico")
    print("=" * 50)
    
    query = "¿Cuál es la capital de Francia?"
    print(f"\nConsulta: {query}\n")
    
    try:
        response = agent.run(query)
        print(f"Respuesta: {response}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    main()
