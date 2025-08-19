# src/cli/commands/models.py
# Models listing & availability command for Loom CLI (OpenAI, Claude & Ollama)

from __future__ import annotations

import typer
from ...ai.models import get_models_by_provider
from ...ai.clients.ollama_client import check_ollama_with_error, get_available_models_with_error
from ...loom_io.console import console
from ...ui.theming.colors import styled_checkmark, accent_gradient, styled_bullet
from ..app import app
from ...ui.help.help_data import command_help
from .help import show_command_help
from ...core.debug import enable_debug

# * Sub-app for models commands; registered on root app
models_app = typer.Typer(
    rich_markup_mode="rich", 
    help="[loom.accent2]List available AI models by provider[/]"
)
app.add_typer(models_app, name="models")

# * default callback: show all available models by provider when no subcommand provided
@command_help(
    name="models",
    description="List available AI models by provider",
    long_description=(
        "Show available AI models from OpenAI, Claude, and Ollama with their availability status. "
        "Models requiring API keys will show setup instructions. Local Ollama models are "
        "discovered dynamically from your running Ollama instance."
    ),
    examples=[
        "loom models  # Show all models by provider",
        "loom models list  # Same as above",
        "loom models test deepseek-r1:14b  # Test specific Ollama model",
    ],
    see_also=["config", "tailor"],
)
@models_app.callback(invoke_without_command=True)
def models_callback(
    ctx: typer.Context,
    help: bool = typer.Option(False, "--help", "-h", help="Show help message and exit."),
) -> None:
    # detect help flag & show custom help
    if help:
        show_command_help("models")
        ctx.exit()
    
    if ctx.invoked_subcommand is None:
        _show_models_list()

# * explicit list command (same as default callback)
@models_app.command()
def list() -> None:
    _show_models_list()

# * helper function to display models by provider
def _show_models_list() -> None:
    providers = get_models_by_provider()
    
    console.print()
    console.print(accent_gradient("Available AI Models"))
    console.print()
    
    for provider_name, info in providers.items():
        provider_display = provider_name.upper()
        models = info["models"]
        available = info["available"]
        requirement = info["requirement"]
        
        # show provider header w/ availability status
        if available and models:
            status_icon = styled_checkmark()
            status_text = "[green]Available[/]"
        elif models:
            status_icon = "[red]✗[/]"
            status_text = f"[dim]Requires {requirement}[/]"
        else:
            status_icon = "[red]✗[/]"
            status_text = "[dim]No models available[/]"
        
        console.print(f"[bold white]{provider_display}[/] {status_icon} {status_text}")
        
        # show models list
        if models:
            for model in models:
                model_text = f"[loom.accent2]{model}[/]" if available else f"[dim]{model}[/]"
                console.print(f"  {styled_bullet()} {model_text}")
        else:
            if provider_name == "ollama":
                console.print(f"  [dim]Start Ollama server & install models to see available options[/]")
            else:
                console.print(f"  [dim]Set {requirement} to use {provider_display} models[/]")
        
        console.print()
    
    # add usage note
    console.print("[dim]Use any available model with:[/] [loom.accent2]loom tailor --model MODEL_NAME[/]")
    console.print("[dim]Set default model with:[/] [loom.accent2]loom config set model MODEL_NAME[/]")

# * test command to check Ollama connectivity & model availability
@models_app.command()
def test(
    model: str = typer.Argument(help="Model name to test (e.g., deepseek-r1:14b)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug output"),
) -> None:
    
    if verbose:
        enable_debug()
    
    console.print(f"\nTesting Ollama model: [loom.accent2]{model}[/]")
    console.print()
    
    # check Ollama server connectivity
    console.print("1. Checking Ollama server connectivity...")
    available, error_msg = check_ollama_with_error()
    
    if not available:
        console.print(f"   {styled_bullet()} [red]Failed[/]: {error_msg}")
        return
    else:
        console.print(f"   {styled_checkmark()} [green]Ollama server is running[/]")
    
    # check available models
    console.print("2. Retrieving available models...")
    models, models_error = get_available_models_with_error()
    
    if models_error:
        console.print(f"   {styled_bullet()} [red]Failed[/]: {models_error}")
        return
    else:
        console.print(f"   {styled_checkmark()} [green]Found {len(models)} models[/]")
    
    # check if specific model is available
    console.print(f"3. Checking if model '{model}' is available...")
    
    if model in models:
        console.print(f"   {styled_checkmark()} [green]Model '{model}' is available[/]")
    else:
        console.print(f"   {styled_bullet()} [red]Model '{model}' not found[/]")
        console.print(f"   Available models: {', '.join(models) if models else 'None'}")
        console.print(f"   Install with: [loom.accent2]ollama pull {model}[/]")
        return
    
    # test basic API call
    console.print("4. Testing basic API call...")
    from ...ai.clients.ollama_client import run_generate
    
    test_prompt = "Please respond with valid JSON containing a single field 'test' with value 'success': "
    result = run_generate(test_prompt, model)
    
    if result.success:
        console.print(f"   {styled_checkmark()} [green]API call successful[/]")
        if verbose:
            console.print(f"   Response: {result.json_text[:100]}{'...' if len(result.json_text) > 100 else ''}")
    else:
        console.print(f"   {styled_bullet()} [red]API call failed[/]: {result.error}")
        return
    
    console.print()
    console.print(f"[green]✓ Model '{model}' is fully functional![/]")
    console.print(f"You can use it with: [loom.accent2]loom tailor --model {model}[/]")
