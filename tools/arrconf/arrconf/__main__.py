"""arrconf CLI entrypoint — 4 subcommands per D-06 + REQ-cli-subcommands."""

from __future__ import annotations

from pathlib import Path

import structlog
import typer

from arrconf.logging import configure_logging

app = typer.Typer(
    name="arrconf",
    help="Reconcile *arr app configurations from YAML to REST APIs.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,  # T-01-01: avoid leaking secrets in tracebacks
)


@app.callback()
def main(
    ctx: typer.Context,
    config: Path = typer.Option(
        Path("/etc/arrconf/arrconf.yml"),
        "--config",
        "-c",
        help="Path to arrconf YAML config",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        "-l",
        envvar="ARRCONF_LOG_LEVEL",
    ),
) -> None:
    """Configure logging and stash common options for subcommands."""
    configure_logging(log_level)
    ctx.obj = {"config_path": config}


@app.command()
def apply(
    ctx: typer.Context,
    apps: str | None = typer.Option(None, help="Comma-separated apps"),
    dry_run: bool = typer.Option(False, "--dry-run", envvar="ARRCONF_DRY_RUN"),
) -> None:
    """Reconcile YAML → cluster APIs."""
    log = structlog.get_logger()
    log.info("apply_invoked", config=str(ctx.obj["config_path"]), apps=apps, dry_run=dry_run)
    raise typer.Exit(code=0)  # W3: replace with actual reconcile dispatch


@app.command()
def dump(
    ctx: typer.Context,
    apps: str | None = typer.Option(None, help="Comma-separated apps"),
    output: Path = typer.Option(Path("examples/dump.yml"), "--output", "-o"),
) -> None:
    """Read-only export of cluster state to YAML."""
    log = structlog.get_logger()
    log.info("dump_invoked", apps=apps, output=str(output))
    raise typer.Exit(code=0)  # W3: replace


@app.command()
def diff(
    ctx: typer.Context,
    apps: str | None = typer.Option(None, help="Comma-separated apps"),
) -> None:
    """Compare YAML config vs cluster state. Exit 3 if drift."""
    log = structlog.get_logger()
    log.info("diff_invoked", config=str(ctx.obj["config_path"]), apps=apps)
    raise typer.Exit(code=0)  # W3: replace


@app.command(name="schema-gen")
def schema_gen_cmd(
    output: Path = typer.Option(Path("schemas/arrconf-schema.json"), "--output", "-o"),
) -> None:
    """Export JSON Schema (Draft 2020-12) from RootConfig (D-15)."""
    log = structlog.get_logger()
    log.info("schema_gen_invoked", output=str(output))
    raise typer.Exit(code=0)  # W3: replace with schema_gen.write_schema(output)


if __name__ == "__main__":
    app()
