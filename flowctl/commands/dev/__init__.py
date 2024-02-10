import typer
from pathlib import Path
from typing import Optional

from flowctl.cli import cli
from flowctl.base import AsyncTyper
from flowctl.render import (
    render,
    build_markdown,
)
from flowctl.commands.dev.utils import generate_docs


dev_cli = AsyncTyper(
    name="dev",
    short_help="Commands for useful for internal development.",
    help=__doc__,
    hidden=True
)
cli.add_typer(dev_cli)


@dev_cli.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
async def test(
    typer_context: typer.Context,
    select: Optional[str] = typer.Option(
        None,
        "--select",
        help="The select query to filter the results.",
    )
) -> None:
    """
    Testing
    """
    ...


@dev_cli.command()
async def docs(
    typer_context: typer.Context,
    output_path: Optional[Path] = typer.Argument(
        None,
        help="The path to write the documentation to. Defaults to None."
    ),
    style: str = typer.Option(
        "table",
        "--style",
        help="The style of the documentation to generate. `simple` or `table`.",
    )
):
    """
    Generate the documentation for the flowctl CLI.
    """

    if not output_path:
        # Rendering to screen requires simple
        # since tables aren't supported
        style = "simple"

    docs = generate_docs(typer_context, cli, style=style)

    if not output_path:
        render(build_markdown(docs))
    else:
        output_path.write_text(docs)
