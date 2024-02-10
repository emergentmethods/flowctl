import asyncio
import typer
import re
from pydantic import AnyUrl, validate_arguments
from pathlib import Path
from typing import (
    Callable,
    Awaitable,
    Any,
    TypeVar,
    ParamSpec,
    Coroutine,
    AsyncIterator,
    Type,
    TypeGuard,
    cast
)
from manifest.parse import get_serializer_from_type
from functools import wraps, partial
from contextlib import asynccontextmanager, contextmanager
from aiofiles.tempfile import TemporaryDirectory

from flowctl.render import render
from flowctl.constants import DEV_MODE

T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")

CallableType = Callable[..., R] | Callable[..., Awaitable[R]]


def is_dev_mode() -> bool:
    """
    Check if the application is running in development mode

    :returns: True if the application is running in development mode
    :rtype: bool
    """
    return DEV_MODE

def set_dev_mode(dev_mode: bool = False):
    """
    Set the development mode of the application

    :param dev_mode: Whether or not to run in development mode
    :type dev_mode: bool
    """
    global DEV_MODE
    DEV_MODE = dev_mode


def apply_decorators(func: Callable, *decorators: Callable) -> Callable:
    """
    Apply a list of decorators to a function

    :param func: The function to apply the decorators to
    :type func: Callable
    :param decorators: The decorators to apply
    :type decorators: list[Callable]
    """
    for decorator in decorators:
        func = decorator(func)
    return func


def is_async_callable(f: CallableType) -> TypeGuard[Coroutine]:
    """
    Test if the callable is an async callable

    :param f: The callable to test
    """
    from inspect import iscoroutinefunction

    if hasattr(f, "__wrapped__"):
        f = f.__wrapped__

    return iscoroutinefunction(f)


def is_async_context_manager(o: Any) -> bool:
    """
    Test if object is an async context manager

    :param o: The object to check
    """
    return hasattr(o, "__aenter__") and hasattr(o, "__aexit__")


async def run_in_thread(callable: Callable, *args, **kwargs):
    """
    Run a sync callable in a the default ThreadPool.

    :param callable: The callable to run
    :param *args: The args to pass to the callable
    :param **kwargs: The kwargs to pass to the callable
    :returns: The return value of the callable
    """
    return await asyncio.get_running_loop().run_in_executor(
        None, partial(callable, *args, **kwargs)
    )


def to_sync(func: Callable[P, Coroutine[Any, Any, R]], use_loop: bool = False) -> Callable[P, R]:
    """
    Convert an async function to a sync function.

    :param func: async function to convert
    :return: sync function
    """
    if not is_async_callable(func):
        return cast(Callable[P, R], func)

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            loop = asyncio.get_running_loop()

            if loop.is_running() and use_loop:
                future = asyncio.run_coroutine_threadsafe(func(*args, **kwargs), loop)
                return future.result()

            return func(*args, **kwargs)
        except RuntimeError:
            return asyncio.run(func(*args, **kwargs))
    return wrapper


def to_async(func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    """
    Convert a sync function to an async function.

    :param func: sync function to convert
    :return: async function
    """
    if is_async_callable(func):
        return cast(Callable[P, Coroutine[Any, Any, R]], func)

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        return await run_in_thread(func, *args, **kwargs)
    return wrapper


def exit_with_code(code: int):
    """
    Exit the application with the given code

    :param code: The exit code to use
    :type code: int
    """
    raise typer.Exit(code=code)


def catch_exceptions(
    exceptions: tuple[Type[BaseException]] | Type[BaseException] = BaseException,
    exit_code: int = 1
):
    """
    Catch an exception and exit with the given code.

    :param exceptions: The exceptions to catch
    :type exceptions: tuple
    :param exit_code: The exit code to use
    :type exit_code: int
    :raises typer.Exit: If the exception is caught
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except typer.Exit:
                pass
            except exceptions as e:
                handle_error(e)
        return wrapper
    return decorator


def handle_error(e: BaseException):
    """
    Handle an error by rendering it to the error panel and exiting with the given code.
    """
    if is_dev_mode():
        raise e

    exit_with_error(
        str(e),
        subtitle=str(e.__class__.__name__),
        code=getattr(e, "status", None) or 1
    )


def exit_with_error(message: str, code: int = 1, subtitle: str = ""):
    """
    Exit the application with an error message and status code.

    :param message: The error message to display
    :type message: str
    :param status: The status code to use
    :type status: int
    """
    render(f"[red]Error:[/red] {message}", highlight=False)
    exit_with_code(code)


@contextmanager
def current_directory(directory: Path):
    """
    Context manager that changes the current working directory to the specified `directory`.
    Upon completion, the current working directory is restored to its original value.

    :param directory: A `Path` object representing the directory to change to.
    :type directory: Path

    :raises ValueError: If the specified path does not exist or is not a directory.

    :yields: None
    """
    import os

    # Check if the specified path exists and is a directory.
    if not directory.exists() or not directory.is_dir():
        raise ValueError(f"`{directory}` must be a directory")

    # Save the current working directory before changing it.
    old = os.getcwd()

    try:
        # Change the current working directory to the specified directory.
        os.chdir(directory)
        # Yield control back
        yield
    finally:
        # Restore the original working directory.
        os.chdir(old)


def resolve_path(file_path: Path, search_dirs: list[Path] = []) -> Path:
    """
    Get the absolute path to a file, searching in the specified directories if the file
    does not exist at the specified path.

    :param file_path: The path to the file to resolve.
    :type file_path: Path
    :param search_dirs: A list of directories to search for the file.
    :type search_dirs: list[Path]
    :returns: The absolute path to the file.
    :rtype: Path
    """
    if (resolved := file_path.resolve()).exists():
        return resolved

    for dir in search_dirs:
        if (dir / file_path).exists():
            return (dir / file_path).resolve()

    raise FileNotFoundError(
        f"`{file_path}` does not exist."
    )


def find_files_in_dir(
    dir_path: Path,
    extensions: list[str] = [],
    recursive: bool = True
):
    """
    Find all files in a directory.

    :param dir_path: The directory to search.
    :type dir_path: Path
    :param extensions: A list of file extensions to filter by.
    :type extensions: list[str]
    :param recursive: Whether or not to search recursively.
    :type recursive: bool
    :return: A list of files found in the directory.
    :rtype: list[Path]
    """
    if not dir_path.exists():
        raise FileNotFoundError(f"{dir_path} does not exist.")

    if not dir_path.is_dir():
        raise NotADirectoryError(f"{dir_path} is not a directory.")

    search_method = dir_path.rglob if recursive else dir_path.glob

    if extensions:
        return [f for f in search_method("*") if f.is_file() and f.suffix in extensions]
    else:
        return [f for f in search_method("*") if f.is_file()]


def expand_file_paths(
    file_paths: list[Path],
    recursive: bool = True
) -> tuple[list[Path], list[Path]]:
    """
    Expand a list of file paths to include all files in directories.

    :param file_paths: A list of file paths to expand.
    :type file_paths: list[Path]
    :param recursive: Whether or not to search recursively.
    :type recursive: bool
    :returns: A list of expanded file paths, and a list of file paths that were not found.
    """
    expanded, not_found = [], []
    for path in file_paths:
        path = path.resolve().expanduser()

        if path.exists() and path.is_file():
            expanded.append(path)
        elif path.is_dir():
            expanded.extend(
                find_files_in_dir(path, recursive=recursive)
            )
        elif not path.exists():
            not_found.append(path)
    return expanded, not_found


def get_app_dir(name: str = "flowdapt") -> Path:
    """
    Get the application directory. This defaults to the
    Flowdapt application directory.

    :param name: The name of the application.
    :type name: str
    :returns: The application directory.
    :rtype: Path
    """
    app_dir = Path(typer.get_app_dir(name, force_posix=True))
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_best_search_dir(search_dirs: list[Path]) -> Path:
    """
    Get the best search directory from a list of directories.

    :param search_dirs: A list of directories to search.
    :type search_dirs: list[Path]
    :returns: The best search directory.
    :rtype: Path
    """
    # If there is only one search directory, return it.
    if len(search_dirs) == 1:
        return search_dirs[0]

    # If there are multiple search directories, return the first one that exists.
    for dir in search_dirs:
        if dir.exists():
            return dir

    # If none of the search directories exist, return the current working directory.
    return Path.cwd()


@asynccontextmanager
async def contents_to_tmp_files(files: dict[str, str]) -> AsyncIterator[list[Path]]:
    """
    Create a temporary directory and save the files to disk.
    """
    tmp_files = []

    async with TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        for filename, contents in files.items():

            filepath = temp_dir / filename
            filepath.write_text(contents)

            tmp_files.append(filepath)

        yield tmp_files


def is_uuid(value: Any) -> bool:
    """
    Determine if a value is a valid UUID.

    :param value: The value to check.
    :type value: Any
    :returns: True if the value is a valid UUID, False otherwise.
    """
    from uuid import UUID

    try:
        UUID(value)
        return True
    except ValueError:
        return False


def is_url(value: Any) -> bool:
    """
    Determine if a value is a valid URL.

    :param value: The value to check.
    :type value: Any
    :returns: True if the value is a valid URL, False otherwise.
    """
    @validate_arguments
    def _is_url(value: AnyUrl) -> bool:
        return True

    try:
        _is_url(value)
        return True
    except ValueError:
        return False


def validate_args_kwargs(fn: Callable, args: tuple, kwargs: dict) -> tuple[tuple, dict]:
    """
    Validate the arguments and keyword arguments for a function.

    :param fn: The function to validate the arguments for.
    :type fn: Callable
    :param args: The arguments to validate.
    :type args: tuple
    :param kwargs: The keyword arguments to validate.
    :type kwargs: dict
    :returns: A tuple containing the validated arguments and keyword arguments.
    :rtype: tuple[tuple, dict]
    """
    from inspect import signature

    sig = signature(fn)
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()

    return bound.args, bound.kwargs

def parse_complex_args(str_args: list[str]) -> tuple[list, dict]:
    args, kwargs = [], {}
    it = iter(str_args)

    for item in it:
        if item.startswith('-'):
            key, value = parse_key(item.lstrip('-')), next(it, None)
            process_nested_key(kwargs, key, value)
        else:
            args.append(item)

    return args, kwargs

def parse_key(key: str) -> list[str]:
    # Extract nested keys and list indices, including empty brackets for list indicator
    return re.findall(r'(\w+|\[\d*\])', key)

def process_nested_key(kwargs: dict, keys: list[str], value: Any):
    for i, key in enumerate(keys):
        if key.startswith('[') and key != '[]':
            # Convert '[index]' to int index, skip '[]' as it is handled later
            keys[i] = int(key.strip('[]'))
    set_nested_value(kwargs, keys, value)

def set_nested_value(d: dict, keys: list[str], value: Any):
    for i, key in enumerate(keys[:-1]):
        next_key = keys[i + 1]

        if isinstance(key, int) or key == '[]':
            # Handle list case, including empty brackets for appending to list
            if key == '[]':
                key = len(d)  # Append to the end of the list
            while len(d) <= key:
                d.append(None)
            if d[key] is None:
                d[key] = [] if isinstance(next_key, int) or next_key == '[]' else {}
            d = d[key]
        else:
            if key not in d or d[key] is None:
                d[key] = [] if isinstance(next_key, int) or next_key == '[]' else {}
            d = d[key]

    # Set the final value
    last_key = keys[-1]
    if isinstance(last_key, int) or last_key == '[]':
        if last_key == '[]':
            last_key = len(d)  # Append to the end of the list
        while len(d) <= last_key:
            d.append(None)
        d[last_key] = value
    else:
        if last_key in d and isinstance(d[last_key], list):
            d[last_key].append(value)  # Append to existing list
        else:
            d[last_key] = value


def deep_merge_dicts(base_dict: dict, new_dict: dict) -> dict:
    merged = base_dict.copy()

    for key, new_val in new_dict.items():
        if key in merged:
            if isinstance(merged[key], dict) and isinstance(new_val, dict):
                merged[key] = deep_merge_dicts(merged[key], new_val)
            elif isinstance(merged[key], list) and isinstance(new_val, list):
                merged[key] = merge_lists(merged[key], new_val)
            else:
                merged[key] = new_val
        else:
            merged[key] = new_val

    return merged


def merge_lists(base_list: list, new_list: list) -> list:
    merged = base_list.copy()

    for i, new_item in enumerate(new_list):
        if i < len(merged):
            if isinstance(merged[i], dict) and isinstance(new_item, dict):
                merged[i] = deep_merge_dicts(merged[i], new_item)
            elif new_item is not None:
                merged[i] = new_item
        else:
            merged.append(new_item)

    return merged


def serialize_as(format: str, data: Any) -> str:
    """
    Serialize the given data as the specified format.

    :param format: The format to serialize as.
    :type format: str
    :param data: The data to serialize.
    :type data: Any
    :returns: The serialized data.
    :rtype: str
    """
    serializer = get_serializer_from_type(format.upper())
    return serializer.dumps(data).decode().rstrip()
