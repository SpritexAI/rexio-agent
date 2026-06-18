import sys
import io
import traceback
from multiprocessing import Process, Queue
from typing import Dict, Any

def _run_code_target(code: str, queue: Queue) -> None:
    """Target function executed in a separate process to run Python code."""
    # Redirect stdout and stderr
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    sys.stdout = stdout_buf
    sys.stderr = stderr_buf
    
    # Execute the code in a clean global scope
    global_vars: Dict[str, Any] = {}
    error = None
    try:
        # Note: we use exec to execute the string
        exec(code, global_vars)
    except Exception:
        error = traceback.format_exc()
    finally:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        
    stdout_val = stdout_buf.getvalue()
    stderr_val = stderr_buf.getvalue()
    
    queue.put({
        "stdout": stdout_val,
        "stderr": stderr_val,
        "error": error
    })

def execute_python_code(code: str, timeout_seconds: float = 10.0) -> str:
    """
    Executes a block of Python code in an isolated subprocess and returns the standard output, 
    standard error, and any exception traceback. Keeps execution safe from locking the main process.
    
    Args:
        code (str): The Python code block to execute.
        timeout_seconds (float): Maximum time in seconds to wait for execution before terminating.
    """
    queue: Queue = Queue()
    process = Process(target=_run_code_target, args=(code, queue))
    
    try:
        process.start()
        # Wait up to the timeout
        process.join(timeout=timeout_seconds)
        
        if process.is_alive():
            process.terminate()
            process.join()
            return f"Execution Error: Code execution timed out after {timeout_seconds} seconds."
            
        if queue.empty():
            return "Execution Error: Process terminated unexpectedly without returning output."
            
        result = queue.get()
        output_str = ""
        if result["stdout"]:
            output_str += f"=== STDOUT ===\n{result['stdout']}\n"
        if result["stderr"]:
            output_str += f"=== STDERR ===\n{result['stderr']}\n"
        if result["error"]:
            output_str += f"=== ERROR ===\n{result['error']}\n"
            
        return output_str.strip() if output_str else "Code executed successfully with no output."
        
    except Exception as e:
        if process.is_alive():
            process.terminate()
        return f"Execution Error: Failed to run subprocess: {str(e)}"
