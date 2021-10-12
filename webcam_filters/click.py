import typing as t
import functools
import enum

import click
import click_completion
import click_completion.core

from . import __version__, GST_PLUGIN_PATH


# monkey patch click to support auto completion
click_completion.init()

# monkey patch click option to show defaults by default
click.option = functools.partial(click.option, show_default=True)


class EnumChoice(click.Choice):

    def __init__(self, enum_type: t.Type[enum.Enum]) -> None:
        self.enum_type = enum_type
        super().__init__([c.name for c in self.enum_type])

    def convert(
        self,
        value: t.Union[str, enum.Enum],
        param: t.Optional[click.Parameter],
        ctx: t.Optional[click.Context],
    ) -> enum.Enum:
        if isinstance(value, self.enum_type):
            value = value.name

        name = super().convert(value, param, ctx)

        return self.enum_type[name]


def show_completion(
    ctx: click.Context,
    param: click.Parameter,
    value: t.Any,
) -> None:
    """
    Show auto completion and exit.
    """
    if not value or ctx.resilient_parsing:
        return
    click.echo(click_completion.core.get_code())
    ctx.exit()


def install_completion(
    ctx: click.Context,
    param: click.Parameter,
    value: t.Any,
) -> None:
    """
    Install auto completion and exit.
    """
    if not value or ctx.resilient_parsing:
        return
    shell, path = click_completion.core.install()
    click.echo(f"{shell} completion installed at {path}")
    ctx.exit()


def print_version(
    ctx: click.Context,
    param: click.Parameter,
    value: t.Any,
) -> None:
    """
    Show version and quit.
    """
    if not value or ctx.resilient_parsing:
        return
    click.echo(__version__)
    ctx.exit()


def print_gstreamer_plugin_path(
    ctx: click.Context,
    param: click.Parameter,
    value: t.Any,
) -> None:
    """
    Show Gstremaer plugin path and exit.
    """
    if not value or ctx.resilient_parsing:
        return
    click.echo(GST_PLUGIN_PATH)
    ctx.exit()
