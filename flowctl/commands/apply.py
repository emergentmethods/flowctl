import typer
from pathlib import Path

from flowctl.cli import cli
from flowctl.client import get_sdk
from flowctl.config import Configuration
from flowctl.render import render
from flowctl.resources import (
    parse_resource_definition,
    filter_definition_paths,
    get_resource_name,
    get_resource,
    create_resource,
    update_resource,
)
from flowctl.utils import expand_file_paths


@cli.command("apply")
async def apply(
    typer_context: typer.Context,
    paths: list[Path] = typer.Option(
        ...,
        "--path",
        "-p",
        help="The path to a file or directory containing the resource(s) to apply.",
    )
) -> None:
    """
    Apply one or more resource definition files.
    """
    config: Configuration = typer_context.obj
    paths, not_found = expand_file_paths(paths)

    if not_found:
        for path in not_found:
            render("[red]Error:[/] File not found:", path, highlight=False)

    filtered_paths = filter_definition_paths(paths)

    for path in paths:
        if path not in filtered_paths:
            render("[red]Error:[/] File not resource definition:", path, highlight=False)

    if filtered_paths:
        async with get_sdk(config) as sdk:
            for path in filtered_paths:
                resource, resource_version, resource_kind = await parse_resource_definition(path)
                name = get_resource_name(resource, resource_kind)

                if not name:
                    render("[red]Error:[/] Resource name not found:", path, highlight=False)
                    continue

                existing_resource = await get_resource(sdk, resource_kind, name)

                if existing_resource:
                    resource = await update_resource(
                        sdk,
                        resource_kind,
                        name,
                        resource,
                        version=resource_version
                    )
                    render(f"[bold]\\[{resource_kind}/{name}][/] updated")
                else:
                    resource = await create_resource(
                        sdk,
                        resource_kind,
                        resource,
                        version=resource_version
                    )
                    render(f"[bold]\\[{resource_kind}/{name}][/] created")
