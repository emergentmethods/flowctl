import typer

from flowctl.cli import cli
from flowctl.client import get_sdk
from flowctl.config import Configuration
from flowctl.resources import (
    normalize_resource_kind,
    get_resource,
    render_resources_output
)
from flowctl.pydantic import model_dump_json_safe


@cli.command(
    "inspect", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
async def inspect(
    typer_context: typer.Context,
    resource_kind: str = typer.Argument(
        ...,
        help="The kind of resource to get."
    ),
    resource_identifier: str = typer.Argument(
        ...,
        help="The identifier of the resource to get."
    ),
):
    """
    Describe a resource of a specific kind.
    """
    # TODO: Change how we display resource inspect information using renderables
    # from rich instead of just rendering as yaml

    config: Configuration = typer_context.obj
    resource_kind, _ = normalize_resource_kind(resource_kind)
    resource = None

    async with get_sdk(config) as sdk:
        resource = await get_resource(sdk, resource_kind, resource_identifier)

    if resource:
        render_resources_output(resource_kind, model_dump_json_safe(resource), format="yaml")
