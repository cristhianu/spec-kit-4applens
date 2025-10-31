"""
Bicep template validation command.

CLI command for automated validation of Bicep templates through
project discovery, resource deployment, and endpoint testing.
"""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from specify_cli.validation import ProjectInfo
from specify_cli.validation.project_discovery import ProjectDiscovery
from specify_cli.validation.config_analyzer import ConfigAnalyzer

console = Console()
app = typer.Typer(name="validate", help="Validate Bicep templates end-to-end")


@app.command()
def validate(
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="Specific project name to validate (skips selection)"
    ),
    environment: str = typer.Option(
        "test-corp",
        "--environment",
        "-e",
        help="Target environment for deployment"
    ),
    max_retries: int = typer.Option(
        3,
        "--max-retries",
        "-r",
        help="Maximum fix-and-retry attempts"
    ),
    skip_cleanup: bool = typer.Option(
        False,
        "--skip-cleanup",
        help="Skip resource cleanup after validation"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output"
    )
):
    """
    Validate Bicep templates end-to-end.
    
    Discovers projects with Bicep templates, analyzes configuration,
    deploys resources, tests endpoints, and fixes issues automatically.
    """
    try:
        # Step 1: Project Discovery
        console.print("\n[bold cyan]🔍 Step 1: Discovering projects...[/bold cyan]")
        
        discovery = ProjectDiscovery(Path.cwd(), use_cache=True)
        projects = discovery.discover_projects()
        
        if not projects:
            console.print(
                "[bold red]❌ No projects found with Bicep templates[/bold red]\n"
                "Run '/speckit.bicep' to generate Bicep templates first."
            )
            raise typer.Exit(1)
        
        console.print(f"[green]Found {len(projects)} project(s) with Bicep templates[/green]")
        
        # Step 2: Project Selection
        selected_project = None
        
        if project:
            # Direct selection via argument
            selected_project = discovery.get_project_by_name(project)
            if not selected_project:
                console.print(f"[bold red]❌ Project not found: {project}[/bold red]")
                console.print("\nAvailable projects:")
                _display_projects(projects)
                raise typer.Exit(1)
        else:
            # Interactive selection
            console.print("\n[bold cyan]📋 Available projects:[/bold cyan]")
            selected_project = _select_project_interactive(projects)
        
        console.print(f"\n[green]✓ Selected: {selected_project.name}[/green]")
        
        # Step 3: Configuration Analysis
        console.print("\n[bold cyan]🔍 Step 2: Analyzing configuration...[/bold cyan]")
        
        analyzer = ConfigAnalyzer()
        analysis = analyzer.analyze_project(selected_project)
        
        console.print(
            f"[green]✓ Analysis complete: {len(analysis.app_settings)} settings, "
            f"{len(analysis.resource_dependencies)} dependencies[/green]"
        )
        
        # Display analysis results
        _display_analysis_results(analysis, verbose)
        
        # Step 4: Validation workflow (placeholder for now)
        console.print(
            "\n[bold yellow]⚠️  Full validation workflow not yet implemented[/bold yellow]"
        )
        console.print(
            "[dim]Next steps: Resource deployment, endpoint testing, fix-and-retry[/dim]"
        )
        
        console.print("\n[bold green]✅ Phase 1 validation complete[/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Validation cancelled by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        console.print(f"\n[bold red]❌ Validation failed: {e}[/bold red]")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


def _display_projects(projects: list[ProjectInfo]) -> None:
    """Display projects in a formatted table"""
    table = Table(title="Projects with Bicep Templates")
    
    table.add_column("#", style="cyan", width=4)
    table.add_column("Name", style="bold")
    table.add_column("Framework", style="magenta")
    table.add_column("Path", style="dim")
    
    for idx, project in enumerate(projects, 1):
        table.add_row(
            str(idx),
            project.name,
            project.framework,
            str(project.path.relative_to(Path.cwd()))
        )
    
    console.print(table)


def _select_project_interactive(projects: list[ProjectInfo]) -> ProjectInfo:
    """
    Prompt user to select a project interactively.
    
    Args:
        projects: List of available projects
        
    Returns:
        Selected project
    """
    _display_projects(projects)
    
    while True:
        choice = Prompt.ask(
            "\n[bold]Select project number[/bold]",
            default="1"
        )
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(projects):
                return projects[idx]
            else:
                console.print(
                    f"[red]Invalid selection. Please enter 1-{len(projects)}[/red]"
                )
        except ValueError:
            console.print("[red]Invalid input. Please enter a number[/red]")


def _display_analysis_results(analysis, verbose: bool) -> None:
    """Display configuration analysis results"""
    
    # App Settings Summary
    console.print("\n[bold]Application Settings:[/bold]")
    
    secure_count = sum(1 for s in analysis.app_settings if s.is_secure)
    console.print(f"  Total: {len(analysis.app_settings)}")
    console.print(f"  Secure values: {secure_count}")
    console.print(f"  Standard values: {len(analysis.app_settings) - secure_count}")
    
    if verbose and analysis.app_settings:
        table = Table(title="App Settings Details")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Secure", style="yellow")
        
        for setting in analysis.app_settings[:10]:  # Limit to first 10
            table.add_row(
                setting.name,
                setting.source_type.value,
                "🔒" if setting.is_secure else "✓"
            )
        
        if len(analysis.app_settings) > 10:
            table.caption = f"Showing 10 of {len(analysis.app_settings)} settings"
        
        console.print(table)
    
    # Resource Dependencies
    if analysis.resource_dependencies:
        console.print("\n[bold]Resource Dependencies:[/bold]")
        for resource in analysis.resource_dependencies:
            console.print(f"  • {resource}")
    
    # Dependency Graph
    if verbose and analysis.dependency_graph:
        console.print("\n[bold]Deployment Order:[/bold]")
        for resource, deps in analysis.dependency_graph.items():
            if deps:
                console.print(f"  {resource} depends on:")
                for dep in deps:
                    console.print(f"    → {dep}")
            else:
                console.print(f"  {resource} (no dependencies)")


if __name__ == "__main__":
    app()
