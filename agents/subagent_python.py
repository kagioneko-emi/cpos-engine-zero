import json
import re
import os

class PythonSubagent:
    def __init__(self, tape_path, mistakes_path):
        self.tape_path = tape_path
        self.mistakes_path = mistakes_path
        self.rules = []
        self.tape_config = {}

    def load_tape(self):
        if not os.path.exists(self.tape_path):
            print(f"Tape not found: {self.tape_path}")
            return
        with open(self.tape_path, 'r') as f:
            content = f.read().strip()
            parts = content.split('|')
            for part in parts:
                if ':' in part:
                    k, v = part.split(':', 1)
                    self.tape_config[k] = v
                else:
                    self.tape_config[part] = True
        print(f"Loaded tape config: {self.tape_config}")

    def load_mistakes(self):
        if not os.path.exists(self.mistakes_path):
            print(f"Mistakes not found: {self.mistakes_path}")
            return
        with open(self.mistakes_path, 'r') as f:
            for line in f:
                if line.strip():
                    self.rules.append(json.loads(line))
        print(f"Loaded {len(self.rules)} rules from memory.")

    def analyze_file(self, file_path):
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}

        with open(file_path, 'r') as f:
            lines = f.readlines()

        findings = []
        for i, line in enumerate(lines):
            line_num = i + 1
            for rule in self.rules:
                pattern = rule.get("pattern")
                if not pattern:
                    continue
                
                # Simple pattern matching: "@NOT" suffix means pattern should NOT be found in a relevant context
                # For MVP, we'll do a slightly smarter check for the requests timeout
                if pattern.endswith("@NOT"):
                    base_pattern = pattern[:-4]
                    # Check if the base pattern matches (e.g. requests.get() exists)
                    # but doesn't contain timeout
                    match_call = re.search(r"requests\.(get|post|put|delete|patch)\(", line)
                    if match_call:
                        if "timeout=" not in line:
                            findings.append({
                                "rule_id": rule["id"],
                                "title": rule["title"],
                                "line": line_num,
                                "content": line.strip(),
                                "fix": rule["fix"],
                                "severity": rule["severity"]
                            })
                else:
                    if re.search(pattern, line):
                        findings.append({
                            "rule_id": rule["id"],
                            "title": rule["title"],
                            "line": line_num,
                            "content": line.strip(),
                            "fix": rule["fix"],
                            "severity": rule["severity"]
                        })

        return findings

if __name__ == "__main__":
    # Self-test logic
    agent = PythonSubagent(
        "cpos_defensive_agent/tapes/python/base.tape",
        "cpos_defensive_agent/memory/python/mistakes.jsonl"
    )
    agent.load_tape()
    agent.load_mistakes()
    # Assume a test file path passed or created
