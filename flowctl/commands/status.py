import typer
from humanize import naturalsize

from flowctl.cli import cli
from flowctl.client import get_sdk
from flowctl.config import Configuration
from flowctl.render import render, build_tree, build_table


@cli.command("status")
async def status(
    typer_context: typer.Context,
):
    """
    Get the status of the Flowdapt server.
    """
    config: Configuration = typer_context.obj

    async with get_sdk(config) as sdk:
        status = await sdk.system.status()
        info = await sdk.ping()

        status_table_rows = [
            [
                service,
                f"[red]{status.get('status')}[/red]"
                if status.get('status') != "OK"
                else f"[green]{status.get('status')}[/green]",
            ]
            for service, status in status.services.items()
        ]

        render(
            build_tree(
                {
                    "Version": info.get("version"),
                    "API Version": info.get("api_version"),
                    "Name": status.name,
                    "System Metrics": {
                        "Time": status.system.time,
                        "CPU": f"{status.system.cpu_pct}%",
                        "Memory": naturalsize(status.system.memory),
                        "Disk": f"{status.system.disk_pct}%",
                        "Network IO Sent": naturalsize(status.system.network_io_sent),
                        "Network IO Received": naturalsize(status.system.network_io_recv),
                    },
                    "Operating System": {
                        "Name": status.os.name,
                        "Release": status.os.release,
                        "Machine": status.os.machine,
                    },
                    "Services": build_table(
                        columns=[],
                        rows=status_table_rows,
                        align="center",
                        show_headers=False,
                    )
                }
            )
        )
