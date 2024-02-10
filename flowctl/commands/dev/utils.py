import typer
import typer.core
from click import Command, Group, Option, Argument, Choice, DateTime, IntRange, FloatRange
from typing import cast


def _format_table_option_type(option: Option) -> str:
    _HTML_PIPE = "&#x7C;"

    typename = option.type.name

    if isinstance(option.type, Choice):
        # @click.option(..., type=click.Choice(["A", "B", "C"]))
        # -> choices (`A` | `B` | `C`)
        choices = f" {_HTML_PIPE} ".join(f"`{choice}`" for choice in option.type.choices)
        return f"{typename} ({choices})"

    if isinstance(option.type, DateTime):
        # @click.option(..., type=click.DateTime(["A", "B", "C"]))
        # -> datetime (`%Y-%m-%d` | `%Y-%m-%dT%H:%M:%S` | `%Y-%m-%d %H:%M:%S`)
        formats = f" {_HTML_PIPE} ".join(f"`{fmt}`" for fmt in option.type.formats)
        return f"{typename} ({formats})"

    if isinstance(option.type, (IntRange, FloatRange)):
        if option.type.min is not None and option.type.max is not None:
            # @click.option(..., type=click.IntRange(min=0, max=10))
            # -> integer range (between `0` and `10`)
            return f"{typename} (between `{option.type.min}` and `{option.type.max}`)"
        elif option.type.min is not None:
            # @click.option(..., type=click.IntRange(min=0))
            # -> integer range (`0` and above)
            return f"{typename} (`{option.type.min}` and above)"
        else:
            # @click.option(..., type=click.IntRange(max=10))
            # -> integer range (`10` and below)
            return f"{typename} (`{option.type.max}` and below)"

    # -> "boolean", "text", etc.
    return typename


def create_title(obj: Command, indent: int, name: str, call_prefix: str) -> str:
    docs = "#" * (1 + indent)
    command_name = name or obj.name
    if call_prefix:
        command_name = f"{call_prefix} {command_name}"
    title = f"`{command_name}`" if command_name else "CLI"
    return docs + f" {title}\n\n"


def add_help_section(obj: Command) -> str:
    return f"{obj.help}\n\n" if obj.help else ""


def create_usage_section(obj: Command, ctx: typer.Context, command_name: str) -> str:
    usage_pieces = obj.collect_usage_pieces(ctx)
    if not usage_pieces:
        return ""
    docs = "**Usage**:\n\n"
    docs += "```bash\n"
    docs += "$ "
    if command_name:
        docs += f"{command_name} "
    docs += f"{' '.join(usage_pieces)}\n"
    docs += "```\n\n"
    return docs


def create_params_sections(obj: Command, ctx: typer.Context, style: str = "simple") -> str:
    args: list[Argument] = []
    opts: list[Option] = []

    for param in obj.get_params(ctx):
        if param.param_type_name == "argument":
            args.append(cast(Argument, param))
        elif param.param_type_name == "option":
            opts.append(cast(Option, param))

    match style:
        case "table":
            return create_args_section(args, ctx) + create_opts_section_table(opts)
        case "simple" | _:
            return create_args_section(args, ctx) + create_opts_section_simple(opts)  # type: ignore


def create_args_section(args: list[Argument], ctx: typer.Context) -> str:
    if not args:
        return ""
    docs = "**Arguments**:\n\n"
    for arg in args:
        help_record = arg.get_help_record(ctx)
        if help_record:
            arg_name, arg_help = help_record
        else:
            arg_name, arg_help = arg.name or "", ""

        docs += f"* `{arg_name}`"
        if arg_help:
            docs += f": {arg_help}"
        docs += "\n"
    docs += "\n"
    return docs


def create_opts_section_table(opts: list[Option]) -> str:
    if not opts:
        return ""
    docs = "**Options**:\n\n"
    docs += "| Name | Type | Description | Default |\n"
    docs += "| ---- | ---- | ----------- | ------- |\n"
    for opt in opts:
        opt_name = ', '.join(opt.opts + opt.secondary_opts)
        opt_type = _format_table_option_type(opt)
        opt_description = opt.help
        opt_default = opt.default if opt.default is not None else "None"
        docs += f"| `{opt_name}` | {opt_type} | {opt_description} | **{opt_default}** |\n"
    docs += "\n"
    return docs


def create_opts_section_simple(opts: list[Option]) -> str:
    if not opts:
        return ""
    docs = "**Options**:\n\n"
    for opt in opts:
        opt_name = ', '.join(opt.opts + opt.secondary_opts)
        opt_description = opt.help
        docs += f"* `{opt_name}`"
        if opt_description:
            docs += f": {opt_description}"
        docs += "\n"
    docs += "\n"
    return docs


def create_commands_section(
    group: Group,
    ctx: typer.Context,
    commands: list[str],
) -> str:
    if not commands:
        return ""
    docs = "**Commands**:\n\n"
    for command in commands:
        command_obj = group.get_command(ctx, command)
        assert command_obj
        if command_obj.hidden:
            continue
        docs += f"* `{command_obj.name}`"
        command_help = command_obj.get_short_help_str(limit=75)
        if command_help:
            docs += f": {command_help}"
        docs += "\n"
    docs += "\n"
    return docs


def add_epilog_section(obj: Command) -> str:
    return f"{obj.epilog}\n\n" if obj.epilog else ""


def get_docs_for_click(
    *,
    obj: Command,
    ctx: typer.Context,
    indent: int = 0,
    name: str = "",
    call_prefix: str = "",
    style: str = "simple"
) -> str:
    command_name = name or obj.name or ""

    if not command_name:
        raise ValueError("Command name is required.")

    if call_prefix:
        command_name = f"{call_prefix} {command_name}"

    if indent > 0:
        docs = "---\n\n"
    else:
        docs = ""

    docs += create_title(obj, indent, name, call_prefix)
    docs += add_help_section(obj)
    docs += create_usage_section(obj, ctx, command_name)
    docs += create_params_sections(obj, ctx, style)
    docs += add_epilog_section(obj)

    if isinstance(obj, Group):
        group: Group = cast(Group, obj)
        commands = group.list_commands(ctx)
        docs += create_commands_section(group, ctx, commands)
        for command in commands:
            command_obj = group.get_command(ctx, command)
            assert command_obj
            if command_obj.hidden:
                continue
            use_prefix = f"{command_name}" if command_name else ""
            docs += get_docs_for_click(
                obj=command_obj,
                ctx=ctx,
                indent=indent + 1,
                call_prefix=use_prefix,
                style=style
            )

    return docs


def generate_docs(
    typer_context: typer.Context,
    typer_app: typer.Typer,
    call_prefix: str = "",
    style: str = "simple",
):
    click_obj = typer.main.get_command(typer_app)
    docs = get_docs_for_click(
        obj=click_obj,
        ctx=typer_context,
        name=click_obj.name or "",
        call_prefix=call_prefix,
        style=style
    )
    docs = f"{docs.strip()}\n"
    return docs
