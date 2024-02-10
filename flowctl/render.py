import plotext as plt
from datetime import datetime
from typing import Literal, Any
from pathlib import Path
from rich import print as pprint, box
from rich.console import Console, RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.align import Align
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table
from rich.tree import Tree
from rich.rule import Rule
from rich.layout import Layout


box_formats = {
    "plain": None,
    "simple": box.SIMPLE_HEAD,
    "rounded": box.ROUNDED,
    "markdown": box.MARKDOWN,
    "ascii": box.ASCII
}


def render_exceptions_table(exceptions: list[tuple[str, Path, BaseException]]):
    render_table(
        columns=["Name", "Path", "Error"],
        rows=[
            [
                f"[blue_violet]{name}",
                path.as_posix(),
                f"[red]{str(exc)}"
            ]
            for name, path, exc in exceptions
        ]
    )


def render_table(
    columns: list[str],
    rows: list[list[str]],
    align: Literal["left", "center", "right"] = "center",
    **kwargs
):
    render(build_table(columns=columns, rows=rows, align=align, **kwargs))


def render_panel(
    message: RenderableType,
    title: str = "",
    subtitle: str = "",
    align: Literal["left", "center", "right"] = "center",
    fit: bool = True
):
    render(
        build_panel(
            message,
            title=title,
            subtitle=subtitle,
            align=align,
            fit=fit,
        )
    )


def render_syntax(syntax: RenderableType, language: str = "yaml", theme: str = "dracula"):
    render(
        build_syntax(
            syntax=syntax,
            language=language,
            theme=theme
        )
    )

def render(renderable, *args, highlight: bool = False, **kwargs):
    console = Console()
    console.print(renderable, *args, highlight=highlight, **kwargs)


def build_markdown(markdown: RenderableType):
    return Markdown(markdown)


def build_panel(
    content: RenderableType,
    title: str = "",
    subtitle: str = "",
    align: Literal["left", "center", "right"] = "left",
    fit: bool = True,
    padding: tuple = (1, 2),
    box_format: str = "rounded"
):
    return Panel(
        Align(content, align=align),
        title=title,
        subtitle=f"[#222222]{subtitle}" if subtitle else "",
        box=box_formats.get(box_format, box.SIMPLE),
        expand=fit,
        padding=padding
    )


def build_error_panel(
    message: RenderableType,
    subtitle: str = "",
    align: Literal["left", "center", "right"] = "left",
    fit: bool = True,
    padding: tuple = (1, 2),
    box_format: str = "rounded"
):
    return build_panel(
        message,
        title="[red]Error",
        subtitle=subtitle,
        align=align,
        fit=fit,
        padding=padding,
        box_format=box_format
    )


def build_result_panel(message: RenderableType, subtitle: str = ""):
    return build_panel(message, title="[blue_violet]Result", subtitle=subtitle)


def build_syntax(syntax: RenderableType, language: str = "yaml", theme: str = "dracula"):
    return Syntax(
        syntax,
        language,
        line_numbers=True,
        background_color="default",
        theme=theme
    )


def build_table(
    columns: list[str] = [],
    rows: list[list[str]] = [],
    box_format: str = "simple",
    align: Literal["left", "center", "right"] = "left",
    pad_edges: bool = True,
    padding: tuple = (0, 1),
    show_headers: bool = True,
    show_lines: bool = True,
    expand: bool = False,
    min_width: int | None = None,
):
    table = Table(
        show_header=show_headers,
        header_style="bold",
        pad_edge=pad_edges,
        padding=padding,
        expand=expand,
        show_lines=show_lines,
        min_width=min_width,
        box=box_formats.get(box_format, box.SIMPLE),
    )
    for column in columns:
        table.add_column(column, justify=align)

    for row in rows:
        table.add_row(*row)

    return table


def build_tree(data: dict | list, label: str | None = None):
    def build_tree_children(tree: Tree, data: Any):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, RenderableType) and not isinstance(value, str):
                    subtree = tree.add(f"[bold]{key}")
                    build_tree_children(subtree, value)
                elif isinstance(value, dict):
                    subtree = tree.add(f"[bold]{key}")
                    build_tree_children(subtree, value)
                elif isinstance(value, list):
                    subtree = tree.add(f"[bold]{key}[/] [dim]({len(value)} items)")
                    build_tree_children(subtree, value)
                else:
                    tree.add(f"[bold]{key}[/]: {value}")
        elif isinstance(data, list):
            for item in data:
                subtree = tree.add("┐")
                build_tree_children(subtree, item)
        else:
            if isinstance(data, RenderableType):
                tree.add(data)
            else:
                tree.add(str(data))

    if label:
        tree = Tree(f"[bold]{label}")
    else:
        tree = Tree("", hide_root=False)

    build_tree_children(tree, data)
    return tree


def build_hr(end: str = "", align: Literal["left", "center", "right"] = "center"):
    return Rule(end=end, align=align, style="dim")


def build_layout(
    renderables: list[RenderableType] | None = None,
    name: str = "main",
    direction: Literal["row", "column"] = "row",
    size: int | None = None,
    min_size: int = 1,
    ratio: int = 1,
    visible: bool = True,
):
    layout = Layout(
        name=name,
        size=size,
        minimum_size=min_size,
        ratio=ratio,
        visible=visible
    )

    if renderables:
        match direction:
            case "row":
                layout.split_row(*renderables)
            case "column":
                layout.split_column(*renderables)

    return layout


def build_dag_layout(
    dag: dict[str, tuple[RenderableType, list[str]]],
    direction: Literal["ttb", "ltr"] = "ttb",
    name: str = "main",
    size: int | None = None,
    min_size: int = 1,
    ratio: int = 1,
    visible: bool = True,
):
    """
    Example DAG:

    dag = {
        "A": (content, ["B", "C"]),
        "B": (content, ["D"]),
        "C": (content, ["D"]),
        "D": (content, [])
    }

    Resulting layout should look like this:

    +-----------------+-----------------+-----------------+
    |                                                     |
    |                          A                          |
    |                                                     |
    +-----------------+--------+--------+-----------------+
    |                          |                          |
    |        B                 |                 C        |
    |                          |                          |
    +-----------------+--------+--------+-----------------+
    |                                                     |
    |                          D                          |
    |                                                     |
    +-----------------+-----------------+-----------------+
    """
    items = []

    def get_next_level_nodes(current_nodes):
        next_level = []

        for node in current_nodes:
            for child in get_children(node):
                if child not in next_level:
                    next_level.append(child)

        return next_level

    def get_children(node):
        return dag.get(node, (None, []))[1]

    def get_content(node):
        return dag.get(node, (None, []))[0]

    all_children = {child for _, children in dag.values() for child in children}
    current_level_nodes = [node for node in dag if node not in all_children]
    i = 0

    while current_level_nodes:
        renderables = [
            build_layout(
                renderables=[
                    get_content(node) if get_content(node) else node
                ],
                name=node
            )
            for node in current_level_nodes
        ]

        items.append(
            build_layout(
                renderables,
                direction="row" if direction == "ttb" else "column",
                name=f"level-{i}"
            )
        )
        current_level_nodes = get_next_level_nodes(current_level_nodes)
        i += 1

    return build_layout(
        items if direction == "ttb" else list(reversed(items)),
        name=name,
        size=size,
        min_size=min_size,
        ratio=ratio,
        visible=visible,
        direction="column" if direction == "ttb" else "row"
    )


def track_progress_spinner(transient: bool = True):
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=transient,
        expand=True
    )


def build_line_plot(
    y: list[float],
    x: list[Any] | None = None,
    y_label: str = "",
    x_label: str = "",
    title: str = "",
    background_color: str = "default",
    ticks_color: str = "default",
) -> str:
    plt.title(title)
    plt.xlabel(x_label, xside="upper")
    plt.ylabel(y_label, yside="left")
    plt.canvas_color(background_color)
    plt.axes_color(background_color)
    plt.ticks_color(ticks_color)

    plt.date_form("Y-m-d H:M:S")

    if x and isinstance(x[0], datetime):
        x = plt.datetimes_to_string(x)

    if x:
        plt.plot(x, y)
    else:
        plt.plot(y)

    return plt.build()


def build_histogram_plot(
    data: list[tuple[list, str]],
    bins: int = 50,
    x_label: str = "",
    y_label: str = "",
    title: str = "",
    background_color: str = "default",
    ticks_color: str = "default",
) -> str:
    plt.title(title)
    plt.xlabel(x_label, xside="upper")
    plt.ylabel(y_label, yside="left")
    plt.canvas_color(background_color)
    plt.axes_color(background_color)
    plt.ticks_color(ticks_color)

    for hist, label in data:
        plt.hist(hist, bins, label=label)

    if min(*[val for val, _ in data]) >= 0:
        plt.xlim(left=0)

    return plt.build()


def confirm(message: str):
    return Confirm.ask(message)


__all__ = (
    "pprint",
    "render_exceptions_table",
    "render",
    "build_markdown",
    "build_panel",
    "build_error_panel",
    "build_result_panel",
    "build_syntax",
    "build_table",
    "track_progress_spinner",
    "confirm",
)
