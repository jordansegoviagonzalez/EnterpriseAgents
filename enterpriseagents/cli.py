from __future__ import annotations

import uuid
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from enterpriseagents.agents.builder import BuilderAgent
from enterpriseagents.agents.director import DirectorAgent
from enterpriseagents.agents.docs import DocsAgent
from enterpriseagents.agents.reviewer import ReviewerAgent
from enterpriseagents.audit.logger import AuditLogger
from enterpriseagents.config.settings import Settings
from enterpriseagents.core.router import DynamicRouter
from enterpriseagents.core.run import RunCoordinator, RunRequest
from enterpriseagents.llm.openai import OpenAIProvider
from enterpriseagents.memory.store import MemoryStore
from enterpriseagents.policy.policy import PolicyEngine
from enterpriseagents.tools.registry import ToolRegistry

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.command()
def run(
    instruction: str = typer.Argument(..., help="One instruction for the agent crew."),
    workspace: str = typer.Option("./workspace", help="Workspace folder for generated artifacts."),
    dry_run: bool = typer.Option(False, help="Print proposed actions; do not execute tools."),
    local: bool = typer.Option(False, help="Use deterministic local scaffold (no API key required)."),
) -> None:
    """Run an end-to-end workflow."""

    # WHAT: Create workspace and run infrastructure
    # WHY it matters: Tool execution must be scoped to a known directory (safety + reproducibility)
    Path(workspace).mkdir(parents=True, exist_ok=True)

    settings = Settings()
    run_id = str(uuid.uuid4())

    # Initialize the "Brain"
    if local:
        from enterpriseagents.llm.local import LocalScaffoldProvider
        llm = LocalScaffoldProvider()
    else:
        llm = OpenAIProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

    # Initialize Memory
    memory_path = Path(".enterpriseagents/memory.db")
    memory_path.parent.mkdir(exist_ok=True)
    memory = MemoryStore(db_path=memory_path)
    
    # Initialize Router
    router = DynamicRouter(llm=llm)

    audit = AuditLogger(runs_dir=Path(settings.runs_dir), run_id=run_id)
    policy = PolicyEngine()
    tools = ToolRegistry.default()

    # Injecting the brain into the agents
    director = DirectorAgent(llm=llm)
    builder = BuilderAgent(llm=llm)
    reviewer = ReviewerAgent(tools=tools)
    docs_agent = DocsAgent(llm=llm)

    coordinator = RunCoordinator(
        run_id=run_id,
        audit=audit,
        policy=policy,
        tools=tools,
        director=director,
        builder=builder,
        reviewer=reviewer,
        docs=docs_agent,
        router=router,
        memory=memory,
    )

    console.print(Panel.fit(f"[bold]EnterpriseAgents[/bold]\nRun: {run_id}\nWorkspace: {workspace}"))
    if dry_run:
        console.print("[yellow]DRY RUN enabled — no tools will be executed.[/yellow]")

    try:
        coordinator.execute(RunRequest(instruction=instruction, workspace=workspace, dry_run=dry_run))
        console.print(Panel.fit(f"[green]Done.[/green]\nEvidence: runs/{run_id}/"))
    except Exception as e:
        console.print(f"[red]Run failed:[/red] {e}")
        # In enterprise, we log the trace to audit, but for CLI we just show error
        raise


@app.command()
def explain() -> None:
    """Print the high-level system mental model."""
    console.print(
        Panel(
            "[bold]WHAT[/bold]\n"
            "EnterpriseAgents orchestrates agents + tools to deliver verified artifacts.\n\n"
            "[bold]WHY[/bold]\n"
            "LLMs alone do not provide durable workflow state, safe tool execution, or audit evidence.\n\n"
            "[bold]HOW[/bold]\n"
            "1) Director -> tasks\n"
            "2) Builder -> tool calls\n"
            "3) Policy -> gate execution\n"
            "4) Reviewer -> deterministic checks\n"
            "5) Audit -> run packet (proof)\n"
        )
    )
