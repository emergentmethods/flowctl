import typer
from typing import Optional
from manifest.utils import coerce_to_basic_types

from flowctl.cli import cli
from flowctl.client import get_sdk
from flowctl.config import Configuration
from flowctl.resources import (
    normalize_resource_kind,
    get_resource,
    update_resource,
    get_resource_name,
)
from flowctl.render import render
from flowctl.pydantic import model_dump_json_safe
from flowctl.utils import parse_complex_args, exit_with_code, deep_merge_dicts


@cli.command("patch", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
async def patch(
    typer_context: typer.Context,
    resource_kind: str = typer.Argument(
        ...,
        help="The kind of resource to get."
    ),
    resource_identifier: Optional[str] = typer.Argument(
        None,
        help="The identifier of the resource to get."
    ),
    schema_version: Optional[str] = typer.Option(
        None,
        "--schema-version",
        "-s",
        help="The schema version to use when validating the resource.",
    ),
):
    """
    Patch a Resource given a kind, identifier, and set of options.
    """
    config: Configuration = typer_context.obj
    resource_kind, _ = normalize_resource_kind(resource_kind)
    _, kwargs = parse_complex_args(typer_context.args)
    kwargs = {k: coerce_to_basic_types(v) for k, v in kwargs.items()}

    async with get_sdk(config) as sdk:
        resource = await get_resource(
            sdk,
            resource_kind,
            resource_identifier,
            version=schema_version
        )

        if resource:
            resource = model_dump_json_safe(resource)
            patched_resource = deep_merge_dicts(resource, kwargs)

            resource = await update_resource(
                sdk,
                resource_kind,
                resource_identifier,
                patched_resource,
                version=schema_version
            )
            name = get_resource_name(resource, resource_kind, resource_identifier)

            render(f"[bold]\\[{resource_kind}/{name}][/] updated")
        else:
            exit_with_code(1)
