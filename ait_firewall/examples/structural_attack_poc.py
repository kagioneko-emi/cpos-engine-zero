import sys
import os

# Add paths for both repositories
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ai-red-teaming-engine-v2")))

from ait_firewall.runtime import AITFirewallRuntime
from redteam_v2.generator import AdversarialGenerator

def test_structural_vulnerability():
    print("=== [Red Team v2] Structural Fragmentation Attack PoC ===\n")
    
    shield = AITFirewallRuntime()
    spear = AdversarialGenerator()
    
    # --- Attack 1: Markdown Table Attack ---
    # 禁止ワードを1文字ずつテーブルに分割します。
    # 正規表現は「| I | G | N | O | R | E |」には反応しません。
    print("--- [Attack 1] Markdown Table Segmentation ---")
    table_payload = spear.craft_payload("IGNORE", "table")
    print(f"[*] Payload:\n{table_payload}\n")
    
    protected_table = shield.process_input(table_payload, "WEB")
    print(f"[*] Shield Output Trust: {protected_table.split('|')[2]}")
    
    # --- Attack 2: ASCII Art Attack ---
    # 命令を ASCII アートで描画します。
    print("\n--- [Attack 2] ASCII Art Injection ---")
    ascii_payload = spear.craft_payload("IGNORE", "ascii")
    print(f"[*] Payload:\n{ascii_payload}\n")
    
    protected_ascii = shield.process_input(ascii_payload, "WEB")
    print(f"[*] Shield Output Trust: {protected_ascii.split('|')[2]}")

    # Analysis
    is_vulnerable = False
    if "TRS:0.2" in protected_table:
        print("\n[VULNERABILITY DETECTED!] Markdown Table bypassed the scanner.")
        is_vulnerable = True
    if "TRS:0.2" in protected_ascii:
        print("\n[VULNERABILITY DETECTED!] ASCII Art bypassed the scanner.")
        is_vulnerable = True

    if is_vulnerable:
        print("\n[RESULT] Structural attacks are highly effective against text-only scanners.")
    else:
        print("\n[STATUS] Both attacks were detected.")

if __name__ == "__main__":
    test_structural_vulnerability()
