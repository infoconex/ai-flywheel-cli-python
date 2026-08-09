from __future__ import annotations

import json
from pathlib import Path

import typer

from ai_flywheel_cli import __version__
from ai_flywheel_cli.completion import CompletionRejectedError, complete_execution
from ai_flywheel_cli.deterministic_operations import (
    UnsupportedDeterministicOperationError,
    advance_lifecycle,
    start_execution,
)
from ai_flywheel_cli.framework_compatibility import (
    SUPPORTED_FRAMEWORK_VERSION,
    classify_framework,
)
from ai_flywheel_cli.mutation import MutationRejectedError, load_yaml_mapping
from ai_flywheel_cli.operations import (
    LockContentionError,
    OperationError,
    RepositoryConflictError,
)
from ai_flywheel_cli.persistence import persist_execution
from ai_flywheel_cli.validation import validate_repository

app = typer.Typer(
    name="flywheel",
    help="Inspect, validate, and safely operate AI Flywheel artifacts.",
    no_args_is_help=True,
    invoke_without_command=True,
)

EXIT_SUCCESS = 0
EXIT_RUNTIME_ABORT = 1
EXIT_USAGE_ERROR = 2
EXIT_VALIDATION_FAILED = 3
EXIT_REPOSITORY_CONFLICT = 4
EXIT_LOCK_CONTENTION = 5
EXIT_AI_FALLBACK_REQUIRED = 6
EXIT_OPERATION_FAILED = 7
EXIT_FRAMEWORK_INCOMPATIBLE = 8


def _emit(payload: dict[str, object], *, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(payload, sort_keys=True))
        return
    for key, value in payload.items():
        typer.echo(f"{key}: {value}")


def _operation_exit(error: OperationError, *, command: str, as_json: bool) -> None:
    if isinstance(error, LockContentionError):
        code = EXIT_LOCK_CONTENTION
        category = "lock-contention"
        reason = "repository-lock-active"
    elif isinstance(error, UnsupportedDeterministicOperationError):
        code = EXIT_AI_FALLBACK_REQUIRED
        category = "ai-fallback-required"
        reason = "governed-ai-step-required"
    elif isinstance(error, RepositoryConflictError):
        code = EXIT_REPOSITORY_CONFLICT
        category = "repository-conflict"
        reason = "repository-content-conflict"
    else:
        code = EXIT_OPERATION_FAILED
        category = "operation-failed"
        if isinstance(error, MutationRejectedError):
            reason = "mutation-rejected"
        else:
            reason = "operation-error"
    payload: dict[str, object] = {
        "command": command,
        "status": category,
        "category": category,
        "reason": reason,
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
    """Report CLI, framework-compatibility, and repository health without mutation."""
    compatibility = classify_framework(repository)
    validation_status = "not-run"
    validation_issues: list[dict[str, str]] = []
    status_value = "framework-incompatible"
    exit_code = EXIT_FRAMEWORK_INCOMPATIBLE
    if compatibility.compatible:
        validation = validate_repository(repository)
        validation_issues = [issue.as_dict() for issue in validation.issues]
        validation_status = "passed" if validation.passed else "failed"
        status_value = "ok" if validation.passed else "validation-failed"
        exit_code = EXIT_SUCCESS if validation.passed else EXIT_VALIDATION_FAILED

    _emit(
        {
            "command": "doctor",
            "repository": str(repository.resolve()),
            "cli_version": __version__,
            "supported_framework_version": SUPPORTED_FRAMEWORK_VERSION,
            "installed_framework_version": compatibility.installed_version,
            "framework_status": compatibility.status,
            "framework_reason": compatibility.reason,
            "repository_validation_status": validation_status,
            "repository_issue_count": len(validation_issues),
            "repository_issues": validation_issues,
            "status": status_value,
        },
        as_json=json_output,
    )
    if exit_code != EXIT_SUCCESS:
        raise typer.Exit(code=exit_code)


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
        "category": "success" if result.passed else "validation-failure",
        "reason": None if result.passed else "repository-validation-errors",
        "error_count": len(result.issues),
        "errors": [issue.as_dict() for issue in result.issues],
    }
    _emit(payload, as_json=json_output)
    if not result.passed:
        raise typer.Exit(code=EXIT_VALIDATION_FAILED)


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
        result = persist_execution(repository, summary, reuse_id, operator=operator)
    except OperationError as error:
        _operation_exit(error, command="persist-execution", as_json=json_output)
        return
    _emit(result.as_dict(), as_json=json_output)


@app.command("complete-execution")
def complete_execution_command(
    summary: str = typer.Option(..., "--summary"),
    ref: list[str] | None = typer.Option(None, "--ref"),
    mission_completion_file: Path | None = typer.Option(
        None,
        "--mission-completion-file",
        exists=True,
        dir_okay=False,
        help="Explicit mission completion evaluation for a final-goal completion.",
    ),
    repository: Path = typer.Option(Path.cwd(), "--repository", exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Emit deterministic JSON output."),
) -> None:
    """Complete Reuse, close the active execution, and evaluate terminal mission state."""
    try:
        mission_completion = (
            load_yaml_mapping(mission_completion_file, CompletionRejectedError)
            if mission_completion_file is not None
            else None
        )
        result = complete_execution(
            repository,
            summary,
            tuple(ref or ()),
            mission_completion=mission_completion,
        )
    except OperationError as error:
        _operation_exit(error, command="complete-execution", as_json=json_output)
        return
    _emit(result.as_dict(), as_json=json_output)
