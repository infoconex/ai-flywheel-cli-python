from __future__ import annotations

import json
from pathlib import Path

import typer

from ai_flywheel_cli import __version__

app = typer.Typer(
    name="flywheel",
    help="Install, inspect, validate, and upgrade AI Flywheel repository artifacts.",
    no_args_is_help=True,
)


def _emit(payload: dict[str, object], *, as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(payload, sort_keys=True))
        return

    for key, value in payload.items():
        typer.echo(f"{key}: {value}")


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the CLI version and exit.",
        is_eager=True,
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
    _emit(
        {
            "command": "status",
            "repository": str(repository.resolve()),
            "state_exists": state_path.is_file(),
            "status": "ok" if state_path.is_file() else "not-installed",
        },
        as_json=json_output,
    )


@app.command()
def validate(
    repository: Path = typer.Argument(Path.cwd(), exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json", help="Emit deterministic JSON output."),
) -> None:
    """Validate repository Flywheel artifacts."""
    state_path = repository / ".flywheel" / "state.yaml"
    if not state_path.is_file():
        _emit(
            {
                "command": "validate",
                "repository": str(repository.resolve()),
                "status": "validation-failed",
                "errors": ["Missing required .flywheel/state.yaml"],
            },
            as_json=json_output,
        )
        raise typer.Exit(code=2)

    _emit(
        {
            "command": "validate",
            "repository": str(repository.resolve()),
            "status": "passed",
            "errors": [],
        },
        as_json=json_output,
    )


@app.command()
def install() -> None:
    """Install Flywheel artifacts into a repository."""
    typer.echo("Install implementation is pending within Goal 004.")
    raise typer.Exit(code=3)


@app.command()
def upgrade() -> None:
    """Upgrade an existing Flywheel installation."""
    typer.echo("Upgrade implementation is pending within Goal 004.")
    raise typer.Exit(code=3)
