import typer

from flowctl.cli import cli
from flowctl.base import AsyncTyper
from flowctl.config import Configuration
from flowctl.render import (
    render_syntax,
)
from flowctl.utils import serialize_as
from flowctl.pydantic import model_dump_json_safe


config_cli = AsyncTyper(
    name="config",
    short_help="Commands for managing flowctl configuration.",
    help=__doc__
)
cli.add_typer(config_cli)


@config_cli.command()
async def show(
    typer_context: typer.Context,
    format: str = typer.Option(
        "yaml",
        "--format",
        "-f",
        help="The format to render the configuration as."
    ),
    raw: bool = typer.Option(
        False,
        "--raw"
    )
):
    """
    Show the resolved Configuration.

    Specify the format with the `--format` option. Defaults to `yaml`.
    Renders the configuration as a syntax highlighted string if `--raw` is not specified.
    """

    config: Configuration = typer_context.obj
    output = serialize_as(format, model_dump_json_safe(config))

    if raw:
        print(output)
    else:
        render_syntax(output, format)


@config_cli.command()
async def set(
    typer_context: typer.Context,
    key: str = typer.Argument(
        ...,
        help="The key to set."
    ),
    value: str = typer.Argument(
        ...,
        help="The value to set."
    ),
):
    """
    Set the specified key to the specified value in the configuration file.
    """

    config: Configuration = typer_context.obj

    if not config.full_path:
        raise RuntimeError("Cannot set configuration value when config file is deactivated.")
    else:
        config = config.set_by_key(key, value)
        await config.to_file(config.full_path)


@config_cli.command()
async def get(
    typer_context: typer.Context,
    key: str = typer.Argument(
        ...,
        help="The key to get."
    ),
):
    """
    Get the specified key from the configuration file.
    """
    config: Configuration = typer_context.obj
    print(config.get_by_key(key))


@config_cli.command()
async def current(
    typer_context: typer.Context,
) -> None:
    """
    Get the current server.
    """
    config: Configuration = typer_context.obj
    print(config.current_server)


@config_cli.command()
async def use(
    typer_context: typer.Context,
    server_name: str = typer.Argument(
        ...,
        help="The server to use."
    ),
) -> None:
    """
    Set the current server.
    """
    config: Configuration = typer_context.obj

    if not config.full_path:
        raise RuntimeError("Cannot set configuration value when config file is deactivated.")
    else:
        if server_name not in [server.name for server in config.servers]:
            raise RuntimeError(f"Server `{server_name}` does not exist.")

        config.current_server = server_name
        await config.to_file(config.full_path)


@config_cli.command()
async def add(
    typer_context: typer.Context,
    server_name: str = typer.Argument(
        ...,
        help="The server to add."
    ),
    url: str = typer.Argument(
        ...,
        help="The url to add."
    ),
) -> None:
    """
    Add a server to the configuration.
    """
    config: Configuration = typer_context.obj

    if not config.full_path:
        raise RuntimeError("Cannot set configuration value when config file is deactivated.")
    else:
        if server_name in config.servers:
            raise RuntimeError(f"Server `{server_name}` already exists.")

        config.servers.append({"name": server_name, "url": url})
        await config.to_file(config.full_path)


@config_cli.command()
async def remove(
    typer_context: typer.Context,
    server_name: str = typer.Argument(
        ...,
        help="The server to remove."
    ),
) -> None:
    """
    Remove a server from the configuration.
    """
    config: Configuration = typer_context.obj

    if not config.full_path:
        raise RuntimeError("Cannot set configuration value when config file is deactivated.")
    else:
        if server_name not in [server.name for server in config.servers]:
            raise RuntimeError(f"Server `{server_name}` does not exist.")

        config.servers = [server for server in config.servers if server.name != server_name]
        config.current_server = config.servers[-1].name
        await config.to_file(config.full_path)
