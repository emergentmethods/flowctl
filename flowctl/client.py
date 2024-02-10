"""
Flowdapt Python Client for interacting with the Rest API.
"""
from typing import AsyncIterator
from flowdapt_sdk import FlowdaptSDK
from flowdapt_sdk.errors import (
    APIError,
    ResourceNotFoundError,
)
from contextlib import asynccontextmanager

from flowctl.config import Configuration


@asynccontextmanager
async def get_sdk(configuration: Configuration) -> AsyncIterator[FlowdaptSDK]:
    """
    Given a configuration object, enter a FlowdaptSDK object.

    :param configuration: The configuration object.
    :type configuration: Configuration
    :yields: The FlowdaptSDK
    """
    server = configuration.get_server(configuration.current_server)
    async with FlowdaptSDK(base_url=server.url) as client:
        yield client


__all__ = (
    "get_sdk",
    "FlowdaptSDK",
    "APIError",
    "ResourceNotFoundError",
)
