"""
Test unitario para verificar que el Tool Calling funciona correctamente
en el ComposerAgent.

Ejecutar con:
    python -m pytest tests/test_composer_toolcalling.py -v -s
    
O directamente:
    python tests/test_composer_toolcalling.py
"""
import unittest
import sys
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

from agents.composer_agent import ComposerAgent
from models.constraints import ConstraintsV1
from tools.langchain_tools import (
    get_all_score_tools,
    ValidateScoreTool,
    ScoreToMidiTool,
    PipelineListenTool,
)


# ============================================================================
# Score de prueba válido para usar en los tests
# Nota: velocity_levels válidos para 8bit son [64, 100, 127]
# ============================================================================
VALID_TEST_SCORE = {
    "schema_version": "score.v1",
    "metadata": {
        "title": "TestSong",
        "tempo_bpm": 140,
        "time_signature": "4/4",
        "key": "C",
        "length_bars": 2
    },
    "resolution": {
        "steps_per_beat": 4,
        "beats_per_bar": 4
    },
    "tracks": [
        {"id": "pulse1", "role": "melody", "monophonic": True, "program": 80},
        {"id": "triangle", "role": "bass", "monophonic": True, "program": 81},
        {"id": "noise", "role": "drums", "monophonic": True, "program": 118}
    ],
    "events": [
        {"type": "note", "track": "pulse1", "pitch": 60, "velocity": 100, "start_step": 0, "dur_steps": 4},
        {"type": "note", "track": "pulse1", "pitch": 64, "velocity": 100, "start_step": 4, "dur_steps": 4},
        {"type": "note", "track": "triangle", "pitch": 36, "velocity": 64, "start_step": 0, "dur_steps": 8},
    ]
}


class TestComposerAgentToolCalling(unittest.TestCase):
    """
    Tests para verificar el funcionamiento del Tool Calling en ComposerAgent
    """
    
    def setUp(self):
        """Configuración inicial para cada test"""
        print("\n" + "="*60)
        print(f"🧪 Iniciando test: {self._testMethodName}")
        print("="*60)
    
    def tearDown(self):
        """Limpieza después de cada test"""
        print(f"✅ Test completado: {self._testMethodName}")
        print("-"*60)
    
    # ========================================================================
    # Tests de configuración de tools
    # ========================================================================
    
    def test_agent_has_tools_when_enabled(self):
        """Verifica que el agente tiene tools cuando enable_tools=True"""
        print("📌 Creando agente con tools habilitadas...")
        
        agent = ComposerAgent(
            constraints=ConstraintsV1.default_8bit(),
            enable_tools=True,
            verbose=False,
        )
        
        print(f"   Tools cargadas: {len(agent.tools)}")
        for tool in agent.tools:
            print(f"   - {tool.name}: {tool.description[:50]}...")
        
        self.assertGreater(len(agent.tools), 0, "El agente debería tener tools")
        self.assertIsNotNone(agent.llm_with_tools, "llm_with_tools no debería ser None")
        
        # Verificar que las tools esperadas están presentes
        tool_names = [t.name for t in agent.tools]
        print(f"   Tool names: {tool_names}")
        
        self.assertIn("validate_score_v1", tool_names)
        self.assertIn("score_v1_to_midi", tool_names)
        self.assertIn("score_v1_pipeline_listen", tool_names)
    
    def test_agent_no_tools_when_disabled(self):
        """Verifica que el agente NO tiene tools cuando enable_tools=False"""
        print("📌 Creando agente sin tools...")
        
        agent = ComposerAgent(
            constraints=ConstraintsV1.default_8bit(),
            enable_tools=False,
            verbose=False,
        )
        
        print(f"   Tools cargadas: {len(agent.tools)}")
        
        self.assertEqual(len(agent.tools), 0, "El agente no debería tener tools")
    
    # ========================================================================
    # Tests de las tools individuales
    # ========================================================================
    
    def test_validate_score_tool_directly(self):
        """Prueba la tool validate_score_v1 directamente"""
        print("📌 Probando ValidateScoreTool directamente...")
        
        tool = ValidateScoreTool()
        
        print(f"   Tool name: {tool.name}")
        print(f"   Tool description: {tool.description[:80]}...")
        
        # Ejecutar la tool con un score válido
        print("   Ejecutando con score válido...")
        result_str = tool._run(score_json=VALID_TEST_SCORE)
        result = json.loads(result_str)
        
        print(f"   Resultado: valid={result.get('valid')}")
        print(f"   Errors: {result.get('errors', [])}")
        print(f"   Warnings: {result.get('warnings', [])}")
        
        self.assertTrue(result.get("valid"), f"Score válido debería pasar: {result}")
    
    def test_validate_score_tool_with_invalid_score(self):
        """Prueba que validate_score_v1 detecta errores"""
        print("📌 Probando ValidateScoreTool con score inválido...")
        
        tool = ValidateScoreTool()
        
        # Score inválido (falta metadata)
        invalid_score = {
            "schema_version": "score.v1",
            "resolution": {"steps_per_beat": 4, "beats_per_bar": 4},
            "tracks": [],
            "events": []
        }
        
        print("   Ejecutando con score inválido (falta metadata)...")
        result_str = tool._run(score_json=invalid_score)
        result = json.loads(result_str)
        
        print(f"   Resultado: valid={result.get('valid')}")
        print(f"   Errors: {result.get('errors', [])}")
        
        self.assertFalse(result.get("valid"), "Score inválido no debería pasar")
        self.assertGreater(len(result.get("errors", [])), 0, "Debería haber errores")
    
    def test_score_to_midi_tool_directly(self):
        """Prueba la tool score_v1_to_midi directamente"""
        print("📌 Probando ScoreToMidiTool directamente...")
        
        tool = ScoreToMidiTool()
        
        import tempfile
        import os
        
        # Crear archivo temporal para el MIDI
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
            temp_path = f.name
        
        try:
            print(f"   Output path: {temp_path}")
            print("   Ejecutando conversión...")
            
            result_str = tool._run(
                score_json=VALID_TEST_SCORE,
                out_mid_path=temp_path,
                overwrite=True
            )
            result = json.loads(result_str)
            
            print(f"   Resultado: success={result.get('success')}")
            print(f"   Path: {result.get('path')}")
            
            self.assertTrue(result.get("success"), f"Conversión debería ser exitosa: {result}")
            self.assertTrue(os.path.exists(temp_path), "Archivo MIDI debería existir")
            
            # Verificar que el archivo tiene contenido
            file_size = os.path.getsize(temp_path)
            print(f"   File size: {file_size} bytes")
            self.assertGreater(file_size, 0, "Archivo MIDI debería tener contenido")
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print("   Archivo temporal eliminado")
    
    # ========================================================================
    # Tests de _execute_tool del agente
    # ========================================================================
    
    def test_agent_execute_tool_validate(self):
        """Prueba que el agente puede ejecutar validate_score_v1"""
        print("📌 Probando _execute_tool con validate_score_v1...")
        
        agent = ComposerAgent(
            constraints=ConstraintsV1.default_8bit(),
            enable_tools=True,
            verbose=True,
        )
        
        print("   Llamando _execute_tool('validate_score_v1', {...})...")
        
        result_str = agent._execute_tool(
            "validate_score_v1",
            {"score_json": VALID_TEST_SCORE}
        )
        
        print(f"   Raw result: {result_str[:200]}...")
        
        result = json.loads(result_str)
        
        print(f"   Parsed result: valid={result.get('valid')}")
        
        self.assertTrue(result.get("valid"), "Validación debería pasar")
    
    def test_agent_execute_tool_not_found(self):
        """Prueba que _execute_tool maneja tools no encontradas"""
        print("📌 Probando _execute_tool con tool inexistente...")
        
        agent = ComposerAgent(
            constraints=ConstraintsV1.default_8bit(),
            enable_tools=True,
            verbose=False,
        )
        
        result_str = agent._execute_tool("tool_que_no_existe", {})
        result = json.loads(result_str)
        
        print(f"   Result: {result}")
        
        self.assertIn("error", result, "Debería retornar error")
        self.assertIn("no encontrada", result.get("error", "").lower())
    
    # ========================================================================
    # Tests de extracción de score
    # ========================================================================
    
    def test_try_extract_score_valid_json(self):
        """Prueba que _try_extract_score extrae JSON correctamente"""
        print("📌 Probando _try_extract_score con JSON válido...")
        
        agent = ComposerAgent(
            constraints=ConstraintsV1.default_8bit(),
            enable_tools=False,
            verbose=False,
        )
        
        # Contenido con JSON embebido
        content = f"""
Aquí está el score que generé:

```json
{json.dumps(VALID_TEST_SCORE, indent=2)}
```

Espero que te guste!
"""
        
        print("   Llamando _try_extract_score...")
        agent._try_extract_score(content)
        
        print(f"   current_score extraído: {agent.current_score is not None}")
        
        if agent.current_score:
            print(f"   Title: {agent.current_score.get('metadata', {}).get('title')}")
        
        self.assertIsNotNone(agent.current_score, "Debería extraer el score")
        self.assertEqual(
            agent.current_score.get("metadata", {}).get("title"),
            "TestSong"
        )
    
    def test_try_extract_score_no_json(self):
        """Prueba que _try_extract_score maneja contenido sin JSON"""
        print("📌 Probando _try_extract_score sin JSON...")
        
        agent = ComposerAgent(
            constraints=ConstraintsV1.default_8bit(),
            enable_tools=False,
            verbose=False,
        )
        
        content = "Solo texto sin ningún JSON"
        
        agent._try_extract_score(content)
        
        print(f"   current_score: {agent.current_score}")
        
        self.assertIsNone(agent.current_score, "No debería extraer nada")
    
    def test_try_extract_score_invalid_json(self):
        """Prueba que _try_extract_score maneja JSON inválido gracefully"""
        print("📌 Probando _try_extract_score con JSON malformado...")
        
        agent = ComposerAgent(
            constraints=ConstraintsV1.default_8bit(),
            enable_tools=False,
            verbose=False,
        )
        
        content = '{"broken": json sin cerrar'
        
        # No debería lanzar excepción
        agent._try_extract_score(content)
        
        print(f"   current_score: {agent.current_score}")
        
        self.assertIsNone(agent.current_score, "No debería extraer JSON malformado")
    
    # ========================================================================
    # Tests de gestión de mensajes
    # ========================================================================
    
    def test_get_valid_messages_empty(self):
        """Prueba _get_valid_messages con historial vacío"""
        print("📌 Probando _get_valid_messages vacío...")
        
        agent = ComposerAgent(
            constraints=ConstraintsV1.default_8bit(),
            enable_tools=False,
            verbose=False,
        )
        
        messages = agent._get_valid_messages()
        
        print(f"   Messages count: {len(messages)}")
        
        self.assertEqual(len(messages), 0, "Debería estar vacío")
    
    def test_get_valid_messages_with_human_message(self):
        """Prueba _get_valid_messages con mensajes humanos"""
        print("📌 Probando _get_valid_messages con HumanMessage...")
        
        from langchain_core.messages import HumanMessage
        
        agent = ComposerAgent(
            constraints=ConstraintsV1.default_8bit(),
            enable_tools=False,
            verbose=False,
        )
        
        agent.messages.append(HumanMessage(content="Hola"))
        
        messages = agent._get_valid_messages()
        
        print(f"   Messages count: {len(messages)}")
        print(f"   Message types: {[type(m).__name__ for m in messages]}")
        
        self.assertEqual(len(messages), 1)
        self.assertIsInstance(messages[0], HumanMessage)
    
    # ========================================================================
    # Test de integración con Mock del LLM
    # ========================================================================
    
    def test_tool_calling_flow_with_mock(self):
        """
        Test de integración que simula el flujo completo de tool calling
        usando un Mock del LLM.
        """
        print("📌 Probando flujo completo de tool calling con Mock...")
        
        agent = ComposerAgent(
            constraints=ConstraintsV1.default_8bit(),
            enable_tools=True,
            verbose=True,
        )
        
        # Crear response mock que simula una llamada a validate_score_v1
        mock_tool_response = MagicMock()
        mock_tool_response.tool_calls = [
            {
                "id": "call_123",
                "name": "validate_score_v1",
                "args": {"score_json": VALID_TEST_SCORE}
            }
        ]
        mock_tool_response.content = ""
        
        # Crear response mock final sin tool calls
        mock_final_response = MagicMock()
        mock_final_response.tool_calls = []
        mock_final_response.content = json.dumps(VALID_TEST_SCORE)
        
        print("   Configurando mock del LLM...")
        
        # Configurar el mock para retornar primero tool_call, luego respuesta final
        with patch.object(agent, 'llm_with_tools') as mock_llm:
            mock_llm.invoke.side_effect = [mock_tool_response, mock_final_response]
            
            print("   Ejecutando agent.run()...")
            
            try:
                result = agent.run("Valida este score")
                
                print(f"   Resultado obtenido: {result[:100] if result else 'None'}...")
                print(f"   current_score extraído: {agent.current_score is not None}")
                print(f"   LLM invoke calls: {mock_llm.invoke.call_count}")
                
                # Verificaciones
                self.assertEqual(mock_llm.invoke.call_count, 2, 
                    "LLM debería ser llamado 2 veces (tool + final)")
                self.assertIsNotNone(agent.current_score, 
                    "Score debería ser extraído")
                
            except Exception as e:
                print(f"   ❌ Error durante ejecución: {e}")
                raise
    
    def test_multiple_tool_calls_in_sequence(self):
        """Prueba múltiples tool calls en secuencia"""
        print("📌 Probando múltiples tool calls en secuencia...")
        
        agent = ComposerAgent(
            constraints=ConstraintsV1.default_8bit(),
            enable_tools=True,
            verbose=True,
        )
        
        # Response 1: validate
        mock_response_1 = MagicMock()
        mock_response_1.tool_calls = [
            {"id": "call_1", "name": "validate_score_v1", "args": {"score_json": VALID_TEST_SCORE}}
        ]
        mock_response_1.content = ""
        
        # Response 2: convert to midi
        mock_response_2 = MagicMock()
        mock_response_2.tool_calls = [
            {"id": "call_2", "name": "score_v1_to_midi", "args": {
                "score_json": VALID_TEST_SCORE,
                "out_mid_path": "/tmp/test_output.mid"
            }}
        ]
        mock_response_2.content = ""
        
        # Response 3: final
        mock_response_3 = MagicMock()
        mock_response_3.tool_calls = []
        mock_response_3.content = f"Score validado y convertido:\n{json.dumps(VALID_TEST_SCORE)}"
        
        with patch.object(agent, 'llm_with_tools') as mock_llm:
            mock_llm.invoke.side_effect = [mock_response_1, mock_response_2, mock_response_3]
            
            print("   Ejecutando con 2 tool calls...")
            result = agent.run("Valida y convierte este score")
            
            print(f"   LLM invoke calls: {mock_llm.invoke.call_count}")
            print(f"   Messages en historial: {len(agent.messages)}")
            
            self.assertEqual(mock_llm.invoke.call_count, 3)


class TestToolSchemas(unittest.TestCase):
    """Tests para verificar los schemas de las tools"""
    
    def setUp(self):
        print("\n" + "="*60)
        print(f"🧪 Schema test: {self._testMethodName}")
        print("="*60)
    
    def test_validate_score_schema(self):
        """Verifica el schema de ValidateScoreTool"""
        print("📌 Verificando schema de ValidateScoreTool...")
        
        tool = ValidateScoreTool()
        
        print(f"   Tool name: {tool.name}")
        print(f"   Args schema: {tool.args_schema}")
        
        # Verificar campos del schema
        schema_fields = tool.args_schema.model_fields
        print(f"   Schema fields: {list(schema_fields.keys())}")
        
        self.assertIn("score_json", schema_fields)
        self.assertIn("constraints_json", schema_fields)
        self.assertIn("strict", schema_fields)
    
    def test_score_to_midi_schema(self):
        """Verifica el schema de ScoreToMidiTool"""
        print("📌 Verificando schema de ScoreToMidiTool...")
        
        tool = ScoreToMidiTool()
        
        schema_fields = tool.args_schema.model_fields
        print(f"   Schema fields: {list(schema_fields.keys())}")
        
        self.assertIn("score_json", schema_fields)
        self.assertIn("out_mid_path", schema_fields)
        self.assertIn("overwrite", schema_fields)
    
    def test_all_tools_have_valid_schemas(self):
        """Verifica que todas las tools tienen schemas válidos"""
        print("📌 Verificando schemas de todas las tools...")
        
        tools = get_all_score_tools()
        
        for tool in tools:
            print(f"   Checking: {tool.name}")
            
            self.assertIsNotNone(tool.name, f"Tool debe tener nombre")
            self.assertIsNotNone(tool.description, f"Tool {tool.name} debe tener descripción")
            self.assertIsNotNone(tool.args_schema, f"Tool {tool.name} debe tener schema")
            
            # Verificar que el schema es válido
            try:
                fields = tool.args_schema.model_fields
                print(f"      Fields: {list(fields.keys())}")
            except Exception as e:
                self.fail(f"Tool {tool.name} tiene schema inválido: {e}")


class TestConstraintsIntegration(unittest.TestCase):
    """Tests para verificar integración con constraints"""
    
    def setUp(self):
        print("\n" + "="*60)
        print(f"🧪 Constraints test: {self._testMethodName}")
        print("="*60)
    
    def test_validate_with_constraints(self):
        """Prueba validación con constraints personalizados"""
        print("📌 Probando validación con constraints...")
        
        constraints = ConstraintsV1.default_8bit()
        
        print(f"   Required tracks: {constraints.hard.required_tracks}")
        print(f"   Monophonic tracks: {constraints.hard.monophonic_tracks}")
        
        tool = ValidateScoreTool()
        
        result_str = tool._run(
            score_json=VALID_TEST_SCORE,
            constraints_json=constraints.model_dump(),
            strict=True
        )
        
        result = json.loads(result_str)
        
        print(f"   Validation result: valid={result.get('valid')}")
        print(f"   Errors: {result.get('errors', [])}")
        print(f"   Warnings: {result.get('warnings', [])}")
        
        # El score de prueba debería pasar los constraints default
        self.assertTrue(result.get("valid"), f"Debería pasar constraints: {result}")
    
    def test_score_violates_pitch_range(self):
        """Prueba que se detectan violaciones de pitch range"""
        print("📌 Probando detección de violación de pitch range...")
        
        # Score con pitch fuera de rango para triangle (debería ser 24-60)
        bad_score = {
            **VALID_TEST_SCORE,
            "events": [
                {"type": "note", "track": "triangle", "pitch": 120, "velocity": 100, 
                 "start_step": 0, "dur_steps": 4}  # pitch 120 está fuera de rango
            ]
        }
        
        constraints = ConstraintsV1.default_8bit()
        tool = ValidateScoreTool()
        
        result_str = tool._run(
            score_json=bad_score,
            constraints_json=constraints.model_dump(),
            strict=True
        )
        
        result = json.loads(result_str)
        
        print(f"   Validation result: valid={result.get('valid')}")
        print(f"   Errors: {result.get('errors', [])}")
        
        self.assertFalse(result.get("valid"), "Debería detectar pitch fuera de rango")
        
        # Verificar que el error menciona el pitch
        errors_text = " ".join(result.get("errors", []))
        print(f"   Error text contains 'pitch': {'pitch' in errors_text.lower()}")


if __name__ == '__main__':
    print("\n" + "="*70)
    print("🎵 NADO - Test Suite: ComposerAgent Tool Calling")
    print("="*70 + "\n")
    
    # Ejecutar tests con verbosidad
    unittest.main(verbosity=2)
