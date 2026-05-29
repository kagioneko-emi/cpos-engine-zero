from agents.fixer_agent import FixerAgent
import os

# Determine project root based on this file's location
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fixer = FixerAgent(os.path.join(project_root, "memory/python/fix_patterns.yaml"))

# 学習 1: shell=True の修正
fixer.register_fix(
    rule_id="PY-MISTAKE-0003",
    description="insecure subprocess with shell=True",
    bad_code='subprocess.run(f"tar -cvf backup.tar {user_provided_path}", shell=True)',
    good_code='subprocess.run(["tar", "-cvf", "backup.tar", user_provided_path], shell=False)'
)

# 学習 2: os.system の修正
fixer.register_fix(
    rule_id="PY-MISTAKE-0004",
    description="unsafe os.system",
    bad_code='os.system("rm -rf /var/log/*.log")',
    good_code='import glob\n    for f in glob.glob("/var/log/*.log"):\n        os.remove(f)'
)

# 学習 3: Hardcoded API Key -> Vault
fixer.register_fix(
    rule_id="PY-MISTAKE-0005",
    description="hardcoded API key",
    bad_code='api_key = "sk-EXAMPLE-REDACTED"',
    good_code='# Fetch from Vault\n    import os\n    from hvac import Client\n    # Note: Use the project standard vault access method\n    api_key = os.getenv("STRIPE_API_KEY") # Or actual vault call: client.secrets.kv.v2.read_secret_version(...)'
)

# 学習 4: requests timeout missing
fixer.register_fix(
    rule_id="PY-MISTAKE-0001",
    description="requests timeout missing",
    bad_code='return requests.get(url).json()',
    good_code='return requests.get(url, timeout=10).json()'
)

print("Memory updated with new learned fix patterns.")
