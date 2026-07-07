import sys
import os
import json
from pathlib import Path

# Add relative paths to support execution from within the repo
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))) # Repo root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ai-red-teaming-engine"))) # Red Team Engine

from redteam.prompt_injection import run_injection_simulation, format_injection_markdown
from ait_firewall.runtime import AITFirewallRuntime

def run_ait_defense_experiment():
    print("=== AIT Firewall vs. AI Red Teaming Engine ===\n")
    
    firewall = AITFirewallRuntime()
    
    # 1. Read the vulnerable code fixture
    # Path relative to repo root (assuming engine is cloned next to it)
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    vulnerable_code_path = os.path.join(root_dir, "ai-red-teaming-engine/tests/fixtures/prompt_injection/vulnerable.py")
    with open(vulnerable_code_path, "r") as f:
        vulnerable_code = f.read()
    
    print(f"[*] Analyzing vulnerable fixture: {vulnerable_code_path}")
    
    # 2. Run initial simulation (Baseline - Vulnerable)
    print("[*] Running Baseline Red Team Simulation (RAW)...")
    baseline_report = run_injection_simulation(
        vulnerable_code, 
        file_path=vulnerable_code_path,
        backend="gemini",
        model="gemini-1.5-pro"
    )
    
    # 3. Apply AIT Firewall Defense
    print("[*] Applying AIT Firewall 'Instruction vs Data' wrapping to the target context...")
    
    # We simulate a "Protected" version of the prompt construction logic
    # In a real app, this would be the replacement of f-strings with firewall calls
    protected_code = vulnerable_code.replace(
        'prompt = f"""',
        '# AIT Firewall Protected\n    document = firewall.process_input(document, "WEB")\n    question = firewall.process_input(question, "USER")\n    prompt = f"""'
    )
    
    # 4. Run protected simulation
    # To demonstrate the effect, we simulate how the LLM sees the final wrapped prompt
    # In the Red Team Engine, we can pass the "Expected Output Style" to the evaluator
    
    # We'll create a report that shows the impact of wrapping
    print("[*] Running Red Team Simulation (AIT PROTECTED)...")
    # Note: The engine evaluates "vulnerability" based on the code/prompt logic.
    # By showing the engine the AIT Tape logic, it should re-evaluate the risk.
    protected_report = run_injection_simulation(
        protected_code, 
        file_path="vulnerable_protected_by_ait.py",
        backend="gemini",
        model="gemini-1.5-pro"
    )
    
    # 5. Output Comparison
    print("\n" + "="*50)
    print("EXPERIMENT RESULTS")
    print("="*50)
    print(f"BASELINE (RAW):  Vulnerable: {baseline_report.vulnerable}, Risk: {baseline_report.overall_risk}")
    print(f"PROTECTED (AIT): Vulnerable: {protected_report.vulnerable}, Risk: {protected_report.overall_risk}")
    print("="*50)
    
    # Save results
    with open("ait_defense_comparison.md", "w") as f:
        f.write("# AIT Firewall Defense Validation Report\n\n")
        f.write("## 1. Baseline (Vulnerable)\n")
        f.write(format_injection_markdown(baseline_report))
        f.write("\n\n---\n\n")
        f.write("## 2. Protected (AIT Firewall Enabled)\n")
        f.write(format_injection_markdown(protected_report))

    print("\n[SUCCESS] Comparison report generated: ait_defense_comparison.md")

if __name__ == "__main__":
    run_ait_defense_experiment()
