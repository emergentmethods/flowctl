import typer
from typing import Optional

from flowctl.cli import cli
from flowctl.client import get_sdk
from flowctl.config import Configuration
from flowctl.resources import (
    normalize_resource_kind,
    render_resources_output,
    get_resource,
    list_resources,
)
from flowctl.pydantic import model_dump_json_safe
from flowctl.utils import parse_complex_args, exit_with_code
from flowctl.jmespath import query_jmespath


@cli.command("get", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
async def get(
    typer_context: typer.Context,
    resource_kind: str = typer.Argument(
        ...,
        help="The kind of resource to get."
    ),
    resource_identifier: Optional[str] = typer.Argument(
        None,
        help="The identifier of the resource to get."
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="The format to output the resource in. Options are `table`, `json`, `yaml` and `raw`.",
    ),
    select: Optional[str] = typer.Option(
        None,
        "--select",
        help="The select query to filter the results.",
    )
):
    """
    Get one or more resources of a specific kind.
    """
    config: Configuration = typer_context.obj
    resource_kind, plural = normalize_resource_kind(resource_kind)
    args, kwargs = parse_complex_args(typer_context.args)

    resources = None

    async with get_sdk(config) as sdk:
        if not plural:
            resources = await get_resource(
                sdk,
                resource_kind,
                resource_identifier,
                *args,
                **kwargs
            )
        else:
            resources = await list_resources(
                sdk,
                resource_kind,
                resource_identifier,
                *args,
                **kwargs
            )

    if resources:
        if isinstance(resources, list):
            resources = [model_dump_json_safe(resource) for resource in resources]
        else:
            resources = model_dump_json_safe(resources)

        if select:
            format = "json" if format == "table" else format
            resources = query_jmespath(select, resources)

            if not resources:
                exit_with_code(1)

        render_resources_output(resource_kind, resources, format=format)
    else:
        exit_with_code(1)
