import os
from typing import List

def read_file(path: str) -> str:
    """
    Reads the content of a file at the specified path and returns it as a string.
    
    Args:
        path (str): The absolute or relative path to the file to read.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_file(path: str, content: str) -> str:
    """
    Writes or overwrites the content of a file at the specified path.
    Creates parent directories if they do not exist.
    
    Args:
        path (str): The absolute or relative path to the file to write.
        content (str): The text content to write to the file.
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File successfully written to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

def list_directory(path: str = ".") -> str:
    """
    Lists files and directories in the specified path.
    
    Args:
        path (str): The directory path to list. Defaults to current directory '.'.
    """
    try:
        items = os.listdir(path)
        result = []
        for item in items:
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                result.append(f"[DIR]  {item}")
            else:
                result.append(f"[FILE] {item}")
        return "\n".join(result) if result else "Directory is empty."
    except Exception as e:
        return f"Error listing directory: {str(e)}"
