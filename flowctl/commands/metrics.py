import typer
from typing import Optional, Literal
from datetime import datetime

from flowctl.cli import cli
from flowctl.client import get_sdk
from flowctl.config import Configuration
from flowctl.render import build_line_plot, build_histogram_plot
from flowctl.utils import serialize_as

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

name_to_metrics = {
    "cpu": "process.runtime.cpython.cpu_time",
    "memory": "process.runtime.cpython.memory",
    "api_latency": "api_request_latency"
}


def convert_to_histogram_values(bounds, counts):
    histogram_values = []

    for i in range(len(counts)):
        # Calculate midpoint for each pair of bounds
        if i < len(bounds) - 1:
            midpoint = (bounds[i] + bounds[i + 1]) / 2
        else:
            # For the last count, use the last bound as the midpoint
            midpoint = bounds[-1]

        # Add the midpoint to the list as many times as the count
        histogram_values.extend([midpoint] * counts[i])

    return histogram_values


def process_cpu_util_metrics(metrics: list) -> list[tuple[datetime, float]]:
    return [
        (
            datetime.fromtimestamp(val.time_unix_nano // 1e9).strftime(DATE_FORMAT),
            val.value
        )
        for val in metrics
        if val.attributes.get("type") == "user"
    ]


def process_memory_util_metrics(metrics: list) -> list[tuple[datetime, float]]:
    return [
        (
            datetime.fromtimestamp(val.time_unix_nano // 1e9).strftime(DATE_FORMAT),
            val.value
        )
        for val in metrics
        if val.attributes.get("type") == "rss"
    ]


def process_api_latency_metrics(metrics: list) -> tuple:
    most_recent_bucket = metrics[-1]

    # Get the bucket bounds and counts
    bounds = most_recent_bucket.explicit_bounds
    counts = most_recent_bucket.bucket_counts

    # Convert the bounds and counts to a list of values
    histogram_values = convert_to_histogram_values(bounds, counts)

    return histogram_values, len(bounds)


def render_cpu_util_metrics(metrics: list):
    if not metrics:
        return

    dates, values = list(zip(*metrics))

    print(
        build_line_plot(values, dates, x_label="Time", y_label="CPU Utilization")
    )


def render_memory_util_metrics(metrics: list):
    if not metrics:
        return

    dates, values = list(zip(*metrics))

    print(
        build_line_plot(values, dates, x_label="Time", y_label="Memory Utilization")
    )


def render_api_latency_metrics(metrics: tuple):
    if not metrics:
        return

    values, num_buckets = metrics

    print(
        build_histogram_plot(
            [(values, "")],
            num_buckets,
            x_label="Latency (ms)",
            y_label="Number of Requests"
        )
    )


metric_processors = {
    "process.runtime.cpython.cpu_time": process_cpu_util_metrics,
    "process.runtime.cpython.memory": process_memory_util_metrics,
    "api_request_latency": process_api_latency_metrics
}
metric_renderers = {
    "process.runtime.cpython.cpu_time": render_cpu_util_metrics,
    "process.runtime.cpython.memory": render_memory_util_metrics,
    "api_request_latency": render_api_latency_metrics
}


def get_metrics_name(name: str) -> str:
    if name not in name_to_metrics:
        raise ValueError(f"Unknown metric name: {name}")

    return name_to_metrics[name]


def render_metrics(
    name: str,
    metrics: dict[str, list],
    format: Literal["graph", "raw", "json", "yaml"]
):
    metrics_values = metrics.get(name, [])
    processed_values = metric_processors[name](metrics_values)

    match format:
        case "graph":
            metric_renderers[name](processed_values)
        case "raw":
            print(processed_values)
        case "json":
            print(serialize_as("json", processed_values))
        case "yaml":
            print(serialize_as(processed_values, "yaml"))
        case _:
            raise ValueError(f"Unknown format: {format}")


@cli.command("metrics")
async def metrics(
    typer_context: typer.Context,
    name: str = typer.Argument(
        "cpu",
        help="The name of the metric to get."
    ),
    start_time: Optional[datetime] = typer.Option(
        None,
        "--start-time",
        "-s",
        help="The start time of the metric to get."
    ),
    end_time: Optional[datetime] = typer.Option(
        None,
        "--end-time",
        "-e",
        help="The end time of the metric to get."
    ),
    limit: int = typer.Option(
        30,
        "--limit",
        "-l",
        help="The maximum number of data points to get."
    ),
    format: str = typer.Option(
        "graph",
        "--format",
        "-f",
        help="The format to render the metrics in. Options are: graph, raw, json, yaml."
    ),
):
    """
    Get information about the metrics of the server.
    """
    config: Configuration = typer_context.obj
    name = get_metrics_name(name)
    limit = None if limit < 0 else limit

    async with get_sdk(config) as sdk:
        metrics = await sdk.metrics.metrics(
            name=name,
            start_time=start_time,
            end_time=end_time,
            max_length=limit,
            # Update the version used when logic changes for this command
            # and metrics DTOs are updated.
            version="v1alpha1"
        )

    render_metrics(name, metrics.root, format=format)
