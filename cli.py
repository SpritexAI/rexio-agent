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

def run_setup_wizard(env_path: str) -> None:
    """Runs an interactive CLI setup wizard to configure the API keys and models."""
    console.print(Panel(Text("Aethelis Agent Setup Wizard ☤", style="bold cyan"), title="System Setup"))
    console.print("Let's configure your environment. This will create or update your local [yellow].env[/] file.\n")
    
    # 1. LLM Provider
    provider = Prompt.ask(
        "Select LLM Provider", 
        choices=["gemini", "openai", "openrouter", "custom"], 
        default="gemini"
    ).lower()
    
    # 2. Model Name
    if provider == "gemini":
        default_model = "gemini-2.5-flash"
    elif provider == "openrouter":
        default_model = "google/gemini-2.5-flash"
    else:
        default_model = "gpt-4o"
    model_name = Prompt.ask("Enter Model Name", default=default_model)
    
    # 3. API Keys
    gemini_key = ""
    openai_key = ""
    api_base_url = ""
    
    if provider == "gemini":
        gemini_key = Prompt.ask("Enter your GEMINI_API_KEY (masking inputs)", password=True)
        while not gemini_key.strip():
            gemini_key = Prompt.ask("GEMINI_API_KEY cannot be empty. Please enter key", password=True)
    elif provider == "openai":
        openai_key = Prompt.ask("Enter your OPENAI_API_KEY (masking inputs)", password=True)
        while not openai_key.strip():
            openai_key = Prompt.ask("OPENAI_API_KEY cannot be empty. Please enter key", password=True)
    elif provider == "openrouter":
        openai_key = Prompt.ask("Enter your OpenRouter API Key (masking inputs)", password=True)
        while not openai_key.strip():
            openai_key = Prompt.ask("OpenRouter API Key cannot be empty. Please enter key", password=True)
        api_base_url = "https://openrouter.ai/api/v1"
    else:
        openai_key = Prompt.ask("Enter your API Key (e.g. Ollama API key)", default="")
        api_base_url = Prompt.ask("Enter custom API Base URL (e.g. http://localhost:11434/v1)", default="")

    # 4. Telegram Gateway Integration
    telegram_token = ""
    telegram_chat_id = ""
    configure_telegram = Prompt.ask("Do you want to configure Telegram Bot Gateway?", choices=["y", "n"], default="n")
    if configure_telegram == "y":
        telegram_token = Prompt.ask("Enter Telegram Bot Token")
        telegram_chat_id = Prompt.ask("Enter Telegram Chat ID")

    # 5. Discord Gateway Integration
    discord_token = ""
    discord_channel_id = ""
    configure_discord = Prompt.ask("Do you want to configure Discord Bot Gateway?", choices=["y", "n"], default="n")
    if configure_discord == "y":
        discord_token = Prompt.ask("Enter Discord Bot Token")
        discord_channel_id = Prompt.ask("Enter Discord Channel ID")

    # Construct file content
    env_content = f"""# Model Configuration
MODEL_PROVIDER={provider}
MODEL_NAME={model_name}

# API Keys
GEMINI_API_KEY={gemini_key}
OPENAI_API_KEY={openai_key}
"""
    if api_base_url:
        env_content += f"API_BASE_URL={api_base_url}\n"
        
    if telegram_token:
        env_content += f"\n# Telegram Gateway\nTELEGRAM_BOT_TOKEN={telegram_token}\nTELEGRAM_CHAT_ID={telegram_chat_id}\n"
        
    if discord_token:
        env_content += f"\n# Discord Gateway\nDISCORD_BOT_TOKEN={discord_token}\nDISCORD_CHANNEL_ID={discord_channel_id}\n"
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(env_content)
        
    console.print("\n[bold green]Configuration saved successfully to .env![/]\n")

def main():
    console.print(Panel(Text("Welcome to Aethelis Agent ☤\nType 'exit' or 'quit' to end the session.", style="bold cyan", justify="center")))
    
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    
    # Run setup if .env doesn't exist, if '--setup' is passed, or if keys are empty
    should_run_setup = not os.path.exists(env_path) or (len(sys.argv) > 1 and sys.argv[1] == "--setup")
    
    if not should_run_setup and os.path.exists(env_path):
        load_dotenv(env_path)
        provider = os.getenv("MODEL_PROVIDER", "gemini").lower()
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")
        
        if (provider == "gemini" and not gemini_key) or (provider == "openai" and not openai_key):
            console.print("[yellow]Warning:[/] Configuration credentials appear to be missing.")
            if Prompt.ask("Would you like to run the setup wizard now?", choices=["y", "n"], default="y") == "y":
                should_run_setup = True

    if should_run_setup:
        try:
            run_setup_wizard(env_path)
            # Re-load env configuration
            load_dotenv(env_path, override=True)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Setup cancelled.[/]")
            sys.exit(1)
            
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
