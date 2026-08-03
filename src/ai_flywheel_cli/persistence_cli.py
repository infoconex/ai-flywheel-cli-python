from __future__ import annotations

from datetime import datetime
from pathlib import Path

import typer

from ai_flywheel_cli import cli as base_cli
from ai_flywheel_cli.deterministic_operations import DeterministicOperationResult
from ai_flywheel_cli.mutation import load_yaml_mapping
from ai_flywheel_cli.operations import OperationError
from ai_flywheel_cli.persistence import PersistenceRejectedError, persist_execution

app = base_cli.app
_original_advance_lifecycle = base_cli.advance_lifecycle


def _guarded_advance_lifecycle(
    repository: Path,
    summary: str,
    refs: tuple[str, ...],
    *,
    completed_at: datetime | None = None,
    expected_stage: str | None = None,
) -> DeterministicOperationResult:
    state = load_yaml_mapping(repository.resolve() / ".flywheel/state.yaml", PersistenceRejectedError)
    if state.get("lifecycle_stage") == "persist":
        raise PersistenceRejectedError(
            "Persist requires flywheel persist-execution because completion must use "
            "an applied persistence plan and a planned reuse assessment."
        )
    return _original_advance_lifecycle(
        repository,
        summary,
        refs,
        completed_at=completed_at,
        expected_stage=expected_stage,
    )


base_cli.advance_lifecycle = _guarded_advance_lifecycle


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
        base_cli._operation_exit(error, command="persist-execution", as_json=json_output)
        return
    base_cli._emit(result.as_dict(), as_json=json_output)
