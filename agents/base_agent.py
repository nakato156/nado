"""
Clase base para agentes
"""
from abc import ABC, abstractmethod
from typing import Any, List


class BaseAgent(ABC):
    """Clase base para todos los agentes"""
    
    def __init__(self, name: str, description: str):
        """
        Inicializa el agente base
        
        Args:
            name: Nombre del agente
            description: Descripción del agente
        """
        self.name = name
        self.description = description
        self.tools = []
    
    @abstractmethod
    def run(self, query: str) -> str:
        """
        Ejecuta una consulta
        
        Args:
            query: Consulta a ejecutar
            
        Returns:
            str: Respuesta del agente
        """
        pass
    
    def add_tool(self, tool: Any) -> None:
        """
        Agrega una herramienta al agente
        
        Args:
            tool: Herramienta a agregar
        """
        self.tools.append(tool)
    
    def get_tools(self) -> List[Any]:
        """
        Obtiene las herramientas disponibles
        
        Returns:
            List[Any]: Lista de herramientas
        """
        return self.tools
