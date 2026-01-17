"""
Módulo principal para crear y gestionar agentes con LangChain y DeepSeek
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    MODEL_NAME,
    TEMPERATURE,
    MAX_TOKENS,
)


def create_deepseek_llm():
    """
    Crea una instancia del modelo de lenguaje DeepSeek
    
    Returns:
        ChatOpenAI: Instancia configurada del modelo
    """
    llm = ChatOpenAI(
        openai_api_key=DEEPSEEK_API_KEY,
        openai_api_base=DEEPSEEK_BASE_URL,
        model_name=MODEL_NAME,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
    )
    return llm


class SimpleAgent:
    """Agente simple usando LangChain con DeepSeek"""
    
    def __init__(self, system_prompt: str = None):
        """
        Inicializa el agente
        
        Args:
            system_prompt: Prompt del sistema opcional
        """
        self.llm = create_deepseek_llm()
        self.system_prompt = system_prompt or "Eres un asistente útil e inteligente."
        self.conversation_history = []
    
    def run(self, query: str) -> str:
        """
        Ejecuta una consulta
        
        Args:
            query: Consulta a ejecutar
            
        Returns:
            str: Respuesta del agente
        """
        messages = [
            SystemMessage(content=self.system_prompt),
            *self.conversation_history,
            HumanMessage(content=query),
        ]
        
        response = self.llm.invoke(messages)
        
        # Guardar en historial
        self.conversation_history.append(HumanMessage(content=query))
        self.conversation_history.append(response)
        
        return response.content
    
    def clear_history(self):
        """Limpia el historial de conversación"""
        self.conversation_history = []


def create_deepseek_agent(tools: list = None, agent_type: str = None):
    """
    Crea un agente con LangChain usando DeepSeek como LLM
    
    Args:
        tools: Lista de herramientas disponibles para el agente (no usado en esta versión simple)
        agent_type: Tipo de agente a usar (no usado en esta versión simple)
        
    Returns:
        SimpleAgent: Agente configurado y listo para usar
    """
    return SimpleAgent()


def run_agent_query(agent, query: str) -> str:
    """
    Ejecuta una consulta en el agente
    
    Args:
        agent: Instancia del agente
        query: Consulta a ejecutar
        
    Returns:
        str: Respuesta del agente
    """
    response = agent.run(query)
    return response
