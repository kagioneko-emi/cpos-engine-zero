import subprocess
import json
import os

class GeminiArchitect:
    """Uses Gemini CLI to generate code fixes based on analysis and sandbox results."""
    
    def __init__(self, model="gemini"):
        self.model = model

    def _run_gemini(self, prompt):
        # Ensure GOOGLE_API_KEY is set for the CLI if GEMINI_API_KEY is present
        env = os.environ.copy()
        if "GEMINI_API_KEY" in env and "GOOGLE_API_KEY" not in env:
            env["GOOGLE_API_KEY"] = env["GEMINI_API_KEY"]
            
        cmd = ["gemini", "--skip-trust", "-p", prompt]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
            return result.stdout.strip().strip("`").replace("python\n", "", 1)
        except subprocess.CalledProcessError as e:
            print(f"Error calling Gemini CLI (Exit {e.returncode}):")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            return None

    def create_test_from_spec(self, spec_title, spec_body, target_module_name):
        prompt = f"""
As a Senior QA Engineer, your task is to write a comprehensive Pytest suite for a new Python module.

Module Name to test: {target_module_name}
Specification: {spec_title} - {spec_body}

Requirements:
1. Provide the COMPLETE Python code for the test file (e.g., test_{target_module_name}.py).
2. Use `pytest` framework.
3. Cover edge cases and normal scenarios based on the spec.
4. Output ONLY the raw Python code. Do not include markdown formatting.
"""
        return self._run_gemini(prompt)

    def propose_fix_from_test(self, file_path, current_code, test_code, test_output):
        prompt = f"""
The Python code you generated failed its tests. Please fix it.

File: {file_path}
Current Code:
---
{current_code}
---

Test Code:
---
{test_code}
---

Test Failure Output:
---
{test_output}
---

Please provide the corrected COMPLETE Python code for {file_path}.
Output ONLY the raw Python code.
"""
        return self._run_gemini(prompt)

    def create_from_spec(self, spec_title, spec_body):
        prompt = f"""
As a Senior Python Developer, your task is to create a new, high-quality Python module based on the following specification.

Specification Title: {spec_title}
Specification Detail: {spec_body}

Requirements:
1. Provide the COMPLETE Python code for the new module.
2. Include necessary imports and follow PEP8 style.
3. Add a basic __main__ block or a test-friendly structure.
4. Output ONLY the raw Python code. Do not include markdown formatting or explanations.

The code must be production-ready and follow defensive coding principles.
"""
        return self._run_gemini(prompt)

    def propose_fix(self, file_path, content, finding, sandbox_output=None):
        description = finding.get('description', finding.get('title', 'Unknown issue'))
        fix_hint = finding.get('fix', 'No specific hint available.')
        
        prompt = f"""
As a Senior DevOps Engineer, your task is to fix a reliability/security issue in a Python project.

File: {file_path}
Issue: {finding.get('title', 'Unknown')} (Severity: {finding.get('severity', 'Unknown')})
Description: {description}
Hint: {fix_hint}
Line: {finding.get('line', 'Unknown')}

Original Code at Line {finding.get('line', 'Unknown')}:
{finding.get('content', 'N/A')}

Sandbox/Lint Output:
{sandbox_output if sandbox_output else "No additional errors reported."}

Full File Content:
---
{content}
---

Please provide the corrected code for the ENTIRE file. 
Output ONLY the raw Python code. Do not include markdown formatting or explanations.
Ensure the fix follows best practices and maintains existing functionality.
"""
        
        fixed_code = self._run_gemini(prompt)
        if fixed_code:
            # Clean up potential markdown blocks if Gemini ignored the instruction
            if fixed_code.startswith("```python"):
                fixed_code = fixed_code.split("```python")[1].split("```")[0].strip()
            elif fixed_code.startswith("```"):
                fixed_code = fixed_code.split("```")[1].split("```")[0].strip()
                
            return fixed_code
        return None

if __name__ == "__main__":
    # Test stub
    arch = GeminiArchitect()
    test_finding = {
        "title": "unsafe eval",
        "severity": "high",
        "description": "Potential arbitrary code execution via eval()",
        "line": 10,
        "content": "    return eval(expr)"
    }
    test_content = "def calculate(expr):\n    return eval(expr)\n\nprint(calculate('1+1'))"
    fix = arch.propose_fix("test.py", test_content, test_finding)
    print("--- Propose Fix ---")
    print(fix)
