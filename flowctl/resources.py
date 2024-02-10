from typing import Any, Literal
from pathlib import Path
from humanize import naturaltime, naturaldelta
from datetime import datetime
from manifest import Manifest
from pydantic import Field, BaseModel

from flowctl.utils import (
    validate_args_kwargs,
    serialize_as,
)
from flowctl.render import render_table
from flowctl.constants import KNOWN_DEFINITION_EXTS
from flowctl.client import (
    FlowdaptSDK,
    ResourceNotFoundError,
)

table_render_format = "plain"
table_render_align = "left"

resource_kinds = {"workflow", "workflow_run", "trigger_rule", "config", "plugin"}
resource_definition_kinds = {"workflow", "trigger_rule", "config"}
resource_kind_aliases = {
    ("workflow",): "workflow",
    ("workflow_run", "run",): "workflow_run",
    ("trigger_rule", "trigger",): "trigger_rule",
    ("config",): "config",
    ("plugin",): "plugin",
}
resource_kind_plural_aliases = {
    ("workflows",): "workflow",
    ("workflow_runs", "runs",): "workflow_run",
    ("trigger_rules", "triggers",): "trigger_rule",
    ("configs",): "config",
    ("plugins",): "plugin",
}
resource_supported_versions = {
    "workflow": ["v1alpha1"],
    "workflow_run": ["v1alpha1"],
    "trigger_rule": ["v1alpha1"],
    "config": ["v1alpha1"],
    "plugin": ["v1alpha1"],
}

get_resource_methods = {
    "workflow": lambda sdk, identifier, *, version: sdk.workflows.get_workflow(
        identifier, version=version
    ),
    "workflow_run": lambda sdk, identifier, *, version: sdk.workflows.get_workflow_run(
        identifier, version=version
    ),
    "trigger_rule": lambda sdk, identifier, *, version: sdk.triggers.get_trigger(
        identifier, version=version
    ),
    "config": lambda sdk, identifier, *, version: sdk.configs.get_config(
        identifier, version=version
    ),
    "plugin": lambda sdk, identifier, *, version: sdk.plugins.get_plugin(
        identifier, version=version
    ),
}
delete_resource_methods = {
    "workflow": lambda sdk, identifier, *, version: sdk.workflows.delete_workflow(
        identifier, version=version
    ),
    "workflow_run": lambda sdk, identifier, *, version: sdk.workflows.delete_workflow_run(
        identifier, version=version
    ),
    "trigger_rule": lambda sdk, identifier, *, version: sdk.triggers.delete_trigger(
        identifier, version=version
    ),
    "config": lambda sdk, identifier, *, version: sdk.configs.delete_config(
        identifier, version=version
    ),
}
list_resource_methods = {
    "workflow": lambda sdk, *, version: sdk.workflows.list_workflows(
        version=version
    ),
    "workflow_run": lambda sdk, identifier, *, version, limit=10: sdk.workflows.list_workflow_runs(
        identifier, limit=limit, version=version
    ),
    "trigger_rule": lambda sdk, *, version: sdk.triggers.list_triggers(
        version=version
    ),
    "config": lambda sdk, *, version: sdk.configs.list_configs(
        version=version
    ),
    "plugin": lambda sdk, *, version: sdk.plugins.list_plugins(
        version=version
    ),
}
create_resource_methods = {
    "workflow": lambda sdk, definition, *, version: sdk.workflows.create_workflow(
        definition, version=version
    ),
    "trigger_rule": lambda sdk, definition, *, version: sdk.triggers.create_trigger(
        definition, version=version
    ),
    "config": lambda sdk, definition, *, version: sdk.configs.create_config(
        definition, version=version
    ),
}
update_resource_methods = {
    "workflow": lambda sdk, identifier, definition, *, version: sdk.workflows.update_workflow(
        identifier, definition, version=version
    ),
    "trigger_rule": lambda sdk, identifier, definition, *, version: sdk.triggers.update_trigger(
        identifier, definition, version=version
    ),
    "config": lambda sdk, identifier, definition, *, version: sdk.configs.update_config(
        identifier, definition, version=version
    ),
}


resource_table_renderers = {
    "workflow": lambda resources: render_table(
        [
            "UID",
            "NAME",
            "CREATED",
        ],
        [
            [
                resource["metadata"]["uid"],
                resource["metadata"]["name"],
                naturaltime(
                    datetime.utcnow() - datetime.fromisoformat(resource["metadata"]["created_at"])
                ),
            ]
            for resource in resources
        ],
        align=table_render_align,
        box_format=table_render_format
    ),
    "workflow_run": lambda resources: render_table(
        [
            "UID",
            "NAME",
            "STATUS",
            "STARTED",
            "DURATION"
        ],
        [
            [
                resource["uid"],
                resource["name"],
                resource["state"],
                naturaltime(datetime.utcnow() - datetime.fromisoformat(resource["started_at"])),
                naturaldelta(
                    datetime.fromisoformat(
                        resource["finished_at"]
                    ) - datetime.fromisoformat(
                        resource["started_at"]
                    )
                )
                if resource["finished_at"] else "..."
            ]
            for resource in resources
        ],
        align=table_render_align,
        box_format=table_render_format
    ),
    "trigger_rule": lambda resources: render_table(
        [
            "UID",
            "NAME",
            "TYPE",
            "CREATED",
        ],
        [
            [
                resource["metadata"]["uid"],
                resource["metadata"]["name"],
                resource["spec"]["type"],
                naturaltime(
                    datetime.utcnow() - datetime.fromisoformat(
                        resource["metadata"]["created_at"]
                    )
                )
            ]
            for resource in resources
        ],
        align=table_render_align,
        box_format=table_render_format
    ),
    "config": lambda resources: render_table(
        [
            "UID",
            "NAME",
            "TYPE",
            "CREATED",
        ],
        [
            [
                resource["metadata"]["uid"],
                resource["metadata"]["name"],
                resource["spec"]["selector"]["type"] if resource["spec"]["selector"] else "",
                naturaltime(
                    datetime.utcnow() - datetime.fromisoformat(
                        resource["metadata"]["created_at"]
                    )
                )
            ]
            for resource in resources
        ],
        align=table_render_align,
        box_format=table_render_format
    ),
    "plugin": lambda resources: render_table(
        [
            "NAME",
            "MODULE",
            "VERSION"
        ],
        [
            [
                resource["name"],
                resource["module"],
                resource["metadata"]["version"]
            ]
            for resource in resources
        ],
        align=table_render_align,
        box_format=table_render_format
    ),
}


class ResourceDefinition(Manifest, extra="allow"):
    version: str | None = Field(None, exclude=True)
    kind: str


async def parse_resource_definition(file_path: Path) -> tuple[dict, str, str]:
    definition = await ResourceDefinition.from_file(file_path)

    if definition.kind not in resource_definition_kinds:
        raise ValueError(f"Unknown resource kind: {definition.kind}")

    if definition.version and \
       definition.version not in resource_supported_versions[definition.kind]:
        raise ValueError(
            f"Unsupported resource version: {definition.version}"
            f" for resource kind: {definition.kind}, supported versions: "
            f"{resource_supported_versions[definition.kind]}"
        )

    return definition.normalize(), definition.version, definition.kind


def filter_definition_paths(file_paths: list[Path]) -> list[Path]:
    return [
        file_path for file_path in file_paths
        if file_path.suffix in KNOWN_DEFINITION_EXTS
    ]


def render_resources_table(resource_kind: str, resources: list[dict]):
    renderer = resource_table_renderers[resource_kind]
    renderer(resources)


def render_resources_output(
    resource_kind: str,
    resources: dict | list[dict],
    format: Literal["table", "json", "yaml", "raw"] = "table"
):
    match format:
        case "table":
            resources = [resources] if not isinstance(resources, list) else resources
            render_resources_table(resource_kind, resources)
        case "json" | "yaml":
            print(serialize_as(format, resources))
        case "raw":
            print(resources)
        case _:
            raise ValueError(f"Unknown output format: {format}")


def normalize_resource_kind(resource_kind: str) -> tuple[str, bool]:
    normalized_kind = resource_kind.lower()

    for aliases, kind in resource_kind_plural_aliases.items():
        if normalized_kind in aliases:
            return kind, True

    for aliases, kind in resource_kind_aliases.items():
        if normalized_kind in aliases:
            return kind, False

    raise ValueError(f"No known resource: {resource_kind}")


def get_latest_supported_version(resource_kind: str) -> str:
    return resource_supported_versions[resource_kind][-1]


def get_resource_name(resource: dict | BaseModel, resource_kind: str, _default=None):
    match resource_kind:
        case "workflow":
            if isinstance(resource, dict):
                return resource["metadata"]["name"]
            else:
                return getattr(getattr(resource, "metadata", object), "name", _default)
        case "workflow_run":
            if isinstance(resource, dict):
                return resource["name"]
            else:
                return getattr(resource, "name", _default)
        case "trigger_rule":
            if isinstance(resource, dict):
                return resource["metadata"]["name"]
            else:
                return getattr(getattr(resource, "metadata", object), "name", _default)
        case "config":
            if isinstance(resource, dict):
                return resource["metadata"]["name"]
            else:
                return getattr(resource, "metadata", {}).get("name", _default)
        case "plugin":
            if isinstance(resource, dict):
                return resource["name"]
            else:
                return getattr(resource, "name", _default)
        case _:
            return _default


async def get_resource(
    sdk: FlowdaptSDK,
    resource_kind: str,
    resource_identifier: str,
    *args,
    version: str | None = None,
    **kwargs,
) -> Any:
    if resource_kind not in resource_kinds:
        raise ValueError(f"Unknown resource kind: {resource_kind}")

    if resource_kind not in get_resource_methods:
        raise ValueError(f"Resource kind {resource_kind} does not support `get`.")

    if not resource_identifier:
        raise ValueError(f"Resource identifier required for resource kind: {resource_kind}")

    getter = get_resource_methods[resource_kind]

    args = (sdk, resource_identifier, *args)
    kwargs["version"] = version or get_latest_supported_version(resource_kind)
    args, kwargs = validate_args_kwargs(getter, args, kwargs)

    try:
        return await getter(*args, **kwargs)
    except ResourceNotFoundError:
        return None


async def list_resources(
    sdk: FlowdaptSDK,
    resource_kind: str,
    resource_identifier: str | None,
    *args,
    version: str | None = None,
    **kwargs,
) -> list:
    if resource_kind not in resource_kinds:
        raise ValueError(f"Unknown resource kind: {resource_kind}")

    if resource_kind not in list_resource_methods:
        raise ValueError(f"Resource kind {resource_kind} does not support `list`.")

    lister = list_resource_methods[resource_kind]

    if resource_identifier:
        args = (resource_identifier, *args)

    args = (sdk, *args)
    kwargs["version"] = version or get_latest_supported_version(resource_kind)
    args, kwargs = validate_args_kwargs(lister, args, kwargs)

    return await lister(*args, **kwargs)


async def delete_resource(
    sdk: FlowdaptSDK,
    resource_kind: str,
    resource_identifier: str,
    *args,
    version: str | None = None,
    **kwargs,
) -> Any:
    if resource_kind not in resource_kinds:
        raise ValueError(f"Unknown resource kind: {resource_kind}")

    if resource_kind not in delete_resource_methods:
        raise ValueError(f"Resource kind {resource_kind} does not support `delete`.")

    deleter = delete_resource_methods[resource_kind]

    args = (sdk, resource_identifier, *args)
    kwargs["version"] = version or get_latest_supported_version(resource_kind)
    args, kwargs = validate_args_kwargs(deleter, args, kwargs)

    try:
        return await deleter(*args, **kwargs)
    except ResourceNotFoundError:
        return None


async def create_resource(
    sdk: FlowdaptSDK,
    resource_kind: str,
    definition: dict,
    *args,
    version: str | None = None,
    **kwargs,
) -> Any:
    if resource_kind not in resource_kinds:
        raise ValueError(f"Unknown resource kind: {resource_kind}")

    if resource_kind not in create_resource_methods:
        raise ValueError(f"Resource kind {resource_kind} does not support `create`.")

    creator = create_resource_methods[resource_kind]

    args = (sdk, definition, *args)
    kwargs["version"] = version or get_latest_supported_version(resource_kind)
    args, kwargs = validate_args_kwargs(creator, args, kwargs)

    return await creator(*args, **kwargs)


async def update_resource(
    sdk: FlowdaptSDK,
    resource_kind: str,
    resource_identifier: str,
    definition: dict,
    *args,
    version: str | None = None,
    **kwargs,
) -> Any:
    if resource_kind not in resource_kinds:
        raise ValueError(f"Unknown resource kind: {resource_kind}")

    if resource_kind not in update_resource_methods:
        raise ValueError(f"Resource kind {resource_kind} does not support `update`.")

    updater = update_resource_methods[resource_kind]

    args = (sdk, resource_identifier, definition, *args)
    kwargs["version"] = version or get_latest_supported_version(resource_kind)
    args, kwargs = validate_args_kwargs(updater, args, kwargs)

    return await updater(*args, **kwargs)
