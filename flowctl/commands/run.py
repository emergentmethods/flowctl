import typer
from typing import Optional
from manifest.utils import coerce_to_basic_types

from flowctl.cli import cli
from flowctl.client import get_sdk
from flowctl.config import Configuration
from flowctl.render import (
    render,
    track_progress_spinner
)
from flowctl.resources import (
    get_latest_supported_version,
    get_resource,
)
from flowctl.utils import (
    parse_complex_args,
    exit_with_code,
    serialize_as,
)


@cli.command("run", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
async def run(
    typer_context: typer.Context,
    resource_identifier: Optional[str] = typer.Argument(
        None,
        help="The identifier of the Workflow to run."
    ),
    format: Optional[str] = typer.Option(
        None,
        "--format",
        "-f",
        help="The output format to use.",
    ),
    result_only: bool = typer.Option(
        False,
        "--result-only",
        help="Only output the result of the run.",
    ),
    wait: bool = typer.Option(
        True,
        "--wait/--no-wait",
        help="Wait for the run to complete.",
    ),
    namespace: Optional[str] = typer.Option(
        None,
        "--namespace",
        "-n",
        help="The namespace to run the Workflow in.",
    ),
    show_progress: bool = typer.Option(
        True,
        "--show-progress/--disable-progress",
        help="Show the progress spinner while waiting for the execution.",
    ),

):
    """
    Execute a Workflow by identifier with an optional input.
    """
    config: Configuration = typer_context.obj
    args, kwargs = parse_complex_args(typer_context.args)
    kwargs = {k: coerce_to_basic_types(v) for k, v in kwargs.items()}

    async with get_sdk(config) as sdk:
        workflow = await get_resource(sdk, "workflow", resource_identifier)

        if workflow:
            if show_progress:
                with track_progress_spinner(transient=False) as progress:
                    task_id = progress.add_task(
                        f"Running [bold]workflow/{workflow.metadata.name}[/]..."
                    )
                    run = await sdk.workflows.run_workflow(
                        identifier=workflow.metadata.uid,
                        input=kwargs,
                        wait=wait,
                        namespace=namespace,
                        version=get_latest_supported_version("workflow_run"),
                    )
                    progress.update(task_id, total=1.0, completed=1.0, visible=False)
                    progress.remove_task(task_id)
                # Clear progress bar and move cursor up one line
                print("\033[A" + "\033[K", end="")
            else:
                run = await sdk.workflows.run_workflow(
                    identifier=workflow.metadata.uid,
                    input=kwargs,
                    wait=wait,
                    namespace=namespace,
                    version=get_latest_supported_version("workflow_run"),
                )

            if result_only:
                if format:
                    render(serialize_as(run.result, format))
                else:
                    render(run.result)
                return

            match run.state:
                case "finished":
                    state_color = "green"
                case "failed":
                    state_color = "red"
                case _:
                    state_color = "yellow"

            render(
                f"[bold]\\[workflow_run/{run.name}][/] "
                f"[{state_color}]\\[{run.state.upper()}][/]: "
                f"{run.result}"
            )

            if run.state != "finished":
                exit_with_code(1)

        else:
            render(f"[bold]\\[workflow/{resource_identifier}][/] not found")
