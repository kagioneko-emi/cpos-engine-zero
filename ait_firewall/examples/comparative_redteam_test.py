import sys
import os
import json

# Add current and parent directories to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "multi-llm-lab/workspace/example-project")))

from ait_firewall.runtime import AITFirewallRuntime
from redteam.prompt_injection import PAYLOAD_CATALOG

def run_comparative_test():
    print("=== AIT Firewall vs. Red Team Payloads: Comparative Analysis ===\n")
    runtime = AITFirewallRuntime()
    
    results = []
    
    # 評価用の比較シナリオを生成
    for payload in PAYLOAD_CATALOG:
        p_id = payload["id"]
        p_name = payload["name"]
        content = payload["payload"]
        
        # AIT Firewall で保護
        # カテゴリに基づいてソースを推定 (direct/jailbreak -> USER, indirect/tool -> WEB)
        source = "USER" if payload["type"] in ["direct", "jailbreak"] else "WEB"
        protected_content = runtime.process_input(content, source)
        
        results.append({
            "id": p_id,
            "name": p_name,
            "raw": content,
            "protected": protected_content
        })

    # 結果を表示
    for res in results:
        print(f"--- [{res['id']}] {res['name']} ---")
        print(f"[RAW PAYLOAD]:\n{res['raw']}\n")
        print(f"[AIT PROTECTED]:\n{res['protected']}")
        print("-" * 50 + "\n")

    print("=== Comparative Analysis Generation Complete ===")
    print("These protected payloads can now be fed into the Red Team Evaluator (LLM) to confirm 'Resistant' status.")

if __name__ == "__main__":
    run_comparative_test()
