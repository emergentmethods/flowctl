from typing import Any
from datetime import datetime
from jmespath import compile as _parse_jmespath, functions, Options


class CustomFunctions(functions.Functions):
    """
    Custom JMESPath functions
    """

    @functions.signature({"types": ["string", "number"]}, {"types": ["string", "number"]})
    def _func_timedelta(self, left, right):
        """
        Calculate the difference between two datetimes.
        """
        if isinstance(left, str):
            left = datetime.fromisoformat(left)
        elif isinstance(left, int):
            left = datetime.fromtimestamp(left)

        if isinstance(right, str):
            right = datetime.fromisoformat(right)
        elif isinstance(right, int):
            right = datetime.fromtimestamp(right)

        return (left - right).total_seconds()


jmespath_options = Options(custom_functions=CustomFunctions())


def query_jmespath(query: str, data: Any) -> Any:
    """
    Parse a JMESPath and search the given data.

    :param query: The JMESPath query to parse.
    :type query: str
    :param data: The data to search.
    :type data: Any
    :returns: The results of the search.
    :rtype: Any
    """
    path = _parse_jmespath(query)
    return path.search(data, options=jmespath_options)
