"""
Implementación de agente específico para DeepSeek
"""
from agents.base_agent import BaseAgent
from src.agent import create_deepseek_agent as create_agent


class DeepseekAgent(BaseAgent):
    """Agente implementado con DeepSeek"""
    
    def __init__(self, name: str = "DeepSeek Agent", description: str = "Agente inteligente basado en DeepSeek"):
        """
        Inicializa el agente DeepSeek
        
        Args:
            name: Nombre del agente
            description: Descripción del agente
        """
        super().__init__(name, description)
        self.agent = None
        self._initialize_agent()
    
    def _initialize_agent(self) -> None:
        """Inicializa la instancia del agente"""
        self.agent = create_agent(tools=self.tools)
    
    def run(self, query: str) -> str:
        """
        Ejecuta una consulta con el agente
        
        Args:
            query: Consulta a ejecutar
            
        Returns:
            str: Respuesta del agente
        """
        if self.agent is None:
            raise RuntimeError("Agente no inicializado")
        
        response = self.agent.run(query)
        return response
    
    def add_tool(self, tool) -> None:
        """
        Agrega una herramienta y reinicializa el agente
        
        Args:
            tool: Herramienta a agregar
        """
        super().add_tool(tool)
        self._initialize_agent()
