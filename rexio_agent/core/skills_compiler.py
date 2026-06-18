import os
import re
from typing import List, Dict, Any, Tuple, Optional
from rexio_agent.core.llm import LlmClient
from rexio_agent.db.connection import save_skill

SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")

COMPILER_PROMPT_TEMPLATE = """You are a software engineer specializing in code consolidation.
Review the following execution log of a task solved by an AI agent using step-by-step tools.

Task Description:
{task_description}

Execution Log:
{execution_log}

Your job is to consolidate these steps into a single, clean, reusable Python function.

Guidelines:
1. The function must be generic and reusable. Do not hardcode input arguments if they can be parameterized.
2. The function name must be a clean snake_case identifier (e.g. `fetch_weather_report`, `compress_files`).
3. The function must contain a clear docstring describing its arguments, return values, and what it does. The docstring will be parsed to register it as a tool.
4. The function must return a string representing the output/result of the action.
5. Import any necessary standard libraries inside the function body or at the top of the code.
6. The output must be valid, executable Python code.

Format your output exactly like this:
```python
# A single python code block containing the function definition.
```
"""

class SkillCompiler:
    def __init__(self):
        self.llm = LlmClient()

    def compile_and_save(self, task_description: str, execution_log: List[Dict[str, Any]]) -> Optional[str]:
        """
        Analyzes execution history, compiles it into a reusable Python tool, and saves it.
        Returns the name of the newly compiled skill if successful, else None.
        """
        # Format execution log into text representation
        log_text = ""
        for i, step in enumerate(execution_log):
            log_text += f"Step {i+1}:\n"
            if "thought" in step and step["thought"]:
                log_text += f"Thought: {step['thought']}\n"
            if "tool" in step:
                log_text += f"Tool Called: {step['tool']}({step.get('args', '')})\n"
            if "observation" in step:
                log_text += f"Observation: {step['observation']}\n"
            log_text += "---\n"

        prompt = COMPILER_PROMPT_TEMPLATE.format(
            task_description=task_description,
            execution_log=log_text
        )

        try:
            system_instruction = "You are an expert Python compiler assistant. Generate clean, modular, human-like Python code."
            response_text = self.llm.generate(
                system_instruction=system_instruction,
                prompt=prompt
            )

            # Extract python code block
            code_match = re.search(r'```python\s*(.*?)\s*```', response_text, re.DOTALL)
            code = code_match.group(1).strip() if code_match else response_text.strip()

            if not code:
                return None

            # Extract function name from code definition: def function_name(...)
            func_name_match = re.search(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', code)
            if not func_name_match:
                return None
            
            skill_name = func_name_match.group(1)

            # Extract docstring from the function code to use as description
            # We look for triple quotes right after the function definition
            docstring_match = re.search(r'def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\(.*?\)\s*(?:->\s*[^:]+)?\s*:\s*"""(.*?)"""', code, re.DOTALL)
            description = docstring_match.group(1).strip() if docstring_match else f"Custom skill: {skill_name}"

            # Save to Database as pending (requires human approval before activation)
            save_skill(skill_name, description, code, status='pending')

            # Save to local file system
            os.makedirs(SKILLS_DIR, exist_ok=True)
            skill_file_path = os.path.join(SKILLS_DIR, f"{skill_name}.py")
            with open(skill_file_path, "w", encoding="utf-8") as f:
                f.write(code)

            return skill_name

        except Exception as e:
            print(f"Error compiling skill: {str(e)}")
            return None
