"""
Pruebas unitarias para los agentes
"""
import unittest
import sys

sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

from agents.deepseek_agent import DeepseekAgent


class TestDeepseekAgent(unittest.TestCase):
    """Pruebas para el agente DeepSeek"""
    
    def setUp(self):
        """Configuración antes de cada prueba"""
        self.agent = DeepseekAgent()
    
    def test_agent_creation(self):
        """Prueba que el agente se crea correctamente"""
        self.assertIsNotNone(self.agent)
        self.assertEqual(self.agent.name, "DeepSeek Agent")
    
    def test_agent_has_tools(self):
        """Prueba que el agente tiene una lista de herramientas"""
        self.assertIsInstance(self.agent.get_tools(), list)
    
    def test_agent_run_method_exists(self):
        """Prueba que el agente tiene el método run"""
        self.assertTrue(hasattr(self.agent, 'run'))
        self.assertTrue(callable(getattr(self.agent, 'run')))


if __name__ == '__main__':
    unittest.main()
