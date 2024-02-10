import typer

from flowctl.utils import (
    apply_decorators,
    is_async_callable,
    to_sync,
    catch_exceptions
)


class AsyncTyper(typer.Typer):
    """
    Custom Typer object to facilitate running async commands
    """
    def callback(self, *args, **kwargs):
        decorator = super().callback(*args, **kwargs)

        def wrapper(fn):
            if is_async_callable(fn):
                fn = to_sync(fn)
            return apply_decorators(fn, catch_exceptions(), decorator)
        return wrapper

    def command(self, *args, **kwargs):
        decorator = super().command(*args, **kwargs)

        def wrapper(fn):
            if is_async_callable(fn):
                fn = to_sync(fn)
            return apply_decorators(fn, catch_exceptions(), decorator)
        return wrapper
