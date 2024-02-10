import typer
from typing import Optional
from pathlib import Path

from flowctl import __version__
from flowctl.base import AsyncTyper
from flowctl.render import pprint
from flowctl.utils import (
    exit_with_code,
    get_app_dir,
    set_dev_mode,
    is_url,
)
from flowctl.config import Configuration, Server

cli = AsyncTyper(name="flowctl")


def _show_version(show: bool):
    if show:
        pprint("flowctl version:", __version__)
        exit_with_code(0)


@cli.callback()
async def entrypoint(
    typer_context: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show the flowctl version and exit.",
        callback=_show_version,
        is_eager=True,
    ),
    app_dir: Optional[Path] = typer.Option(
        None,
        "--app-dir",
        envvar="FLOWCTL__APP_DIR",
        help="The application directory to use."
             "Defaults to the Flowdapt app directory.",
    ),
    config_file: str = typer.Option(
        "flowctl.yaml",
        "--config",
        "-c",
        envvar="FLOWCTL__CONFIG_FILE",
        help="The path to the configuration file relative to the application configs directory.",
    ),
    dotenv: list[str] = typer.Option(
        [],
        "--env",
        help="Load a .env file in the configuration."
    ),
    dev_mode: bool = typer.Option(
        False,
        "--dev",
        help="Run flowctl in development mode.",
        envvar="FLOWCTL__DEV_MODE",
    ),
    server: str = typer.Option(
        "",
        "--server",
        "-s",
        envvar="FLOWCTL__SERVER",
        help="The Flowdapt server to connect to. Can be the server name or URL.",
    ),
):
    """
    The CLI tool for managing Flowdapt.
    """
    set_dev_mode(dev_mode)

    app_dir = app_dir or get_app_dir()
    app_dir = app_dir.resolve()

    if not app_dir.exists():
        raise ValueError(f"The app directory `{app_dir}` does not exist.")

    # If the user specified "-" then use default configuration
    config_path: str | Path | None = config_file if config_file != "-" else None

    # If the user specified a config file, it should be in the
    # app_dir, so we need to make sure it exists. If it doesn't,
    # write the default configuration to that path.
    if config_path:
        config_path = app_dir / config_path

        # If it doesn't exist, write the default values to it
        if not config_path.exists():
            await Configuration(
                app_dir=app_dir,
                config_file=config_path
            ).to_file(config_path)

    # Read the configuration file and build the full
    # model from it, the environment vars, and the CLI args.
    typer_context.obj = await Configuration.build(
        files=[] if not config_path else [config_path],
        dotenv_files=dotenv,
        env_prefix="FLOWCTL",
        app_dir=app_dir,
        config_file=config_file,
        dev_mode=dev_mode,
    )

    if server:
        if is_url(server):
            typer_context.obj.servers.append(Server(name="cli", url=server))
            typer_context.obj.current_server = "cli"
        else:
            if server not in [server.name for server in typer_context.obj.servers]:
                raise RuntimeError(f"Server `{server}` does not exist.")
            typer_context.obj.current_server = server
