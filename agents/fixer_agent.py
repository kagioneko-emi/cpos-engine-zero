import yaml
import os
import json

class FixerAgent:
    def __init__(self, patterns_path):
        self.patterns_path = patterns_path
        self.patterns = []
        self.load_patterns()

    def load_patterns(self):
        if os.path.exists(self.patterns_path):
            with open(self.patterns_path, 'r') as f:
                content = yaml.safe_load(f)
                self.patterns = content if content else []

    def save_patterns(self):
        with open(self.patterns_path, 'w') as f:
            yaml.dump(self.patterns, f, allow_unicode=True)

    def register_fix(self, rule_id, bad_code, good_code, description):
        # すでに同じパターンがないか確認
        for pattern in self.patterns:
            if pattern['rule_id'] == rule_id:
                for case in pattern.get('cases', []):
                    if case['bad'] == bad_code:
                        return # 既知
                pattern.setdefault('cases', []).append({
                    "bad": bad_code,
                    "good": good_code,
                    "verified": True
                })
                self.save_patterns()
                return

        # 新規ルールID
        self.patterns.append({
            "rule_id": rule_id,
            "description": description,
            "cases": [{
                "bad": bad_code,
                "good": good_code,
                "verified": True
            }]
        })
        self.save_patterns()

    def get_suggested_fix(self, rule_id, bad_code):
        for pattern in self.patterns:
            if pattern['rule_id'] == rule_id:
                for case in pattern.get('cases', []):
                    if case['bad'].strip() == bad_code.strip():
                        return case['good']
        return None
