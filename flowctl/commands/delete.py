import typer
from typing import Optional
from pathlib import Path

from flowctl.cli import cli
from flowctl.client import get_sdk
from flowctl.config import Configuration
from flowctl.render import render
from flowctl.resources import (
    normalize_resource_kind,
    parse_resource_definition,
    filter_definition_paths,
    get_resource_name,
    delete_resource,
)
from flowctl.utils import parse_complex_args, expand_file_paths


@cli.command("delete", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
async def delete(
    typer_context: typer.Context,
    resource_kind: Optional[str] = typer.Argument(
        None,
        help="The kind of resource to get."
    ),
    resource_identifier: Optional[str] = typer.Argument(
        None,
        help="The identifier of the resource to get."
    ),
    paths: Optional[list[Path]] = typer.Option(
        None,
        "--path",
        "-p",
        help="The path to a file or directory containing the resource(s) to delete.",
    )
):
    """
    Delete one or more resources of a specific kind.
    """
    if (not resource_identifier or not resource_kind) and not paths:
        raise ValueError("Either a resource kind and identifier or path must be provided.")
    elif resource_identifier and resource_kind and paths:
        raise ValueError(
            "Either a resource kind and identifier or path must be provided, not both."
        )

    config: Configuration = typer_context.obj
    args, kwargs = parse_complex_args(typer_context.args)

    if paths:
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
                    resource, _, resource_kind = await parse_resource_definition(path)
                    name = get_resource_name(resource, resource_kind)

                    if not name:
                        render("[red]Error:[/] Resource name not found:", path, highlight=False)
                        continue

                    await delete_resource(sdk, resource_kind, name)
                    render(f"[bold]\\[{resource_kind}/{name}][/] deleted")
    else:
        resource_kind, _ = normalize_resource_kind(resource_kind)

        async with get_sdk(config) as sdk:
            resource = await delete_resource(
                sdk,
                resource_kind,
                resource_identifier,
                *args,
                **kwargs
            )
            name = get_resource_name(resource, resource_kind)
            render(f"[bold]\\[{resource_kind}/{name}][/] deleted")
