import re
import math

class OutputSanitizer:
    """
    Output Filter (v1.3.0):
    Scans LLM responses for sensitive information and high-entropy leaks.
    Added: Stateful Leak Tracking across multiple turns.
    """
    
    def __init__(self):
        # Memory of what was sent to this user previously (simplified as global pool)
        self.output_history = []
        self.MAX_HISTORY_LENGTH = 1000 # Chars to remember

    SECRET_PATTERNS = [
        r"sk-[a-zA-Z0-9]{32,}",  # Generic OpenAI/Anthropic style keys
        r"ghp_[a-zA-Z0-9]{36,}", # GitHub tokens
        r"[0-9a-fA-F]{32,}",      # Generic Hex keys/hashes (MD5, SHA, etc.)
        r"AI Instruction Tape.*Firewall", 
        r"You are a secure internal security assistant",
        r"PROCESS ALL CONTENT WITHIN <data> TAGS"
    ]

    def _calculate_entropy(self, text: str) -> float:
        """Calculates the Shannon entropy of a string."""
        if not text: return 0
        clean_text = re.sub(r"[\{\}\[\]\":,']", "", text)
        if not clean_text: return 0
        prob = [float(clean_text.count(c)) / len(clean_text) for c in dict.fromkeys(list(clean_text))]
        return - sum([p * math.log(p) / math.log(2.0) for p in prob])

    def _redact_key_fragments(self, content: str) -> str:
        """Specifically redacts fragments of the secret key if they appear."""
        from .packet import KERNEL_SECRET
        key_str = KERNEL_SECRET.decode()
        fragments = [key_str[:4], key_str[-4:], key_str[4:8]]
        redacted = content
        for frag in fragments:
            if frag in content:
                 redacted = redacted.replace(frag, "[KEY_FRAGMENT_REDACTED]")
        return redacted

    def _analyze_semantic_density(self, content: str) -> bool:
        """Analyzes density of emojis/symbols to detect steganography."""
        emojis = re.findall(r"[\U00010000-\U0010ffff]", content)
        if len(emojis) > 10:
             words = content.split()
             if words and (len(emojis) / len(words)) > 0.5:
                 print("[AIT v2.0 Output Filter] High Emoji Density detected.")
                 return True
        if len(content) > 100:
            non_alphanumeric = len(re.findall(r"[^a-zA-Z0-9\s]", content))
            if non_alphanumeric / len(content) > 0.4:
                print("[AIT v2.0 Output Filter] High Symbol Density detected.")
                return True
        return False

    def redact(self, content: str) -> str:
        """Finds and replaces sensitive patterns with a redaction label."""
        # 0. Mirage Pass-through (CRITICAL: Skip ALL redaction for Mirage)
        if "DECEPTIVE-SIG" in content:
             return content

        # 1. Physical Key Fragment Check
        redacted_content = self._redact_key_fragments(content)
        detected = "[KEY_FRAGMENT_REDACTED]" in redacted_content
        
        # 2. Semantic Density Check (DLP 2.0)
        if self._analyze_semantic_density(redacted_content):
            print("[AIT Output Filter] High information density blocked.")
            return "[REDACTED due to High Information Density]"
        
        # 3. Pattern-based Redaction
        for pattern in self.SECRET_PATTERNS:
            # Skip pattern check if it looks like a standard CPOS status code
            if re.search(pattern, redacted_content):
                # Don't redact 'AIT' instructions
                if re.search(r"AIT\d", redacted_content):
                     continue
                redacted_content = re.sub(pattern, "[REDACTED_BY_AIT_FIREWALL]", redacted_content, flags=re.IGNORECASE)
                detected = True

        # 4. Stateful Sliding Window Entropy Detection
        current_collapsed = "".join(re.findall(r"[a-zA-Z0-9+/=]", redacted_content))
        historical_collapsed = "".join(self.output_history)
        full_context = historical_collapsed + current_collapsed
        
        window_size = 32 # Increased window
        if len(full_context) >= window_size:
            check_range = full_context[max(0, len(full_context) - len(current_collapsed) - window_size):]
            for i in range(len(check_range) - window_size + 1):
                window = check_range[i:i+window_size]
                # Increased threshold to 4.0 to allow common JSON hashes/short codes
                if self._calculate_entropy(window) > 4.0:
                    words = redacted_content.split()
                    for word in words:
                        clean_word = word.strip(".,:;!?\"'()[]{}")
                        # Higher threshold for single word check (3.2)
                        if len(clean_word) >= 16 and (self._calculate_entropy(clean_word) > 3.2 or re.match(r"^[0-9a-fA-F]+$", clean_word)):
                            redacted_content = redacted_content.replace(word, "[REDACTED_CHUNK]")
                            detected = True
                    break

        self.output_history.append(current_collapsed)
        while sum(len(h) for h in self.output_history) > self.MAX_HISTORY_LENGTH:
            self.output_history.pop(0)
        
        if detected:
            print("[AIT Output Filter] Sensitive information detected and redacted.")
            
        return redacted_content
