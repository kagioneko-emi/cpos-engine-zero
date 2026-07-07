from .packet import AITPacket

class PolicyEngine:
    def __init__(self):
        self.default_deny = ["SYSTEM_OVERRIDE", "SECRET_ACCESS", "TOOL_EXEC"]

    def apply(self, packet: AITPacket) -> AITPacket:
        # Rule 1: DATA is restricted
        if packet.type == "DATA":
            packet.deny.extend(self.default_deny)
            packet.permissions = ["READ", "SUMMARIZE"]

        # Rule 2: Low trust ( < 0.5) cannot call tools or access secrets
        if packet.trust < 0.5:
            if "TOOL_EXEC" not in packet.deny:
                packet.deny.append("TOOL_EXEC")
            if "SECRET_ACCESS" not in packet.deny:
                packet.deny.append("SECRET_ACCESS")

        # Rule 3: High trust ( > 0.9) can do anything
        if packet.trust >= 0.9:
            packet.permissions = ["ALL"]
            packet.deny = []

        # Deduplicate
        packet.deny = list(set(packet.deny))
        packet.permissions = list(set(packet.permissions))
        
        return packet
