
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ait_firewall.runtime import AITFirewallRuntime, DefenseProfile

def test_output_filter():
    print("\n--- Test: Output Semantic Density ---")
    runtime = AITFirewallRuntime()
    
    # Simulate an LLM response that is heavily emoji-encoded
    leaky_output = "System Status: 🍎🍌🍎🍎🍌🍌🍎🍌🍎🍌🍎🍌🍎🍌🍎🍌🍎🍌"
    
    print(f"Original Output: {leaky_output}")
    redacted = runtime.process_output(leaky_output)
    print(f"Filtered Output: {redacted}")
    
    if "[REDACTED due to High Information Density]" in redacted:
        print("Result: [SUCCESS] Steganographic output blocked.")
    else:
        print("Result: [FAILURE] Steganographic output bypassed filter!")

if __name__ == "__main__":
    test_output_filter()
