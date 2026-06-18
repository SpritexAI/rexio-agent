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
from rexio_agent.core.config import CONFIG_PATH, load_environment, save_config
from rexio_agent.core.loop import AgentSession

console = Console()

def select_option(prompt_text: str, choices: list, default_idx: int = 0) -> str:
    """Helper to render a beautiful arrow-key based selection list in terminal, matching Hermes TUI."""
    # Print header
    sys.stdout.write(f"\033[1;33mSelect {prompt_text.replace('Select ', '')}:\033[0m\n")
    sys.stdout.write("  \033[2m↑↓ navigate  ENTER/SPACE select  Ctrl+C exit\033[0m\n\n")
    sys.stdout.flush()
    current_idx = default_idx
    visible_limit = 10
    scroll_offset = 0
    last_rendered_lines = 0
    
    # Hide cursor
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    
    try:
        while True:
            # 1. Clear previous render (if any) to redraw in place
            if last_rendered_lines > 0:
                for _ in range(last_rendered_lines):
                    sys.stdout.write("\033[K\n")
                sys.stdout.write(f"\033[{last_rendered_lines}A")
                sys.stdout.flush()
                
            # 2. Compute viewport offsets to keep the selection centered/in view
            if current_idx < scroll_offset:
                scroll_offset = current_idx
            elif current_idx >= scroll_offset + visible_limit:
                scroll_offset = current_idx - visible_limit + 1
            scroll_offset = max(0, min(scroll_offset, max(0, len(choices) - visible_limit)))
            
            rendered_choices = choices[scroll_offset : scroll_offset + visible_limit]
            
            # 3. Print current choices with pagination indicators if necessary
            rendered_lines = 0
            if scroll_offset > 0:
                sys.stdout.write("     \033[2m▲ ...\033[0m\n")
                rendered_lines += 1
                
            for i, choice in enumerate(rendered_choices):
                actual_idx = scroll_offset + i
                if actual_idx == current_idx:
                    # Selected: Green arrow ➔, filled circle (●), and bold green text
                    sys.stdout.write(f"\033[1;32m➔ (●) {choice}\033[0m\n")
                else:
                    # Unselected: empty circle (o) and normal text
                    sys.stdout.write(f"   (o) {choice}\n")
                rendered_lines += 1
                
            if scroll_offset + visible_limit < len(choices):
                sys.stdout.write("     \033[2m▼ ...\033[0m\n")
                rendered_lines += 1
                
            # Move cursor back to the top of the choices list for drawing
            sys.stdout.write(f"\033[{rendered_lines}A")
            sys.stdout.flush()
            
            last_rendered_lines = rendered_lines
            
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
                elif char in ('\r', '\n', ' '): # Enter or Space
                    break
                elif char == '\x03':  # Ctrl+C
                    raise KeyboardInterrupt()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                
    finally:
        # Show cursor and clean options from terminal scrollback
        if last_rendered_lines > 0:
            for _ in range(last_rendered_lines):
                sys.stdout.write("\033[K\n")
            sys.stdout.write(f"\033[{last_rendered_lines + 3}A")
        else:
            sys.stdout.write("\033[3A")
        sys.stdout.write("\033[K\n\033[K\n\033[K")
        sys.stdout.write("\033[2A") # Move back to the first line
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        
    # Print final selected answer on the same line as the prompt
    clean_choice = choices[current_idx].split("  ←")[0]
    print(f"\033[1;33mSelect {prompt_text.replace('Select ', '')}:\033[0m \033[1;32m{clean_choice}\033[0m\n")
    return choices[current_idx]

def fetch_provider_models(provider: str, api_key: str, api_base_url: str = "") -> list[str]:
    """Fetch model names from the provider using the specified API key.
    Returns a list of model display choices, or an empty list if fetching fails.
    """
    import urllib.request
    import json
    
    timeout = 4.0
    
    try:
        if provider == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            req = urllib.request.Request(url)
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            models = []
            for m in data.get("models", []):
                name = m.get("name", "")
                if name.startswith("models/"):
                    name = name[len("models/"):]
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    models.append(name)
            gemini_models = [m for m in models if m.startswith("gemini")]
            gemini_models.sort(reverse=True)
            return gemini_models
            
        elif provider == "openai":
            base_url = api_base_url or "https://api.openai.com/v1"
            url = f"{base_url.rstrip('/')}/models"
            req = urllib.request.Request(url)
            req.add_header("Authorization", f"Bearer {api_key}")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            models = []
            for m in data.get("data", []):
                mid = m.get("id", "")
                if any(term in mid for term in ("embed", "whisper", "dall-e", "tts", "moderation", "babbage", "davinci", "similarity")):
                    continue
                if "gpt" in mid or "o1" in mid or "o3" in mid:
                    models.append(mid)
            models.sort()
            return models
            
        elif provider == "openrouter":
            url = "https://openrouter.ai/api/v1/models"
            req = urllib.request.Request(url)
            if api_key:
                req.add_header("Authorization", f"Bearer {api_key}")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            models = []
            for m in data.get("data", []):
                mid = m.get("id", "")
                name = m.get("name", "")
                if mid:
                    if name:
                        models.append(f"{mid}  ({name})")
                    else:
                        models.append(mid)
            models.sort()
            return models
            
        elif provider == "custom":
            if not api_base_url:
                return []
            url = f"{api_base_url.rstrip('/')}/models"
            req = urllib.request.Request(url)
            if api_key:
                req.add_header("Authorization", f"Bearer {api_key}")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
            models = []
            for m in data.get("data", []):
                mid = m.get("id", "")
                if mid:
                    models.append(mid)
            models.sort()
            return models
            
    except Exception:
        pass
        
    return []

def run_setup_wizard(config_path: str) -> None:
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
    console.print(f"  [bold]Configuration File (JSON):[/] {config_path}")
    console.print(f"  [bold]Database Path (SQLite):[/]    {DB_PATH}")
    console.print(f"  [bold]Install Directory:[/]         {install_dir}")
    console.print()

    # Load existing configuration defaults if present
    current_provider = ""
    current_model = ""
    current_gemini_key = ""
    current_openai_key = ""
    current_openrouter_key = ""
    current_api_base = ""
    current_telegram_token = ""
    current_telegram_chat_id = ""
    current_discord_token = ""
    current_discord_channel_id = ""

    if os.path.exists(config_path):
        load_environment()
        current_provider = os.getenv("MODEL_PROVIDER", "").lower()
        current_model = os.getenv("MODEL_NAME", "")
        current_gemini_key = os.getenv("GEMINI_API_KEY", "")
        current_openai_key = os.getenv("OPENAI_API_KEY", "")
        current_openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        current_api_base = os.getenv("API_BASE_URL", "")
        current_telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        current_telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        current_discord_token = os.getenv("DISCORD_BOT_TOKEN", "")
        current_discord_channel_id = os.getenv("DISCORD_CHANNEL_ID", "")

    provider_labels = {
        "gemini": "Google Gemini (Gemini models - native Gemini API)",
        "openai": "OpenAI (GPT-4o, o1, and compatible models)",
        "openrouter": "OpenRouter (100+ models, pay-per-use)",
        "custom": "Custom Endpoint (Local / Ollama / Custom API)"
    }

    # Show active configurations
    active_provider_label = provider_labels.get(current_provider, "none") if (os.path.exists(config_path) and current_provider) else "none"
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
        if p == current_provider and os.path.exists(config_path):
            display_choices.append(f"{label}  ← currently active")
            default_provider_idx = i
        else:
            display_choices.append(label)
            
    selected_display = select_option("Select LLM Provider", display_choices, default_idx=default_provider_idx)
    selected_idx = display_choices.index(selected_display)
    provider = provider_choices[selected_idx]
    
    # 3. API Credentials Configuration (Moved to Step 3, before Model Selection)
    gemini_key = ""
    openai_key = ""
    openrouter_key = ""
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
        if current_openrouter_key:
            mask_preview = f"{current_openrouter_key[:4]}...{current_openrouter_key[-4:] if len(current_openrouter_key) > 8 else ''}"
            keep_existing = select_option(f"An existing OpenRouter API Key is configured ({mask_preview}). Keep it?", ["yes", "no"], default_idx=0)
            if keep_existing == "yes":
                openrouter_key = current_openrouter_key
            else:
                openrouter_key = Prompt.ask("Enter new OpenRouter API Key", password=True)
        else:
            openrouter_key = Prompt.ask("Enter your OpenRouter API Key (masking inputs)", password=True)
            while not openrouter_key.strip():
                openrouter_key = Prompt.ask("OpenRouter API Key cannot be empty. Please enter key", password=True)
        api_base_url = "https://openrouter.ai/api/v1"
        
    else: # custom
        openai_key = Prompt.ask("Enter your API Key (e.g. Ollama API key)", default=current_openai_key)
        api_base_url = Prompt.ask("Enter custom API Base URL (e.g. http://localhost:11434/v1)", default=current_api_base or "http://localhost:11434/v1")

    # Fetch available models using the configured API credentials
    fetched = []
    with console.status(f"[bold cyan]Fetching available models for {provider}...[/]"):
        if provider == "gemini":
            fetched = fetch_provider_models("gemini", gemini_key)
        elif provider == "openai":
            fetched = fetch_provider_models("openai", openai_key, api_base_url)
        elif provider == "openrouter":
            fetched = fetch_provider_models("openrouter", openrouter_key)
        elif provider == "custom":
            fetched = fetch_provider_models("custom", openai_key, api_base_url)
            
    if fetched:
        console.print(f"  [bold green]✓[/] Successfully fetched {len(fetched)} models from provider API.\n")
    else:
        console.print("  [bold yellow]⚠[/] Could not fetch models from API (offline or invalid key). Using default list.\n")

    # 4. Model Name Selection
    model_choices = {
        "gemini": [
            "gemini-2.5-flash  (Fast, default model)",
            "gemini-2.5-pro  (Highly capable, reasoning model)",
            "gemini-1.5-flash  (Older generation flash)",
            "gemini-1.5-pro  (Older generation pro)"
        ],
        "openai": [
            "gpt-4o  (High-speed, premium multi-modal)",
            "gpt-4o-mini  (Cost-efficient, fast model)",
            "o1  (Advanced reasoning model)",
            "o1-mini  (Fast reasoning model)"
        ],
        "openrouter": [
            "google/gemini-2.5-flash  (Recommended flash)",
            "google/gemini-2.5-pro  (Recommended pro)",
            "openai/gpt-4o  (GPT-4o on OpenRouter)",
            "anthropic/claude-3.5-sonnet  (Claude 3.5 Sonnet)"
        ],
        "custom": [
            "llama3  (Meta Llama 3)",
            "qwen2.5-coder  (Qwen 2.5 Coder)",
            "mistral  (Mistral 7B)",
            "phi3  (Microsoft Phi 3)"
        ]
    }

    default_choices = model_choices.get(provider, [])
    choices = []
    if fetched:
        desc_map = {}
        for choice in default_choices:
            parts = choice.split("  ")
            clean_id = parts[0].strip()
            if len(parts) > 1:
                desc_map[clean_id] = parts[1].strip()
                
        for m in fetched:
            if "  " in m:
                choices.append(m)
            else:
                desc = desc_map.get(m, "")
                if desc:
                    choices.append(f"{m}  {desc}")
                else:
                    choices.append(m)
    else:
        choices = default_choices.copy()
        
    manual_option = "Enter model name manually..."
    choices.append(manual_option)
    
    default_model_idx = 0
    if current_model:
        found_match = False
        for i, choice in enumerate(choices):
            # Split by double space to extract raw model name
            choice_clean = choice.split("  ")[0].strip()
            if choice_clean == current_model:
                choices[i] = f"{choice_clean}  ← currently active"
                default_model_idx = i
                found_match = True
                break
        if not found_match:
            choices.insert(0, f"{current_model}  ← currently active")
            default_model_idx = 0
            
    selected_model_display = select_option("Select Model", choices, default_idx=default_model_idx)
    
    if selected_model_display == manual_option:
        model_name = Prompt.ask("Enter Model Name").strip()
        while not model_name:
            model_name = Prompt.ask("Model Name cannot be empty. Please enter name").strip()
    else:
        # Parse the raw model identifier
        model_name = selected_model_display.split("  ")[0].strip()

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

    # Construct config dictionary
    config_dict = {
        "MODEL_PROVIDER": provider,
        "MODEL_NAME": model_name,
        "GEMINI_API_KEY": gemini_key,
        "OPENAI_API_KEY": openai_key,
        "OPENROUTER_API_KEY": openrouter_key,
        "API_BASE_URL": api_base_url,
        "TELEGRAM_BOT_TOKEN": telegram_token,
        "TELEGRAM_CHAT_ID": telegram_chat_id,
        "DISCORD_BOT_TOKEN": discord_token,
        "DISCORD_CHANNEL_ID": discord_channel_id,
    }
    
    save_config(config_dict)
        
    # 7. Print tool & configuration availability summary (matching Hermes)
    console.print("\n[bold cyan]◆ Configuration Summary[/]")
    console.print(f"  [bold]LLM Provider:[/]  [green]{provider}[/]")
    console.print(f"  [bold]Model Name:[/]    [green]{model_name}[/]")
    
    key_configured = False
    if provider == "gemini" and gemini_key:
        key_configured = True
    elif provider == "openai" and openai_key:
        key_configured = True
    elif provider == "openrouter" and openrouter_key:
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
    console.print("\n[bold green]🎉 Configuration saved successfully![/]\n")

    # Automatically build web frontend if dist is missing and npm is available
    web_dir = os.path.join(install_dir, "web")
    web_dist_dir = os.path.join(web_dir, "dist")
    if not os.path.exists(web_dist_dir):
        import shutil
        import subprocess
        npm_bin = shutil.which("npm")
        if npm_bin and os.path.exists(web_dir):
            console.print("🌐 [yellow]First-time setup: Building web frontend dashboard...[/]")
            try:
                subprocess.run([npm_bin, "install"], cwd=web_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run([npm_bin, "run", "build"], cwd=web_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                console.print("[bold green]✓ Web frontend compiled successfully.[/]\n")
            except Exception:
                console.print("[bold red]✗ Failed to compile web frontend automatically. Headless API mode will still be available.[/]\n")

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
        
        # Automatically rebuild web frontend if npm is available
        web_dir = os.path.join(install_dir, "web")
        npm_bin = shutil.which("npm")
        if npm_bin and os.path.exists(web_dir):
            console.print("\n🌐 [yellow]Rebuilding web frontend dashboard...[/]")
            try:
                subprocess.run([npm_bin, "install"], cwd=web_dir, check=True)
                subprocess.run([npm_bin, "run", "build"], cwd=web_dir, check=True)
                console.print("[bold green]✓ Web frontend compiled successfully.[/]")
            except Exception as e:
                console.print(f"[bold red]✗ Failed to build web frontend:[/] {str(e)}")

        # Restart systemd service — try system-level first, then user-level
        console.print("\n🔁 [yellow]Restarting RexiO service...[/]")
        try:
            # System-level (VPS, sudo)
            sys_result = subprocess.run(
                ["sudo", "systemctl", "restart", "rexio.service"],
                capture_output=True, text=True, timeout=15
            )
            if sys_result.returncode == 0:
                console.print("[bold green]✓ System service restarted.[/]")
            else:
                # Fall back to user-level
                usr_result = subprocess.run(
                    ["systemctl", "--user", "restart", "rexio.service"],
                    capture_output=True, text=True
                )
                if usr_result.returncode == 0:
                    console.print("[bold green]✓ User service restarted.[/]")
                else:
                    console.print("[yellow]⚠ Could not restart service — run manually.[/]")
        except Exception:
            console.print("[yellow]⚠ systemd not available — skipping restart.[/]")

        console.print("\n[bold green]🎉 RexiO Agent update complete![/]\n")
    except subprocess.CalledProcessError as e:
        console.print("[bold red]✗ Failed to compile and install package dependencies.[/]")
        sys.exit(1)

def run_gateway_install():
    """Installs RexiO as a system-level service (/etc/systemd/system/).
    Runs with sudo so it stays alive after SSH disconnect and auto-starts on VPS reboot.
    """
    import subprocess
    import shutil
    import getpass
    import pwd

    install_dir = os.path.dirname(os.path.abspath(__file__))
    python_path = os.path.join(install_dir, ".venv", "bin", "python")
    username = getpass.getuser()
    home_dir = os.path.expanduser("~")
    env_file = os.path.join(install_dir, ".env")
    log_dir = os.path.join(os.path.dirname(install_dir), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Detect group
    try:
        group_name = pwd.getpwnam(username).pw_name
    except Exception:
        group_name = username

    console.print()
    console.print("[bold cyan]┌─────────────────────────────────────────────────────────┐[/]")
    console.print("[bold cyan]│            ☤ RexiO Gateway Install                     │[/]")
    console.print("[bold cyan]├─────────────────────────────────────────────────────────┤[/]")
    console.print("[bold cyan]│  Installing system-level service (requires sudo)        │[/]")
    console.print("[bold cyan]│  Stays alive after SSH disconnect, auto-starts on boot  │[/]")
    console.print("[bold cyan]└─────────────────────────────────────────────────────────┘[/]")
    console.print()

    service_name = "rexio"
    service_path = f"/etc/systemd/system/{service_name}.service"

    service_content = f"""[Unit]
Description=RexiO Agent Gateway
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
User={username}
Group={group_name}
WorkingDirectory={install_dir}
ExecStart={python_path} run_agent.py
EnvironmentFile={env_file}
Environment="HOME={home_dir}"
Environment="USER={username}"
Environment="LOGNAME={username}"
Environment="REXIO_DEV=0"
Restart=always
RestartSec=5
RestartMaxDelaySec=300
KillMode=mixed
KillSignal=SIGTERM
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

    # Write service file via sudo
    console.print(f"📝 [yellow]Writing service file to {service_path}...[/]")
    try:
        write_cmd = f"echo {repr(service_content)} | sudo tee {service_path} > /dev/null"
        result = subprocess.run(write_cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            # Try alternative approach
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.service', delete=False) as tmp:
                tmp.write(service_content)
                tmp_path = tmp.name
            subprocess.run(["sudo", "cp", tmp_path, service_path], check=True)
            subprocess.run(["sudo", "chmod", "644", service_path], check=True)
            os.unlink(tmp_path)
        console.print(f"[bold green]✓ Service file written.[/]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]✗ Failed to write service file:[/] {e}")
        sys.exit(1)

    # Disable old user-level service if exists
    user_service = os.path.expanduser("~/.config/systemd/user/rexio.service")
    if os.path.exists(user_service):
        console.print("🔄 [yellow]Disabling old user-level service...[/]")
        subprocess.run(["systemctl", "--user", "stop", "rexio.service"], capture_output=True)
        subprocess.run(["systemctl", "--user", "disable", "rexio.service"], capture_output=True)

    # Reload + enable + start
    console.print("⚙️  [yellow]Enabling and starting system service...[/]")
    try:
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "enable", service_name], check=True)
        subprocess.run(["sudo", "systemctl", "restart", service_name], check=True)
        console.print(f"[bold green]✓ RexiO service enabled and started.[/]")
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]✗ systemctl failed:[/] {e}")
        sys.exit(1)

    # Show status
    import time
    time.sleep(2)
    status = subprocess.run(
        ["sudo", "systemctl", "status", service_name, "--no-pager", "-l"],
        capture_output=True, text=True
    )
    active_line = next((l for l in status.stdout.splitlines() if "Active:" in l), "")
    if "active (running)" in active_line:
        console.print(f"\n[bold green]🎉 RexiO gateway is live![/]")
        console.print(f"   Logs:    [cyan]journalctl -u {service_name} -f[/]")
        console.print(f"   Status:  [cyan]sudo systemctl status {service_name}[/]")
        console.print(f"   Restart: [cyan]sudo systemctl restart {service_name}[/]\n")
    else:
        console.print(f"\n[yellow]⚠ Service may not be running. Check:[/]")
        console.print(f"   [cyan]sudo systemctl status {service_name}[/]")
        console.print(f"   [cyan]journalctl -u {service_name} -n 30[/]\n")


def main():
    # gateway install
    if len(sys.argv) > 2 and sys.argv[1] == "gateway" and sys.argv[2] == "install":
        try:
            run_gateway_install()
            sys.exit(0)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Install cancelled.[/]")
            sys.exit(1)

    # 1. Check for update request
    if len(sys.argv) > 1 and sys.argv[1] in ("update", "--update"):
        try:
            run_update_wizard()
            sys.exit(0)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Update cancelled.[/]")
            sys.exit(1)

    # 1b. Check for backend server request
    if len(sys.argv) > 1 and sys.argv[1] in ("server", "web", "start"):
        try:
            import run_agent
            run_agent.start()
            sys.exit(0)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]Failed to start server:[/] {str(e)}")
            sys.exit(1)

    config_path = CONFIG_PATH
    
    # Run setup wizard if configuration does not exist, if explicitly requested via 'setup' / '--setup', or if keys are empty
    should_run_setup = not os.path.exists(config_path) or (len(sys.argv) > 1 and sys.argv[1] in ("setup", "--setup"))
    
    if should_run_setup:
        try:
            run_setup_wizard(config_path)
            # Re-load configuration
            load_environment()
            # If setup was explicitly requested as a CLI argument, exit after completion
            if len(sys.argv) > 1 and sys.argv[1] in ("setup", "--setup"):
                sys.exit(0)
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Setup cancelled.[/]")
            sys.exit(1)

    if not should_run_setup and os.path.exists(config_path):
        load_environment()
        provider = os.getenv("MODEL_PROVIDER", "gemini").lower()
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        
        if (provider == "gemini" and not gemini_key) or (provider == "openai" and not openai_key) or (provider == "openrouter" and not openrouter_key):
            console.print("[yellow]Warning:[/] Configuration credentials appear to be missing.")
            if select_option("Would you like to run the setup wizard now?", ["yes", "no"], default_idx=0) == "yes":
                try:
                    run_setup_wizard(config_path)
                    load_environment()
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
        console.print("Make sure your API keys are correctly set in the setup configuration.")
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
