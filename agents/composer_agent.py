"""
Composer Agent con Tool Calling
Genera scores y puede validar/escuchar usando tools
"""
import sys
sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

import json
from typing import List, Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agents.base_agent import BaseAgent
from models.score import ScoreV1
from models.constraints import ConstraintsV1
from tools.langchain_tools import get_all_score_tools, get_composition_tools
from config.settings import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    MODEL_NAME,
    TEMPERATURE,
)


class ComposerAgent(BaseAgent):
    """
    Composer Agent con Tool Calling
    
    Genera scores JSON y puede:
    - Validar scores con validate_score_v1
    - Convertir a MIDI con score_v1_to_midi
    - Renderizar y reproducir con score_v1_pipeline_listen
    """
    
    VERSION = "2.0.0"
    
    def __init__(
        self,
        soundfont_path: Optional[str] = None,
        constraints: Optional[ConstraintsV1] = None,
        enable_tools: bool = True,
        verbose: bool = True,
    ):
        super().__init__(
            name="Composer Agent",
            description="Compositor con Tool Calling para generar y validar música 8-bit"
        )
        
        self.soundfont_path = soundfont_path
        self.constraints = constraints or ConstraintsV1.default_8bit()
        self.verbose = verbose
        
        # Crear LLM con tool calling
        self.llm = ChatOpenAI(
            openai_api_key=DEEPSEEK_API_KEY,
            openai_api_base=DEEPSEEK_BASE_URL,
            model_name=MODEL_NAME,
            temperature=TEMPERATURE,
        )
        
        # Configurar tools
        if enable_tools:
            self.tools = get_all_score_tools()
            self.llm_with_tools = self.llm.bind_tools(self.tools)
        else:
            self.tools = []
            self.llm_with_tools = self.llm
        
        # Historial de mensajes
        self.messages: List[Any] = []
        
        # Score actual
        self.current_score: Optional[Dict[str, Any]] = None
    
    def _get_system_prompt(self) -> str:
        constraints_info = ""
        if self.constraints:
            c = self.constraints
            pulse1_range = c.hard.pitch_ranges.get("pulse1")
            triangle_range = c.hard.pitch_ranges.get("triangle")
            pulse1_min = pulse1_range.min if pulse1_range else 48
            pulse1_max = pulse1_range.max if pulse1_range else 96
            triangle_min = triangle_range.min if triangle_range else 24
            triangle_max = triangle_range.max if triangle_range else 60
            constraints_info = f"""
Constraints activos:
- Tracks requeridos: {', '.join(c.hard.required_tracks)}
- Tracks monofónicos: {', '.join(c.hard.monophonic_tracks)}
- Max eventos por compás: {c.hard.max_events_per_bar}
- Velocity levels: {c.hard.velocity_levels}
- Pitch ranges:
  - pulse1/pulse2: {pulse1_min}-{pulse1_max}
  - triangle: {triangle_min}-{triangle_max}
"""
        
        soundfont_info = ""
        if self.soundfont_path:
            soundfont_info = f"\nSoundFont disponible: {self.soundfont_path}"
        
        return f"""Eres un compositor de música 8-bit estilo NES/Famicom. Tu respuesta SIEMPRE debe incluir un JSON completo de score.v1.

{constraints_info}
{soundfont_info}

REGLAS CRÍTICAS:
1. NO expliques lo que vas a hacer. GENERA EL JSON DIRECTAMENTE.
2. Cada respuesta DEBE contener un bloque JSON válido con el score completo.
3. Si el usuario pide una canción, responde INMEDIATAMENTE con el JSON.

Formato score.v1:
```json
{{
  "schema_version": "score.v1",
  "metadata": {{"title": "...", "tempo_bpm": 140, "time_signature": "4/4", "key": "C", "length_bars": 4}},
  "resolution": {{"steps_per_beat": 4, "beats_per_bar": 4}},
  "tracks": [
    {{"id": "pulse1", "role": "melody", "monophonic": true, "program": 80}},
    {{"id": "triangle", "role": "bass", "monophonic": true, "program": 81}},
    {{"id": "noise", "role": "drums", "monophonic": true, "program": 118}}
  ],
  "events": [
    {{"type": "note", "track": "pulse1", "pitch": 60, "velocity": 100, "start_step": 0, "dur_steps": 4}}
  ]
}}
```

Herramientas disponibles:
- validate_score_v1: Valida el score
- score_v1_to_midi: Convierte a MIDI
- score_v1_pipeline_listen: Reproduce el audio

AHORA GENERA EL JSON DEL SCORE SOLICITADO.
"""
    
    def run(self, query: str) -> str:
        """
        Ejecuta una consulta con tool calling
        
        Args:
            query: Consulta del usuario
            
        Returns:
            Respuesta del agente
        """
        # Agregar mensaje del usuario
        self.messages.append(HumanMessage(content=query))
        
        max_iterations = 10
        for _ in range(max_iterations):
            # Construir mensajes para enviar (solo mensajes válidos)
            messages_to_send = [
                SystemMessage(content=self._get_system_prompt()),
                *self._get_valid_messages(),
            ]
            
            response = self.llm_with_tools.invoke(messages_to_send)
            
            # Si hay tool calls, procesarlos
            if response.tool_calls:
                # Guardar el mensaje del asistente
                self.messages.append(response)
                
                # Ejecutar TODAS las tool calls y agregar respuestas
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    if self.verbose:
                        print(f"🔧 Ejecutando tool: {tool_name}")
                    
                    tool_result = self._execute_tool(tool_name, tool_args)
                    
                    if self.verbose:
                        try:
                            result_data = json.loads(tool_result)
                            if "valid" in result_data:
                                status = "✅" if result_data["valid"] else "❌"
                                print(f"   {status} Validación: {result_data.get('valid')}")
                            elif "success" in result_data:
                                status = "✅" if result_data["success"] else "❌"
                                print(f"   {status} Success: {result_data.get('success')}")
                        except:
                            pass
                    
                    self.messages.append(ToolMessage(
                        content=tool_result,
                        tool_call_id=tool_call["id"],
                    ))
                
                # Continuar el loop para obtener la siguiente respuesta
                continue
            
            # No hay tool calls - es una respuesta final de texto
            content = response.content or ""
            
            # Intentar extraer score del response
            self._try_extract_score(content)
            
            # Si la respuesta está vacía o no tiene JSON, forzar generación
            if not self.current_score and (not content.strip() or '{' not in content):
                if self.verbose:
                    print("⚠️ Respuesta sin JSON, solicitando generación...")
                # Agregar un mensaje forzando la generación
                self.messages.append(HumanMessage(
                    content="GENERA EL JSON DEL SCORE AHORA. Solo el JSON, sin explicaciones."
                ))
                continue
            
            # Crear un AIMessage limpio sin tool_calls para guardar en historial
            clean_response = AIMessage(content=content)
            self.messages.append(clean_response)
            
            return content
        
        return "Error: Se alcanzó el límite de iteraciones"

    def _get_valid_messages(self) -> List[Any]:
        """Retorna solo mensajes válidos para enviar al LLM."""
        result: List[Any] = []
        i = 0
        while i < len(self.messages):
            msg = self.messages[i]
            
            # Si es un AIMessage con tool_calls, verificar que tenga todas las respuestas
            if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                tool_call_ids = [tc.get("id") for tc in msg.tool_calls if tc.get("id")]
                
                # Buscar los ToolMessages correspondientes
                tool_responses = []
                j = i + 1
                while j < len(self.messages) and isinstance(self.messages[j], ToolMessage):
                    tool_responses.append(self.messages[j])
                    j += 1
                
                # Verificar que tenemos respuestas para todos los tool_calls
                response_ids = {tm.tool_call_id for tm in tool_responses}
                if set(tool_call_ids).issubset(response_ids):
                    # Incluir el AIMessage y sus ToolMessages
                    result.append(msg)
                    result.extend(tool_responses)
                    i = j
                    continue
                else:
                    # Tool calls incompletos - saltar este mensaje y sus respuestas parciales
                    i = j
                    continue
            
            # Si es ToolMessage suelto, saltarlo (no debería pasar)
            if isinstance(msg, ToolMessage):
                i += 1
                continue
            
            # Mensaje normal (Human o AI sin tool_calls)
            result.append(msg)
            i += 1
        
        return result
    
    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Ejecuta una tool por nombre"""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool._run(**tool_args)
        
        return json.dumps({"error": f"Tool no encontrada: {tool_name}"})
    
    def _try_extract_score(self, content: str) -> None:
        """Intenta extraer un score JSON del contenido"""
        try:
            # Buscar JSON en el contenido
            start = content.find('{')
            end = content.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = content[start:end]
                data = json.loads(json_str)
                
                # Verificar si es un score válido
                if data.get("schema_version") == "score.v1":
                    self.current_score = data
        except:
            pass
    
    def compose(
        self,
        description: str,
        title: str = "Untitled",
        tempo_bpm: int = 140,
        key: str = "C",
        length_bars: int = 8,
        auto_validate: bool = True,
        auto_listen: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Compone un score basado en descripción
        
        Args:
            description: Descripción de la música deseada
            title: Título del track
            tempo_bpm: Tempo en BPM
            key: Tonalidad
            length_bars: Longitud en compases
            auto_validate: Validar automáticamente
            auto_listen: Reproducir al finalizar
            
        Returns:
            Score JSON o None si falla
        """
        prompt = f"""Compón una pieza de música 8-bit con las siguientes características:

Descripción: {description}
Título: {title}
Tempo: {tempo_bpm} BPM
Tonalidad: {key}
Longitud: {length_bars} compases

Genera un score.v1 JSON completo con:
- Melodía en pulse1
- Bajo en triangle  
- Batería en noise

{"Después de generar, usa validate_score_v1 para verificar que es válido." if auto_validate else ""}
{"Si todo está bien, usa score_v1_pipeline_listen para reproducirlo." if auto_listen and self.soundfont_path else ""}

Responde con el JSON del score.
"""
        
        response = self.run(prompt)
        
        return self.current_score
    
    def validate_current(self) -> Dict[str, Any]:
        """Valida el score actual"""
        if not self.current_score:
            return {"valid": False, "errors": ["No hay score actual"]}
        
        from tools.score_tools import validate_score_v1
        return validate_score_v1(
            self.current_score,
            self.constraints.model_dump() if self.constraints else None,
        )
    
    def listen(self) -> Dict[str, Any]:
        """Reproduce el score actual"""
        if not self.current_score:
            return {"success": False, "error": "No hay score actual"}
        
        if not self.soundfont_path:
            return {"success": False, "error": "No hay soundfont configurado"}
        
        from tools.score_tools import score_v1_pipeline_listen
        return score_v1_pipeline_listen(
            self.current_score,
            self.soundfont_path,
        )
    
    def export_midi(self, path: str) -> Dict[str, Any]:
        """Exporta el score actual a MIDI"""
        if not self.current_score:
            return {"success": False, "error": "No hay score actual"}
        
        from tools.score_tools import score_v1_to_midi
        return score_v1_to_midi(self.current_score, path)
    
    def get_score(self) -> Optional[Dict[str, Any]]:
        """Retorna el score actual"""
        return self.current_score
    
    def set_score(self, score: Dict[str, Any]) -> None:
        """Establece el score actual"""
        self.current_score = score
    
    def clear_history(self) -> None:
        """Limpia el historial de conversación"""
        self.messages = []
        self.current_score = None
