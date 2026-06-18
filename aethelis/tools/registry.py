import inspect
from typing import Dict, Any, Callable, List, Optional
from aethelis.tools.file_tools import read_file, write_file, list_directory
from aethelis.tools.web_tools import search_web
from aethelis.tools.executor import execute_python_code
from aethelis.db.connection import get_skills

# Built-in tools registry
BUILTIN_TOOLS: Dict[str, Callable] = {
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "search_web": search_web,
    "execute_python_code": execute_python_code
}

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = dict(BUILTIN_TOOLS)
        self.load_custom_skills()
        
    def load_custom_skills(self) -> None:
        """Loads learned skills from the database and adds them to the active tools."""
        try:
            db_skills = get_skills()
            for skill in db_skills:
                name = skill["name"]
                code = skill["code"]
                try:
                    # Execute code to extract the target function
                    local_vars: Dict[str, Any] = {}
                    exec(code, globals(), local_vars)
                    if name in local_vars and callable(local_vars[name]):
                        self.tools[name] = local_vars[name]
                except Exception as e:
                    print(f"Error loading custom skill '{name}': {str(e)}")
        except Exception as e:
            # DB might not be initialized yet
            pass

    def get_tool_definitions(self) -> str:
        """Generates a text description of all available tools, their signatures, and docstrings."""
        definitions = []
        for name, func in self.tools.items():
            sig = inspect.signature(func)
            doc = func.__doc__.strip() if func.__doc__ else "No description available."
            # Clean up indentation in docstring
            doc_cleaned = "\n".join([line.strip() for line in doc.split("\n")])
            definitions.append(f"- {name}{sig}:\n  Description: {doc_cleaned}\n")
            
        # Add the special self-improvement tool description
        definitions.append(
            "- save_recent_workflow_as_tool(task_description: str):\n"
            "  Description: Saves the sequence of steps taken in the current session as a reusable tool.\n"
            "  Call this when you have successfully completed a multi-step task and want to memorize the workflow.\n"
        )
        return "\n".join(definitions)

    def execute(self, name: str, kwargs: Dict[str, Any], execution_log: Optional[List[Dict[str, Any]]] = None) -> str:
        """Executes a tool by name with keyword arguments."""
        if name == "save_recent_workflow_as_tool":
            return self._save_recent_workflow(kwargs.get("task_description", ""), execution_log)
            
        if name not in self.tools:
            return f"Error: Tool '{name}' is not registered."
        
        try:
            func = self.tools[name]
            result = func(**kwargs)
            return str(result)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

    def _save_recent_workflow(self, task_description: str, execution_log: Optional[List[Dict[str, Any]]]) -> str:
        if not execution_log:
            return "Error: No execution log found for this session."
        
        from aethelis.core.skills_compiler import SkillCompiler
        compiler = SkillCompiler()
        skill_name = compiler.compile_and_save(task_description, execution_log)
        
        if skill_name:
            self.load_custom_skills()  # reload to make it active
            return f"Success: Created new tool '{skill_name}' and saved to filesystem/database."
        else:
            return "Error: Could not compile workflow into a valid Python skill tool."
