import orjson
from typing import Any
from pydantic import BaseModel
from pydantic.version import VERSION as PYDANTIC_VERSION

IS_V1 = PYDANTIC_VERSION.startswith("1.")


def model_dump_json_safe(model: BaseModel, **kwargs) -> Any:
    """
    Dump a Pydantic model to JSON safe types.

    :param model: The Pydantic model to dump.
    :type model: Any
    :return: A python object representing the Pydantic model.
    :rtype: dict
    """
    if IS_V1:
        json = model.json(**kwargs)
    else:
        json = model.model_dump_json(**kwargs)

    return orjson.loads(json)
