from __future__ import annotations

from pathlib import Path

import typer

from ai_flywheel_cli.cli import _emit, _operation_exit, app
from ai_flywheel_cli.operations import OperationError
from ai_flywheel_cli.persistence import persist_execution


@app.command("persist-execution")
def persist_execution_command(
    summary: str = typer.Option(..., "--summary"),
    reuse_id: str = typer.Option(..., "--reuse-id"),
    operator: str = typer.Option("ai-flywheel-cli", "--operator"),
    repository: Path = typer.Option(Path.cwd(), "--repository", exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Emit deterministic JSON output."),
) -> None:
    """Persist validated execution records and atomically activate Reuse."""
    try:
        result = persist_execution(
            repository,
            summary,
            reuse_id,
            operator=operator,
        )
    except OperationError as error:
        _operation_exit(error, command="persist-execution", as_json=json_output)
        return
    _emit(result.as_dict(), as_json=json_output)
