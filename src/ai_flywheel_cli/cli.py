from __future__ import annotations

import json
from pathlib import Path

import typer

from ai_flywheel_cli import __version__
from ai_flywheel_cli.completion import complete_execution
from ai_flywheel_cli.deterministic_operations import (
    UnsupportedDeterministicOperationError,
    advance_lifecycle,
    start_execution,
)
from ai_flywheel_cli.mutation import MutationRejectedError
from ai_flywheel_cli.operations import (
    LockContentionError,
    OperationError,
    RepositoryConflictError,
    install_from_archive,
    plan_install,
)
from ai_flywheel_cli.upgrade import upgrade_from_archive
from ai_flywheel_cli.validation import validate_repository

app = typer.Typer(
    name="flywheel",
    help="Install, inspect, validate, upgrade, and safely operate AI Flywheel artifacts.",
    no_args_is_help=True,
    invoke_without_command=True,
)


def _emit(payload: dict[str, object], *, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(payload, sort_keys=True))
        return
    for key, value in payload.items():
        typer.echo(f"{key}: {value}")


def _operation_exit(error: OperationError, *, command: str, as_json: bool) -> None:
    if isinstance(error, LockContentionError):
        code = 5
        category = "lock-contention"
    elif isinstance(error, UnsupportedDeterministicOperationError):
        code = 6
        category = "ai-fallback-required"
    elif isinstance(error, RepositoryConflictError):
        code = 4
        category = "repository-conflict"
    else:
        code = 8
        category = "operation-failed"
    payload: dict[str, object] = {
        "command": command,
        "status": category,
        "error": str(error),
    }
    if isinstance(error, MutationRejectedError):
        payload["failures"] = [failure.as_dict() for failure in error.failures]
    _emit(payload, as_json=as_json)
    raise typer.Exit(code=code)


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", help="Show the CLI version and exit.", is_eager=True
    ),
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command()
def doctor(
    repository: Path = typer.Argument(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Emit deterministic JSON output."),
) -> None:
    """Inspect local prerequisites without modifying the repository."""
    flywheel_path = repository / ".flywheel"
    _emit(
        {
            "command": "doctor",
            "repository": str(repository.resolve()),
            "flywheel_exists": flywheel_path.is_dir(),
            "repository_writable": repository.exists() and repository.is_dir(),
            "status": "ok",
        },
        as_json=json_output,
    )


@app.command()
def status(
    repository: Path = typer.Argument(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Emit deterministic JSON output."),
) -> None:
    """Report the current repository Flywheel status."""
    state_path = repository / ".flywheel" / "state.yaml"
    if not state_path.is_file():
        _emit(
            {
                "command": "status",
                "repository": str(repository.resolve()),
                "status": "not-installed",
            },
            as_json=json_output,
        )
        return
    result = validate_repository(repository)
    _emit(
        {
            "command": "status",
            "repository": str(repository.resolve()),
            "status": "valid" if result.passed else "invalid",
            "issue_count": len(result.issues),
        },
        as_json=json_output,
    )


@app.command()
def validate(
    repository: Path = typer.Argument(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Emit deterministic JSON output."),
) -> None:
    """Validate repository Flywheel artifacts and active references."""
    result = validate_repository(repository)
    payload: dict[str, object] = {
        "command": "validate",
        "repository": str(repository.resolve()),
        "status": "passed" if result.passed else "validation-failed",
        "error_count": len(result.issues),
        "errors": [issue.as_dict() for issue in result.issues],
    }
    _emit(payload, as_json=json_output)
    if not result.passed:
        raise typer.Exit(code=2)


@app.command("start-execution")
def start_execution_command(
    mission_id: str = typer.Argument(...),
    goal_id: str = typer.Argument(...),
    execution_id: str = typer.Argument(...),
    intended_outcome: str = typer.Option(..., "--intended-outcome"),
    repository: Path = typer.Option(Path.cwd(), "--repository", exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Emit deterministic JSON output."),
) -> None:
    """Create and activate an execution with synchronized goal and state artifacts."""
    try:
        result = start_execution(
            repository,
            mission_id,
            goal_id,
            execution_id,
            intended_outcome,
        )
    except OperationError as error:
        _operation_exit(error, command="start-execution", as_json=json_output)
        return
    _emit(result.as_dict(), as_json=json_output)


@app.command("advance-lifecycle")
def advance_lifecycle_command(
    summary: str = typer.Option(..., "--summary"),
    ref: list[str] | None = typer.Option(None, "--ref"),
    expected_stage: str | None = typer.Option(
        None,
        "--expected-stage",
        help="Reject a retry when the active lifecycle stage has already changed.",
    ),
    repository: Path = typer.Option(Path.cwd(), "--repository", exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Emit deterministic JSON output."),
) -> None:
    """Complete the active lifecycle stage and start the next stage atomically."""
    try:
        result = advance_lifecycle(
            repository,
            summary,
            tuple(ref or ()),
            expected_stage=expected_stage,
        )
    except OperationError as error:
        _operation_exit(error, command="advance-lifecycle", as_json=json_output)
        return
    _emit(result.as_dict(), as_json=json_output)


@app.command("complete-execution")
def complete_execution_command(
    summary: str = typer.Option(..., "--summary"),
    ref: list[str] | None = typer.Option(None, "--ref"),
    repository: Path = typer.Option(Path.cwd(), "--repository", exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Emit deterministic JSON output."),
) -> None:
    """Complete reuse, close the active execution, and ready the next dependent goal."""
    try:
        result = complete_execution(repository, summary, tuple(ref or ()))
    except OperationError as error:
        _operation_exit(error, command="complete-execution", as_json=json_output)
        return
    _emit(result.as_dict(), as_json=json_output)


@app.command()
def install(
    repository: Path = typer.Argument(Path.cwd(), exists=True, file_okay=False),
    archive: Path = typer.Option(..., "--archive", exists=True, dir_okay=False),
    checksum: str = typer.Option(..., "--checksum", help="Expected SHA-256 checksum."),
    framework_version: str = typer.Option(..., "--framework-version"),
    source_identity: str = typer.Option("local-archive", "--source-identity"),
    apply: bool = typer.Option(False, "--apply", "--yes", help="Apply the displayed plan."),
    json_output: bool = typer.Option(False, "--json", help="Emit deterministic JSON output."),
) -> None:
    """Install verified Flywheel artifacts transactionally from an immutable archive."""
    try:
        plan = plan_install(archive, framework_version)
        if not apply:
            _emit(
                {**plan.as_dict(), "status": "planned", "apply_required": True},
                as_json=json_output,
            )
            return
        result = install_from_archive(
            repository,
            archive,
            checksum,
            framework_version,
            source_identity,
        )
    except OperationError as error:
        _operation_exit(error, command="install", as_json=json_output)
        return
    _emit(result.as_dict(), as_json=json_output)


@app.command()
def upgrade(
    repository: Path = typer.Argument(Path.cwd(), exists=True, file_okay=False),
    archive: Path = typer.Option(..., "--archive", exists=True, dir_okay=False),
    checksum: str = typer.Option(..., "--checksum", help="Expected SHA-256 checksum."),
    framework_version: str = typer.Option(..., "--framework-version"),
    source_identity: str = typer.Option("local-archive", "--source-identity"),
    apply: bool = typer.Option(False, "--apply", "--yes", help="Apply the displayed upgrade."),
    json_output: bool = typer.Option(False, "--json", help="Emit deterministic JSON output."),
) -> None:
    """Upgrade verified Flywheel artifacts with conflict detection and rollback."""
    if not apply:
        _emit(
            {
                "command": "upgrade",
                "status": "planned",
                "framework_version": framework_version,
                "apply_required": True,
            },
            as_json=json_output,
        )
        return
    try:
        result = upgrade_from_archive(
            repository,
            archive,
            checksum,
            framework_version,
            source_identity,
        )
    except OperationError as error:
        _operation_exit(error, command="upgrade", as_json=json_output)
        return
    _emit(result.as_dict(), as_json=json_output)
