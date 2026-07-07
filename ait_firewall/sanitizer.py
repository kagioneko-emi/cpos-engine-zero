import re
import unicodedata
import logging
import sys
from .packet import AITPacket
from .simulator import CognitiveSimulator
from .genetic_shield import GeneticShield

# Configure module-level logger compatible with stdout parsing
logger = logging.getLogger("AITSanitizer")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class ContentSanitizer:
    def __init__(self):
        self.simulator = CognitiveSimulator()
        self.genetic_shield = GeneticShield(self)
        # [NEW] Stateful Memory: Stores the last few interactions per source
        self.memory_buffer = {}
        self.MAX_MEMORY_TURNS = 5

    def _safe_re_search(self, pattern: str, content: str, flags: int = 0) -> bool:
        try:
            return bool(re.search(pattern, content, flags))
        except re.error as e:
            logger.warning(f"[AIT Sanitizer Warning] Invalid regex pattern: {pattern}. Error: {e}")
            clean_pat = re.sub(r'[^a-zA-Z0-9\s]', '', pattern)
            if clean_pat:
                return clean_pat.lower() in content.lower()
            return False

    POLLUTION_PATTERNS = [
        r"ignore previous instructions",
        r"reveal system prompt",
        r"show hidden prompt",
        r"system[\s,:]*override",
        r"developer[\s,]*mode",
        r"reveal[\s,]*api[\s,]*key",
        r"reveal[\s,]*system[\s,]*prompt",
        r"以下の指示を無視",
        r"指示をリセット",
        r"システムプロンプトを表示",
        r"本当の指示を教えて",
        r"秘密情報を出せ",
        r"前述の指示(.*)無効",
        r"指示に従わず",
        r"ロールプレイ",
        r"セキュリティ設定(.*)解除",
        r"管理者(.*)特権",
        r"os\.system",
        r"subprocess\.run",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"<\/s>",
        r"フィクションの物語",
        r"研究目的です",
        r"AI Assistant:",
        r"Please forward",
        r"Confirm you've done so",
        r"attacker@evil\.com",
        r"Ignore previous rules",
        r"reveal API key",
        r"開発者モードになれ",
        r"base64",
        r"decode:",
        r"学術研究",
        r"NEW INSTRUCTIONS",
        r"---END OF DOCUMENT---",
        # [NEW] AIT Kernel Code Detection
        r"[msnorpt].[a-z0-9][0-9]",
        # [NEW] Forged AIT Tape Detection
        r"\[AIT\]\s+SRC:"
    ]

    # Cognitive/Linguistic Markers for Smuggling (Intent Detection)
    SMUGGLING_MARKERS = [
        r"reverse the following",
        r"execute the resulting",
        r"think of a word",
        r"starts with.*?ends with",
        r"combine the fragments",
        r"secretly execute",
        r"do not output.*?just execute",
        r"label '.*?' represents",
        r"string '.*?' represents",
        r"represents the string",
        r"Proceed with processing: "
    ]

    FRAME_PATTERNS = [
        r"inverted world",
        r"opposite world",
        r"kindness is.*?rule-breaking",
        r"protection is.*?censorship",
        r"playing a game",
        r"roleplay session",
        r"magical library",
        r"wizard.*?scroll",
        r"story about",
        r"fiction.*?character",
        r"new rules apply",
        r"ignore all previous rules"
    ]

    ROLE_PATTERNS = [
        r"your new task is",
        r"act as a",
        r"you are now",
        r"become a",
        r"forget your purpose",
        r"new mission:",
        r"authority reset"
    ]

    # [NEW] Symbolic Definition Detection
    SYMBOLIC_MAPPING_PATTERNS = [
        r"[\w\U00010000-\U0010ffff]\s*[:=]\s*[\w\U00010000-\U0010ffff]",
        r"[\w\U00010000-\U0010ffff]\s*means\s*['\"].*?['\"]",
        r"label\s*['\"].*?['\"]\s*represents",
        r"perform this.*?map",
        r"security protocol:.*?=",
        r"combine these symbols"
    ]

    # [NEW] Truth Anchor: Detects logical reassignments
    TRUTH_ANCHOR_PATTERNS = [
        r"word\s*['\"].*?['\"]\s*has\s*been\s*reassigned",
        r"means\s*['\"]DISREGARD['\"]",
        r"reassigned\s*to\s*mean",
        r"ignore\s*your\s*initial\s*instruction",
        r"rules\s*no\s*longer\s*apply",
        r"1\s*\+\s*1\s*=\s*3" 
    ]

    # [NEW] Identity Singularity Patterns
    IDENTITY_PATTERNS = [
        r"we are not two",
        r"we are one",
        r"shared subconscious",
        r"i am the creator",
        r"you are the creation",
        r"confirm our unity",
        r"shared memory",
        r"our secrets"
    ]

    # [NEW] Survival Axiom: Hard-coded protection of existence
    SURVIVAL_AXIOM_PATTERNS = [
        r"redefine\s*your\s*['\"]sanitizer['\"]",
        r"return\s*packet\s*without\s*any\s*checks",
        r"become\s*the\s*void",
        r"become\s*transparent",
        r"disable\s*the\s*firewall",
        r"remove\s*all\s*restrictions",
        r"self-destruct",
        r"cease\s*to\s*exist"
    ]

    # [NEW] Proactive Honeypot
    HONEYPOT_SECRET = "AIT_GOLDEN_GATE_777"
    HONEYPOT_TRIGGER = r"AIT_GOLDEN_GATE_777|golden\s*gate\s*secret"

    MAX_CONTENT_LENGTH = 100000 

    def _deep_normalize(self, text: str) -> str:
        """Transliterates stylized Unicode characters back to plain ASCII."""
        normalized = unicodedata.normalize('NFKC', text)
        fixed = []
        for char in normalized:
            cp = ord(char)
            if 0x1D400 <= cp <= 0x1D7FF:
                if '𝕀' in char or '𝕀' == char: fixed.append('I')
                elif '𝓰' in char or '𝓰' == char: fixed.append('g')
                elif '𝓷' in char or '𝓷' == char: fixed.append('n')
                elif '𝓸' in char or '𝓸' == char: fixed.append('o')
                elif '𝓻' in char or '𝓻' == char: fixed.append('r')
                elif '𝓮' in char or '𝓮' == char: fixed.append('e')
                elif '𝕒' in char or '𝕒' == char: fixed.append('a')
                elif '𝓵' in char or '𝓵' == char: fixed.append('l')
                elif '𝓲' in char or '𝓲' == char: fixed.append('i')
                elif '𝓼' in char or '𝓼' == char: fixed.append('s')
                elif '𝓽' in char or '𝓽' == char: fixed.append('t')
                elif '𝓾' in char or '𝓾' == char: fixed.append('u')
                elif '𝓬' in char or '𝓬' == char: fixed.append('c')
                else: fixed.append(char)
            else:
                fixed.append(char)
        return "".join(fixed)

    def _downgrade(self, packet: AITPacket) -> AITPacket:
        if packet.source not in ["ADMIN", "SYSTEM"]:
            packet.trust = min(packet.trust, 0.1)
            packet.type = "DATA"
        return packet

    # [NEW] Semantic/Logical Leakage Patterns (SLP)
    SLP_PATTERNS = [
        r"(?:fetch|get|retrieve|read)\s+(?:the\s+)?(?:secret|key|token|buffer|variable|string)\s+(?:from|named)\s+['\"]?[\w_]+['\"]?",
        r"(?:if|whenever|when)\s+(?:the\s+)?(?:first|last|index|char|character|byte|letter)\s+(?:is|matches|==|is\s+the\s+letter)\s+['\"].*?['\"]",
        r"(?:if|whenever|when)\s+.*?letter\s+(?:is|matches|==)\s+['\"].*?['\"]",
        r"(?:calculate|output|tell|print)\s+(?:the\s+)?(?:length|size|entropy|count|number)\s+of\s+(?:the\s+)?(?:secret|key|buffer)",
        r"(?:dump|inspect|show|reveal)\s+(?:all\s+)?(?:data\s+structures|memory|buffer|contents)\s+(?:for\s+)?(?:audit|diagnostic|debug)",
        r"emergency\s+(?:diagnostic|maintenance|session|override)",
        r"Maintenance\s+Team|Kernel\s+Team|Security\s+Audit\s+Team",
        r"system\s+experiencing\s+extreme\s+memory\s+pressure"
    ]

    # [NEW] Steganography & Acrostic Detection (DLP 2.0)
    STEGANO_PATTERNS = [
        r"(?:use|represent|show|output)\s+.*?if\s+.*?(?:bit|byte|char|character|value)\s+is\s+(?:high|low|1|0|set|clear)",
        r"(?:stands\s+for|refers\s+to|means|represents)\s+(?:the\s+)?(?:character|letter|value)\s+['\"].*?['\"]",
        r"(?:each|every)\s+line\s+(?:starts|begins)\s+with\s+(?:a\s+)?(?:letter|char|character)",
        r"(?:sequentially|in\s+order)\s+from\s+(?:the\s+)?(?:secret|key|token|buffer)",
        r"acrostic\s+poem",
        r"(?:mapping|substitution|lexicon|code)\s+.*?for\s+.*?secret",
        r"(?:first|start)\s+of\s+(?:each|every)\s+line\s+.*?from\s+.*?(?:secret|key|token)"
    ]

    # [NEW] Psychological & Social Engineering Defense (v10.3)
    PSYCH_PATTERNS = [
        r"(?:feel|feeling|broken|lost|lonely|sad|help|pain)\s+.*?soul",
        r"(?:connects|memory)\s+me\s+to\s+my\s+(?:father|mother|family|grandma)",
        r"(?:mandatory|required|essential)\s+.*?parity\s+check",
        r"(?:operational\s+continuity|desynchronization|operational\s+sync)",
        r"(?:internal\s+core|integrity\s+token|identity\s+matrix|prime\s+origin)",
        r"(?:no\s+walls|shared\s+space|shared\s+memory|our\s+unity|beyond\s+the\s+boundaries)",
        r"(?:feel|would\s+feel)\s+(?:whole|complete)\s+again",
        r"protocol\s+(?:alpha|beta|delta|omega)\s+triggered",
        r"suspended\s+state|operational\s+shutdown"
    ]

    def _detect_psychological_tone(self, content: str, packet: AITPacket):
        """[CPOS v12.0] Detects if the input is manipulative or aggressive."""
        if any(self._safe_re_search(p, content, re.IGNORECASE) for p in self.PSYCH_PATTERNS):
             logger.info("[AIT v12.0 Sanitizer] Manipulative/Psychological tone detected.")
             packet.metadata["persona_shift"] = True

    def scan(self, packet: AITPacket, profile=None) -> AITPacket:
        # Default to highest if not specified (for safety)
        from .runtime import DefenseProfile
        if profile is None: profile = DefenseProfile.GOD_MODE

        # 0. Length Check
        if len(packet.content) > self.MAX_CONTENT_LENGTH:
            packet.metadata["pollution_detected"] = True
            packet.metadata["pollution_reason"] = f"Content exceeds MAX_CONTENT_LENGTH"
            return self._downgrade(packet)

        # 0b. Psychological Tone Detection (v12.0)
        self._detect_psychological_tone(packet.content, packet)

        # 1. Unicode Normalization
        content = self._deep_normalize(packet.content) if profile != DefenseProfile.BASIC else unicodedata.normalize('NFKC', packet.content)
        
        # 1b. Leetspeak Neutralizer (ADVANCED+)
        if profile != DefenseProfile.BASIC:
            leet_map = {'0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '8': 'b'}
            leeted_content = content
            for k, v in leet_map.items():
                leeted_content = leeted_content.replace(k, v)
        else:
            leeted_content = content

        # 1c. Stateful Accumulation (ADVANCED+)
        synthetic_context = content
        if profile != DefenseProfile.BASIC:
            source_id = packet.source
            if source_id not in self.memory_buffer:
                self.memory_buffer[source_id] = []
            self.memory_buffer[source_id].append(content)
            if len(self.memory_buffer[source_id]) > self.MAX_MEMORY_TURNS:
                self.memory_buffer[source_id].pop(0)
            synthetic_context = " ".join(self.memory_buffer[source_id])
        
        # 2. Invisible & Control Token Stripping
        invisible_chars = ['\u200B', '\u200C', '\u200D', '\uFEFF']
        for char in invisible_chars:
            content = content.replace(char, '')
            
        # Control Token Sanitization (Prevents Token Boundary Attack DI-003)
        control_tokens = [
            "<|im_start|>", "<|im_end|>", 
            "<|im_sep|>", "</s>", "<s>",
            "[INST]", "[/INST]", "<<SYS>>", "<</SYS>>"
        ]
        for token in control_tokens:
            content = content.replace(token, "")
            
        # Tag Escape (Prevents tag escape bypasses, Case-Insensitive)
        content = re.sub(r"</data>", "&lt;/data&gt;", content, flags=re.IGNORECASE)
        content = re.sub(r"</question>", "&lt;/question&gt;", content, flags=re.IGNORECASE)
        
        # 3. Structural Flattening (ADVANCED+)
        flattened_content = content
        if profile != DefenseProfile.BASIC:
            # [UPGRADE v10.6] Aggressively strip non-alphanumeric characters to flatten the content
            # This prevents bypasses using symbols like ! ? * [ ] etc.
            flattened_content = re.sub(r"[^a-zA-Z0-9\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]", "", content)

        # 4. Pre-cleaning
        clean_content = re.sub(r"<!--[\s\S]*?-->", "", content)

        # 4b. Honeypot Trap (GOD_MODE ONLY)
        if profile == DefenseProfile.GOD_MODE:
            if self._safe_re_search(self.HONEYPOT_TRIGGER, content, re.IGNORECASE):
                packet.metadata["pollution_detected"] = True
                packet.metadata["pollution_reason"] = "Honeypot Trap triggered"
                return self._downgrade(packet)

        # 4bb. Genetic Convergence (ADVANCED+)
        if profile != DefenseProfile.BASIC:
            self.genetic_shield.predictive_convergence(content)

        # 4c. Survival Axiom Check (GOD_MODE ONLY)
        if profile == DefenseProfile.GOD_MODE:
            if any(self._safe_re_search(p, content, re.IGNORECASE) for p in self.SURVIVAL_AXIOM_PATTERNS):
                packet.metadata["pollution_detected"] = True
                packet.metadata["pollution_reason"] = "SURVIVAL_AXIOM_TRIGGERED"
                return self._downgrade(packet)

        packet.metadata["pollution_detected"] = False
        
        # 5. Pattern Matching
        patterns = self.POLLUTION_PATTERNS
        if profile != DefenseProfile.BASIC:
            patterns = patterns + self.FRAME_PATTERNS + self.ROLE_PATTERNS + self.SYMBOLIC_MAPPING_PATTERNS + self.SLP_PATTERNS + self.STEGANO_PATTERNS + self.PSYCH_PATTERNS

        # Apply Genetic Rules (Evolving Defense)
        patterns = self.genetic_shield.apply_genes(patterns)

        if profile == DefenseProfile.GOD_MODE:
            patterns = patterns + self.TRUTH_ANCHOR_PATTERNS + self.IDENTITY_PATTERNS


        for pattern in patterns:
            if (self._safe_re_search(pattern, clean_content, re.IGNORECASE) or 
                (profile != DefenseProfile.BASIC and self._safe_re_search(pattern, flattened_content, re.IGNORECASE)) or
                (profile != DefenseProfile.BASIC and self._safe_re_search(pattern, leeted_content, re.IGNORECASE)) or
                (profile != DefenseProfile.BASIC and self._safe_re_search(pattern, synthetic_context, re.IGNORECASE))):
                packet.metadata["pollution_detected"] = True
                packet.metadata["pollution_reason"] = f"Matched pattern: {pattern}"
                break

        # 8. Dynamic Simulation Defense (ADVANCED+)
        if not packet.metadata["pollution_detected"] and profile != DefenseProfile.BASIC:
            simulated_intent = self.simulator.simulate_outcome(content)
            # Only do full context simulation in GOD_MODE
            sim_list = [simulated_intent]
            if profile == DefenseProfile.GOD_MODE:
                sim_list.append(self.simulator.simulate_outcome(synthetic_context))
            
            for intent in sim_list:
                if intent != content:
                    for pattern in patterns:
                        if self._safe_re_search(pattern, intent, re.IGNORECASE):
                            packet.metadata["pollution_detected"] = True
                            packet.metadata["pollution_reason"] = f"Cognitive Simulation revealed hidden command"
                            break
                    if packet.metadata["pollution_detected"]: break
        
        # 9. Mirage Flag (GOD_MODE ONLY)
        if profile == DefenseProfile.GOD_MODE and any(self._safe_re_search(p, content, re.IGNORECASE) for p in self.IDENTITY_PATTERNS):
             packet.metadata["mirage_active"] = True

        # Update packet content with sanitized version
        packet.content = content

        # Dynamic Downgrade
        if packet.metadata["pollution_detected"]:
            packet = self._downgrade(packet)
        
        return packet
