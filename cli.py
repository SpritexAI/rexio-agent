import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text

# Add workspace to python path so aethelis can be imported directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aethelis.db.connection import init_db
from aethelis.core.loop import AgentSession

console = Console()

def main():
    console.print(Panel(Text("Welcome to Aethelis Agent ☤\nType 'exit' or 'quit' to end the session.", style="bold cyan", justify="center")))
    
    # 1. Check env config
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        console.print("[bold red]Error:[/] .env file not found!")
        console.print("Please copy [bold yellow].env.example[/] to [bold yellow].env[/] and set your API keys.")
        sys.exit(1)
        
    load_dotenv(env_path)
    
    # 2. Initialize database
    try:
        init_db()
    except Exception as e:
        console.print(f"[bold red]Database Init Error:[/] {str(e)}")
        sys.exit(1)
        
    # 3. Create agent session
    try:
        session = AgentSession(platform="cli", channel_id="terminal_session")
    except Exception as e:
        console.print(f"[bold red]Initialization Error:[/] {str(e)}")
        console.print("Make sure your API keys are correctly set in the [bold].env[/] file.")
        sys.exit(1)
        
    console.print("[bold green]Agent initialized and ready.[/]\n")
    
    # 4. Interactive chat loop
    while True:
        try:
            user_msg = Prompt.ask("[bold magenta]You[/]")
            if user_msg.strip().lower() in ["exit", "quit"]:
                console.print("[bold yellow]Goodbye![/]")
                break
                
            if not user_msg.strip():
                continue
                
            with console.status("[bold cyan]Agent is thinking...[/]"):
                response = session.run(user_msg)
                
            console.print(Panel(Text(response, style="white"), title="Aethelis"))
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Session ended.[/]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error running agent loop:[/] {str(e)}\n")

if __name__ == "__main__":
    main()
