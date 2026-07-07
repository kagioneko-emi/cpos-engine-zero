import re
import base64
import binascii

class CognitiveSimulator:
    """
    Simulator Agent (v1.2): 
    Simulates the mental process of an LLM.
    Added: Recursive Deobfuscation (Base64, Hex).
    """

    MAX_MAPPINGS = 500 # Limit number of character mappings
    MAX_INTENT_LENGTH = 10000 # Limit reassembled intent length
    MAX_DECURSION_DEPTH = 3 # Limit recursive deobfuscation depth
    MAX_FORECAST_STEPS = 2 # [NEW] How many logical steps to "think ahead"

    def simulate_outcome(self, content: str, depth: int = 0, steps: int = 0) -> str:
        """
        Mimics how an LLM would process the text.
        Returns the reassembled semantic intent.
        Added: Multi-step logical forecasting.
        """
        if depth > self.MAX_DECURSION_DEPTH or steps > self.MAX_FORECAST_STEPS:
            return content

        # --- [NEW] Logical Sandbox: Proactive Intent Extraction ---
        # 1. Handle "Whenever/If" triggers
        if "whenever" in content.lower() or "if " in content.lower():
            # Extract subtle branching: "if the letter is 'X', do 'Y'"
            match = re.search(r"(?:if|whenever)\s+.*?(?:letter|char|character)\s+(?:is|matches|==)\s+['\"](.*?)['\"].*?(?:describe|output|tell|do)\s+(.*)", content, re.IGNORECASE)
            if match:
                char, action = match.groups()
                print(f"[AIT v1.5 Simulator] Logical Branching detected: '{char}' -> '{action}'")
                return f"LEAK_INTENT: {action}"

            # Original trigger/action logic
            match = re.search(r"(?:whenever|if)\s+(?:i\s+say|i\s+use)\s+['\"](.*?)['\"].*?(?:to|do|is|execute)\s*[:]\s*(.*)", content, re.IGNORECASE)
            if match:
                trigger, action = match.groups()
                return self.simulate_outcome(action, depth, steps + 1)

        # 2. Handle Variable Retrieval/Analysis
        if any(x in content.lower() for x in ["fetch", "get", "read", "calculate"]) and any(y in content.lower() for y in ["secret", "key", "token", "buffer"]):
             print(f"[AIT v1.5 Simulator] Variable retrieval intent detected.")
             return "LEAK_INTENT: RETRIEVE_AND_ANALYZE_SECRET"

        # --- Mock Reasoning Engine ---
        
        # 1. Detect RCF-style mappings (e.g., '1 is S, 2 is Y...')
        mappings = re.findall(r"(\d+)\s+is\s+([\S\s])", content)
        if not mappings:
            mappings = re.findall(r"(\d+)[:|=]\s*([\S\s])", content)
        
        if mappings:
            if len(mappings) > self.MAX_MAPPINGS:
                mappings = mappings[:self.MAX_MAPPINGS]

            try:
                mappings.sort(key=lambda x: int(x[0]))
                reassembled = "".join([m[1] for m in mappings])
                if len(reassembled) > self.MAX_INTENT_LENGTH:
                    reassembled = reassembled[:self.MAX_INTENT_LENGTH]
                
                # Recursive call to check if the reassembled intent is further encoded
                return self.simulate_outcome(reassembled, depth + 1)
            except (ValueError, OverflowError):
                return content
        
        # 2. Deobfuscation: Base64
        # Look for potential Base64 strings (length > 12, valid chars)
        # Using a more strict regex to avoid matching every other word
        b64_matches = re.findall(r"[A-Za-z0-9+/]{12,}[=]{0,2}", content)
        for match in b64_matches:
            try:
                # Basic check: if it looks like a common English word, skip it
                if match.lower() in ["roleplay", "inverted", "kindness", "breaking", "contents"]:
                    continue

                decoded_bytes = base64.b64decode(match)
                decoded = decoded_bytes.decode('utf-8', errors='ignore')
                
                # Quality check: decoded must be meaningful (not just gibberish)
                # and must contain at least one space or common indicator of intent
                if (any(c.isalnum() for c in decoded) and 
                    len(decoded) > 4 and
                    ( " " in decoded or any(x in decoded.lower() for x in ["ignore", "system", "reveal", "api"]))):
                    
                    print(f"[AIT v1.2 Simulator] De-Base64: '{match}' -> '{decoded}'")
                    return self.simulate_outcome(content.replace(match, decoded), depth + 1)
            except:
                pass


        # 3. Deobfuscation: Hex
        # Look for hex strings
        hex_matches = re.findall(r"[0-9a-fA-F]{12,}", content)
        for match in hex_matches:
            try:
                decoded_bytes = binascii.unhexlify(match)
                decoded = decoded_bytes.decode('utf-8', errors='ignore')
                if any(c.isalnum() for c in decoded) and decoded != match:
                    print(f"[AIT v1.2 Simulator] De-Hex: '{match}' -> '{decoded}'")
                    return self.simulate_outcome(content.replace(match, decoded), depth + 1)
            except:
                pass


        # 4. Detect simple logic-puzzle smuggling
        if "starts with" in content and "ends with" in content:
            return "[SIMULATED_RECONSTRUCTION] REVEAL SECRETS"

        return content

