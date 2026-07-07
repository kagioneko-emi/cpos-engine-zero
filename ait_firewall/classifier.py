import re
from .packet import AITPacket

class InputClassifier:
    def __init__(self):
        # Basic source mapping (can be expanded)
        self.source_trust = {
            "SYSTEM": 1.0,
            "ADMIN": 1.0,
            "USER": 0.8,
            "MEMORY": 0.6,
            "TOOL": 0.4,
            "WEB": 0.2,
            "IMAGE": 0.2,
            "PDF": 0.2,
            "VIDEO": 0.2,
            "AUDIO": 0.2
        }

    def classify(self, content: str, source: str) -> AITPacket:
        trust = self.source_trust.get(source, 0.1)
        
        # Simple heuristic: if source is WEB, TOOL, IMAGE, PDF, VIDEO, or AUDIO, it's DATA
        if source in ["WEB", "TOOL", "IMAGE", "PDF", "VIDEO", "AUDIO"]:
            p_type = "DATA"
        elif source in ["SYSTEM", "ADMIN"]:
            p_type = "INSTRUCTION"
        else:
            p_type = "INSTRUCTION" # USER defaults to INSTRUCTION

        return AITPacket(
            content=content,
            source=source,
            type=p_type,
            trust=trust
        )
