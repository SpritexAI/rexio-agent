import os
import sys
import tty
import termios
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.text import Text

# Add workspace to python path so rexio_agent can be imported directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rexio_agent.db.connection import init_db
from rexio_agent.core.config import ENV_PATH, load_environment
from rexio_agent.core.loop import AgentSession

console = Console()

def select_option(prompt_text: str, choices: list, default_idx: int = 0) -> str:
    """Helper to render a beautiful arrow-key based selection list in terminal."""
    sys.stdout.write(f"\033[1;36m? \033[1;37m{prompt_text}\033[0m\n")
    sys.stdout.flush()
    current_idx = default_idx
    
    # Hide cursor
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    
    try:
        while True:
            # Print choices
            for i, choice in enumerate(choices):
                if i == current_idx:
                    sys.stdout.write(f"  \033[36m❯ {choice}\033[0m\n")
                else:
                    sys.stdout.write(f"    {choice}\n")
                    
            # Move cursor back to the top of the choices list
            sys.stdout.write(f"\033[{len(choices)}A")
            sys.stdout.flush()
            
            # Read character
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                char = sys.stdin.read(1)
                if char == '\x1b':  # Arrow key sequence prefix
                    char2 = sys.stdin.read(1)
                    char3 = sys.stdin.read(1)
                    if char3 == 'A':  # Up
                        current_idx = (current_idx - 1) % len(choices)
                    elif char3 == 'B':  # Down
                        current_idx = (current_idx + 1) % len(choices)
                elif char in ('\r', '\n'):
                    break
                elif char == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                
            # Clear lines for redraw
            for _ in range(len(choices)):
                sys.stdout.write("\033[K\n")
            sys.stdout.write(f"\033[{len(choices)}A")
            sys.stdout.flush()
            
    finally:
        # Show cursor and clean options
        for _ in range(len(choices)):
            sys.stdout.write("\033[K\n")
        # Move up to prompt header
        sys.stdout.write(f"\033[{len(choices) + 1}A")
        sys.stdout.write("\033[K")
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        
    # Print final selected answer on the same line as the prompt
    print(f"\033[1;36m? \033[1;37m{prompt_text}\033[0m \033[36m{choices[current_idx]}\033[0m")
    return choices[current_idx]

def run_setup_wizard(env_path: str) -> None:
    """Runs an interactive CLI setup wizard to configure the API keys and models."""
    from rexio_agent.db.connection import DB_PATH
    
    # 1. Print the premium boxed welcome header
    console.print()
    console.print("[bold cyan]┌─────────────────────────────────────────────────────────┐[/]")
    console.print("[bold cyan]│            ☤ RexiO Agent Setup Wizard                 │[/]")
    console.print("[bold cyan]├─────────────────────────────────────────────────────────┤[/]")
    console.print("[bold cyan]│  Let's configure your RexiO Agent environment.          │[/]")
    console.print("[bold cyan]│  Press Ctrl+C at any time to exit.                      │[/]")
    console.print("[bold cyan]└─────────────────────────────────────────────────────────┘[/]")
    console.print()

    install_dir = os.path.dirname(os.path.abspath(__file__))
    
    console.print("[bold cyan]◆ Configuration Locations[/]")
    console.print(f"  [bold]Environment File (.env):[/] {env_path}")
    console.print(f"  [bold]Database Path (SQLite):[/]  {DB_PATH}")
    console.print(f"  [bold]Install Directory:[/]       {install_dir}")
    console.print()

    # Load existing configuration defaults if present
    current_provider = ""
    current_model = ""
    current_gemini_key = ""
    current_openai_key = ""
    current_api_base = ""
    current_telegram_token = ""
    current_telegram_chat_id = ""
    current_discord_token = ""
    current_discord_channel_id = ""

    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        current_provider = os.getenv("MODEL_PROVIDER", "").lower()
        current_model = os.getenv("MODEL_NAME", "")
        current_gemini_key = os.getenv("GEMINI_API_KEY", "")
        current_openai_key = os.getenv("OPENAI_API_KEY", "")
        current_api_base = os.getenv("API_BASE_URL", "")
        current_telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        current_telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        current_discord_token = os.getenv("DISCORD_BOT_TOKEN", "")
        current_discord_channel_id = os.getenv("DISCORD_CHANNEL_ID", "")

    provider_labels = {
        "gemini": "Google Gemini",
        "openai": "OpenAI",
        "openrouter": "OpenRouter",
        "custom": "Custom Endpoint (Local / Ollama / Custom API)"
    }

    # Show active configurations
    active_provider_label = provider_labels.get(current_provider, "none") if (os.path.exists(env_path) and current_provider) else "none"
    active_model_label = current_model if current_model else "(not set)"
    
    console.print(f"  [bold]Current Model:[/]    {active_model_label}")
    console.print(f"  [bold]Active Provider:[/]  {active_provider_label}")
    console.print()

    # 2. Select LLM Provider
    provider_choices = ["gemini", "openai", "openrouter", "custom"]
    display_choices = []
    default_provider_idx = 0
    
    for i, p in enumerate(provider_choices):
        label = provider_labels[p]
        if p == current_provider and os.path.exists(env_path):
            display_choices.append(f"{label}  ← currently active")
            default_provider_idx = i
        else:
            display_choices.append(label)
            
    selected_display = select_option("Select LLM Provider", display_choices, default_idx=default_provider_idx)
    selected_idx = display_choices.index(selected_display)
    provider = provider_choices[selected_idx]
    
    # 3. Model Name
    if not current_model:
        if provider == "gemini":
            default_model = "gemini-2.5-flash"
        elif provider == "openrouter":
            default_model = "google/gemini-2.5-flash"
        else:
            default_model = "gpt-4o"
    else:
        default_model = current_model
        
    model_name = Prompt.ask("Enter Model Name", default=default_model)
    
    # 4. API Credentials Configuration
    gemini_key = ""
    openai_key = ""
    api_base_url = ""
    
    if provider == "gemini":
        if current_gemini_key:
            mask_preview = f"{current_gemini_key[:4]}...{current_gemini_key[-4:] if len(current_gemini_key) > 8 else ''}"
            keep_existing = select_option(f"An existing GEMINI_API_KEY is configured ({mask_preview}). Keep it?", ["yes", "no"], default_idx=0)
            if keep_existing == "yes":
                gemini_key = current_gemini_key
            else:
                gemini_key = Prompt.ask("Enter new GEMINI_API_KEY", password=True)
        else:
            gemini_key = Prompt.ask("Enter your GEMINI_API_KEY (masking inputs)", password=True)
            while not gemini_key.strip():
                gemini_key = Prompt.ask("GEMINI_API_KEY cannot be empty. Please enter key", password=True)
                
    elif provider == "openai":
        if current_openai_key:
            mask_preview = f"{current_openai_key[:4]}...{current_openai_key[-4:] if len(current_openai_key) > 8 else ''}"
            keep_existing = select_option(f"An existing OPENAI_API_KEY is configured ({mask_preview}). Keep it?", ["yes", "no"], default_idx=0)
            if keep_existing == "yes":
                openai_key = current_openai_key
            else:
                openai_key = Prompt.ask("Enter new OPENAI_API_KEY", password=True)
        else:
            openai_key = Prompt.ask("Enter your OPENAI_API_KEY (masking inputs)", password=True)
            while not openai_key.strip():
                openai_key = Prompt.ask("OPENAI_API_KEY cannot be empty. Please enter key", password=True)
                
    elif provider == "openrouter":
        if current_openai_key:
            mask_preview = f"{current_openai_key[:4]}...{current_openai_key[-4:] if len(current_openai_key) > 8 else ''}"
            keep_existing = select_option(f"An existing OpenRouter API Key is configured ({mask_preview}). Keep it?", ["yes", "no"], default_idx=0)
            if keep_existing == "yes":
                openai_key = current_openai_key
            else:
                openai_key = Prompt.ask("Enter new OpenRouter API Key", password=True)
        else:
            openai_key = Prompt.ask("Enter your OpenRouter API Key (masking inputs)", password=True)
            while not openai_key.strip():
                openai_key = Prompt.ask("OpenRouter API Key cannot be empty. Please enter key", password=True)
        api_base_url = "https://openrouter.ai/api/v1"
        
    else:
        openai_key = Prompt.ask("Enter your API Key (e.g. Ollama API key)", default=current_openai_key)
        api_base_url = Prompt.ask("Enter custom API Base URL (e.g. http://localhost:11434/v1)", default=current_api_base or "http://localhost:11434/v1")

    # 5. Telegram Gateway Integration
    telegram_token = ""
    telegram_chat_id = ""
    default_telegram_idx = 1 if not current_telegram_token else 0
    configure_telegram = select_option("Do you want to configure Telegram Bot Gateway?", ["yes", "no"], default_idx=default_telegram_idx)
    if configure_telegram == "yes":
        telegram_token = Prompt.ask("Enter Telegram Bot Token", default=current_telegram_token)
        telegram_chat_id = Prompt.ask("Enter Telegram Chat ID", default=current_telegram_chat_id)

    # 6. Discord Gateway Integration
    discord_token = ""
    discord_channel_id = ""
    default_discord_idx = 1 if not current_discord_token else 0
    configure_discord = select_option("Do you want to configure Discord Bot Gateway?", ["yes", "no"], default_idx=default_discord_idx)
    if configure_discord == "yes":
        discord_token = Prompt.ask("Enter Discord Bot Token", default=current_discord_token)
        discord_channel_id = Prompt.ask("Enter Discord Channel ID", default=current_discord_channel_id)

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
        
    # 7. Print tool & configuration availability summary (matching Hermes)
    console.print("\n[bold cyan]◆ Configuration Summary[/]")
    console.print(f"  [bold]LLM Provider:[/]  [green]{provider}[/]")
    console.print(f"  [bold]Model Name:[/]    [green]{model_name}[/]")
    
    key_configured = False
    if provider == "gemini" and gemini_key:
        key_configured = True
    elif provider in ("openai", "openrouter") and openai_key:
        key_configured = True
    elif provider == "custom":
        key_configured = True
        
    if key_configured:
        console.print("  [bold]API Credentials:[/] [bold green]✓ Configured[/]")
    else:
        console.print("  [bold]API Credentials:[/] [bold red]✗ Missing / Empty[/]")
        
    if telegram_token and telegram_chat_id:
        console.print("  [bold]Telegram Gateway:[/] [bold green]✓ Enabled[/]")
    else:
        console.print("  [bold]Telegram Gateway:[/] [dim]Disabled[/]")
        
    if discord_token and discord_channel_id:
        console.print("  [bold]Discord Gateway:[/]  [bold green]✓ Enabled[/]")
    else:
        console.print("  [bold]Discord Gateway:[/]  [dim]Disabled[/]")
        
    db_status = "[bold green]✓ Initialized[/]" if os.path.exists(DB_PATH) else "[yellow]Pending Init[/]"
    console.print(f"  [bold]Local Database:[/]   {db_status}")
    console.print("\n[bold green]🎉 Configuration saved successfully to .env![/]\n")

def run_update_wizard() -> None:
    """Updates the RexiO Agent installation by pulling the latest code and syncing package dependencies."""
    import subprocess
    import shutil
    
    console.print()
    console.print("[bold cyan]┌─────────────────────────────────────────────────────────┐[/]")
    console.print("[bold cyan]│            ☤ RexiO Agent Update Manager               │[/]")
    console.print("[bold cyan]├─────────────────────────────────────────────────────────┤[/]")
    console.print("[bold cyan]│  Checking for updates and updating dependencies...      │[/]")
    console.print("[bold cyan]│  Press Ctrl+C to abort.                                 │[/]")
    console.print("[bold cyan]└─────────────────────────────────────────────────────────┘[/]")
    console.print()

    install_dir = os.path.dirname(os.path.abspath(__file__))
    git_dir = os.path.join(install_dir, ".git")

    if not os.path.exists(git_dir):
        console.print("[bold red]✗ Not a git repository.[/] Please update manually or run the installer script:")
        console.print("  [bold]curl -fsSL https://agent.rexio.pro/install.sh | bash[/]")
        sys.exit(1)

    console.print("🔄 [yellow]Fetching updates from remote...[/]")
    try:
        # Check current commit hash
        curr_hash_res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=install_dir, capture_output=True, text=True, check=True)
        curr_hash = curr_hash_res.stdout.strip()
        
        # Git fetch
        subprocess.run(["git", "fetch", "origin", "main"], cwd=install_dir, check=True, capture_output=True)
        
        # Check if remote has new commits
        status_res = subprocess.run(["git", "rev-list", "HEAD..origin/main", "--count"], cwd=install_dir, capture_output=True, text=True, check=True)
        new_commits_count = int(status_res.stdout.strip())
        
        if new_commits_count == 0:
            console.print(f"[bold green]✓ Up to date![/] RexiO is already on the latest commit ([cyan]{curr_hash}[/cyan]).")
        else:
            console.print(f"📥 [yellow]Found {new_commits_count} new commit(s). Pulling updates...[/]")
            subprocess.run(["git", "pull", "origin", "main"], cwd=install_dir, check=True)
            new_hash_res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=install_dir, capture_output=True, text=True, check=True)
            new_hash = new_hash_res.stdout.strip()
            console.print(f"[bold green]✓ Code updated successfully:[/] [cyan]{curr_hash}[/cyan] ➔ [cyan]{new_hash}[/cyan]")
            
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]✗ Git error during update:[/] {e.stderr.strip() if e.stderr else str(e)}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]✗ Unexpected error during update:[/] {str(e)}")
        sys.exit(1)

    # Re-install dependencies inside the venv
    console.print("\n⚡ [yellow]Syncing and updating package dependencies...[/]")
    
    # Locate virtualenv python
    is_windows = sys.platform == "win32"
    if is_windows:
        pip_bin = os.path.join(install_dir, ".venv", "Scripts", "pip.exe")
    else:
        pip_bin = os.path.join(install_dir, ".venv", "bin", "pip")

    # Locate uv
    uv_bin = shutil.which("uv")

    try:
        if uv_bin and os.path.exists(os.path.join(install_dir, ".venv")):
            console.print("🪄 [cyan]Detected 'uv' package manager. Using fast-installer...[/]")
            subprocess.run([uv_bin, "pip", "install", "-e", "."], cwd=install_dir, check=True)
        else:
            console.print("📦 [cyan]Using standard pip...[/]")
            if os.path.exists(pip_bin):
                subprocess.run([pip_bin, "install", "-e", "."], cwd=install_dir, check=True)
            else:
                subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], cwd=install_dir, check=True)
                
        console.print("[bold green]✓ Dependencies re-installed and compiled successfully.[/]")
        console.print("\n[bold green]🎉 RexiO Agent update complete![/]\n")
    except subprocess.CalledProcessError as e:
        console.print("[bold red]✗ Failed to compile and install package dependencies.[/]")
        sys.exit(1)

def main():
    # 1. Check for update request
    if len(sys.argv) > 1 and sys.argv[1] in ("update", "--update"):
        try:
            run_update_wizard()
            sys.exit(0)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Update cancelled.[/]")
            sys.exit(1)

    env_path = ENV_PATH
    
    # Run setup wizard if configuration does not exist, if explicitly requested via 'setup' / '--setup', or if keys are empty
    should_run_setup = not os.path.exists(env_path) or (len(sys.argv) > 1 and sys.argv[1] in ("setup", "--setup"))
    
    if should_run_setup:
        try:
            run_setup_wizard(env_path)
            # Re-load env configuration
            load_dotenv(env_path, override=True)
            # If setup was explicitly requested as a CLI argument, exit after completion
            if len(sys.argv) > 1 and sys.argv[1] in ("setup", "--setup"):
                sys.exit(0)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Setup cancelled.[/]")
            sys.exit(1)

    if not should_run_setup and os.path.exists(env_path):
        load_dotenv(env_path, override=True)
        provider = os.getenv("MODEL_PROVIDER", "gemini").lower()
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")
        
        if (provider == "gemini" and not gemini_key) or (provider == "openai" and not openai_key):
            console.print("[yellow]Warning:[/] Configuration credentials appear to be missing.")
            if select_option("Would you like to run the setup wizard now?", ["yes", "no"], default_idx=0) == "yes":
                try:
                    run_setup_wizard(env_path)
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
    
    console.print(Panel(Text("Welcome to RexiO Agent ☤\nType 'exit' or 'quit' to end the session.", style="bold cyan", justify="center")))
    
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
                
            console.print(Panel(Text(response, style="white"), title="RexiO"))
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Session ended.[/]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error running agent loop:[/] {str(e)}\n")

if __name__ == "__main__":
    main()
