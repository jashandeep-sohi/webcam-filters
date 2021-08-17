import typing as t
import functools

import click
import click_completion

from . import __version__, GST_PLUGIN_PATH


# monkey patch click to support auto completion
click_completion.init()

# monkey patch click option to show defaults by default
click.option = functools.partial(click.option, show_default=True)


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
