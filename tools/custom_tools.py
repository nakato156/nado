"""
Herramientas personalizadas para los agentes
"""
from langchain.tools import Tool
from typing import Callable


def create_custom_tool(
    name: str,
    func: Callable,
    description: str,
) -> Tool:
    """
    Crea una herramienta personalizada para los agentes
    
    Args:
        name: Nombre de la herramienta
        func: Función a ejecutar
        description: Descripción de la herramienta
        
    Returns:
        Tool: Herramienta creada
    """
    return Tool(
        name=name,
        func=func,
        description=description,
    )


# Ejemplos de herramientas simples

def search_web(query: str) -> str:
    """
    Herramienta ejemplo para buscar en la web
    
    Args:
        query: Consulta de búsqueda
        
    Returns:
        str: Resultados de búsqueda
    """
    return f"Resultados de búsqueda para: {query}"


def get_current_weather(location: str) -> str:
    """
    Herramienta ejemplo para obtener el clima
    
    Args:
        location: Ubicación
        
    Returns:
        str: Información del clima
    """
    return f"Clima en {location}: 20°C, soleado"


# Crear herramientas
search_tool = create_custom_tool(
    name="Search Web",
    func=search_web,
    description="Útil para buscar información en la web",
)

weather_tool = create_custom_tool(
    name="Get Weather",
    func=get_current_weather,
    description="Obtiene el clima actual de una ubicación",
)
