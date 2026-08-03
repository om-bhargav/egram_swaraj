import yaml
from rich.console import Console


def load_config():
    console = Console()
    console.print("[cyan]Loading configuration...[/cyan]")
    console.print("[green]✓ Configuration loaded[/green]")

    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)