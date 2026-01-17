"""
Demo del wire protocol entre agentes
Muestra el flujo: Musician -> Researcher -> Orchestrator -> PM
"""
import sys
import json
sys.path.insert(0, '/home/chris/Documentos/Percep3/nado')

from models.score import ScoreV1
from models.constraints import ConstraintsV1
from agents.pm_agent import PMAgent
from agents.musician_agent import MusicianAgent
from agents.researcher_agent import ResearcherAgent


def main():
    """Demo del wire protocol"""
    print("\n" + "=" * 60)
    print("📡 Demo Wire Protocol - Comunicación entre Agentes")
    print("=" * 60 + "\n")
    
    # 1. Crear score vacío y constraints
    print("1️⃣ Inicializando score y constraints...")
    score = ScoreV1.create_empty(
        title="Wire Protocol Demo",
        tempo_bpm=120,
        key="C",
        length_bars=2,
    )
    constraints = ConstraintsV1.default_8bit()
    
    # 2. Inicializar agentes
    print("2️⃣ Inicializando agentes...")
    pm = PMAgent(constraints=constraints)
    musician = MusicianAgent(use_llm=False)  # Solo algorítmico para demo
    researcher = ResearcherAgent(constraints=constraints)
    
    # 3. PM publica constraints
    print("\n3️⃣ PM Agent publica constraints:")
    print(pm.get_constraints_summary())
    
    # 4. Musician genera propuesta
    print("\n4️⃣ Musician Agent genera propuesta para bar 0:")
    proposal = musician.compose_window(
        score=score,
        bar_index=0,
        num_variants=3,
    )
    
    print(f"   Schema: {proposal.schema_version}")
    print(f"   Window: bar={proposal.window.bar_index}, steps=[{proposal.window.start_step}, {proposal.window.end_step})")
    print(f"   Variantes: {len(proposal.variants)}")
    
    for v in proposal.variants:
        print(f"     - {v.id}: {len(v.events)} eventos, tags={v.tags}")
    
    # 5. Researcher evalúa y genera critic report
    print("\n5️⃣ Researcher Agent evalúa propuesta:")
    critic_report = researcher.evaluate_proposal(proposal, score)
    
    print(f"   Schema: {critic_report.schema_version}")
    print(f"   Rankings:")
    for r in critic_report.rankings:
        status = "✅" if r.passed_hard_constraints else "❌"
        print(f"     {status} {r.variant_id}: score={r.score:.1f}")
        for reason in r.reasons[:2]:
            print(f"        → {reason}")
    
    print(f"\n   Métricas agregadas:")
    print(f"     - Densidad: {critic_report.metrics.density:.2f}")
    print(f"     - Repetición: {critic_report.metrics.repetition:.2f}")
    print(f"     - Entropía rítmica: {critic_report.metrics.rhythm_entropy:.2f}")
    print(f"     - Cumplimiento estilo: {critic_report.metrics.style_compliance:.2f}")
    
    print(f"\n   Hints:")
    for h in critic_report.hints:
        print(f"     [{h.priority}] {h.message}")
    
    # 6. Seleccionar mejor variante
    best_id = critic_report.get_best_variant_id()
    best_variant = proposal.get_variant(best_id)
    print(f"\n6️⃣ Variante seleccionada: {best_id}")
    
    # 7. PM valida
    print("\n7️⃣ PM Agent valida variante:")
    validation = pm.validate_variant(
        best_variant,
        proposal.window.start_step,
        proposal.window.end_step,
    )
    
    if validation.is_valid:
        print("   ✅ Validación exitosa")
        score.add_events(best_variant.events)
        print(f"   → {len(best_variant.events)} eventos agregados al score")
    else:
        print("   ❌ Validación fallida:")
        for v in validation.violations:
            print(f"     - [{v.constraint_type}] {v.rule}: {v.message}")
    
    # 8. Mostrar score final
    print("\n8️⃣ Estado final del score:")
    print(f"   Total eventos: {len(score.events)}")
    
    # Exportar JSON para inspección
    print("\n📄 Proposal JSON (muestra):")
    proposal_dict = proposal.model_dump()
    print(json.dumps(proposal_dict, indent=2)[:500] + "...")
    
    print("\n📄 Critic Report JSON (muestra):")
    report_dict = critic_report.model_dump()
    print(json.dumps(report_dict, indent=2)[:500] + "...")
    
    print("\n" + "=" * 60)
    print("✅ Demo Wire Protocol completado")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
