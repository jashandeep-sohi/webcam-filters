import typing as t
import logging
import os
import sys

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")

from fractions import Fraction
from pathlib import Path

from gi.repository import Gst, GObject, GstBase
from rich.console import Console
from rich.table import Table

from .mediapipe import (
    SelfieSegmentationModel,
)
from .click import (
    click,
)

from . import GST_PLUGIN_PATH


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# hack to let Gst.ElementFactory.make("...") to find custom plugins
os.environ["GST_PLUGIN_PATH"] = ":".join(
    [GST_PLUGIN_PATH] + os.environ.get("GST_PLUGIN_PATH", "").split(":")
)

# hack to ensure interperter path is on PATH so that custom plugins will use the correct interpeter
os.environ["PATH"] = ":".join(
    [str(Path(sys.executable).parent)] + os.environ.get("PATH", "").split(":")
)

GObject.threads_init()
Gst.init(None)


def add_filters(
    input_dev: str,
    output_dev: str,
    input_width: t.Optional[int],
    input_height: t.Optional[int],
    input_framerate: t.Optional[str],
    input_media_type: t.Optional[str],
    background_blur: t.Optional[int],
    selfie_segmentation_model: SelfieSegmentationModel,
    selfie_segmentation_threshold: int,
) -> None:
    """
    Run filters pipeline.
    """
    src = Gst.ElementFactory.make("v4l2src")
    src.set_property("device", input_dev)
    src.set_state(Gst.State.READY)
    caps = src.get_static_pad("src").query_caps(None)

    src.set_state(Gst.State.NULL)

    structs = []
    for c in caps:
        keep = True

        if input_media_type is not None and input_media_type != c.get_name():
            keep = False

        if input_width is not None and input_width != c.get_value("width"):
            keep = False

        if input_height is not None and input_height != c.get_value("height"):
            keep = False

        if input_framerate is not None:
            if input_framerate != str(c.get_value("framerate")):
                keep = False

        if keep:
            structs.append(c)

    structs = sorted(
        structs,
        key=lambda x: (
            Fraction(str(x.get_value("framerate"))),
            x.get_value("width"),
            x.get_value("height"),
        ),
        reverse=True
    )
    new_caps = Gst.Caps.new_empty()
    for s in structs:
        new_caps.append_structure(s)

    pipeline = Gst.Pipeline.new()

    inputfilter = Gst.ElementFactory.make("capsfilter")
    decodebin = Gst.ElementFactory.make("decodebin")
    rgbconvert = Gst.ElementFactory.make("videoconvert")
    rgbfilter = Gst.ElementFactory.make("capsfilter")
    tee = Gst.ElementFactory.make("tee")
    sinkconvert = Gst.ElementFactory.make("videoconvert")
    sinkfilter = Gst.ElementFactory.make("capsfilter")
    sink = Gst.ElementFactory.make("v4l2sink")

    inputfilter.set_property("caps", new_caps)
    rgbfilter.set_property(
        "caps",
        Gst.Caps.from_string("video/x-raw, format=RGB")
    )
    sinkfilter.set_property(
        "caps",
        Gst.Caps.from_string(f"video/x-raw, format=YUY2")
    )
    sink.set_property("device", output_dev)
    sink.set_property("throttle-time", 10)
    sink.set_property("qos", True)

    pipeline.add(
        src,
        inputfilter,
        decodebin,
        rgbconvert,
        rgbfilter,
        tee,
        sinkconvert,
        sinkfilter,
        sink,
    )

    src.link(inputfilter)
    inputfilter.link(decodebin)
    decodebin.connect(
        "pad-added",
        lambda dbin, pad: pad.link(rgbconvert.get_static_pad("sink"))
    )
    rgbconvert.link(rgbfilter)
    rgbfilter.link(tee)

    out = tee

    need_selfie = background_blur or False

    if need_selfie:
        selfie_queue = Gst.ElementFactory.make("queue", "selfie_queue")
        selfie = Gst.ElementFactory.make("selfie_seg")
        selfie.set_property("model", selfie_segmentation_model)
        selfie.set_property("threshold", selfie_segmentation_threshold)
        pipeline.add(selfie_queue, selfie)
        tee.link(selfie_queue)
        selfie_queue.link(selfie)

    if background_blur:
        blured_queue = Gst.ElementFactory.make("queue", "blured_queue")
        blured = Gst.ElementFactory.make("cv2_boxfilter")
        blured.set_property("ksize", background_blur)
        pipeline.add(blured_queue, blured)
        tee.link(blured_queue)
        blured_queue.link(blured)

        where = Gst.ElementFactory.make("numpy_where")
        pipeline.add(where)
        selfie.get_static_pad("src").link(where.get_static_pad("condition"))
        tee.request_pad(tee.get_pad_template("src_%u"), None, None).link(
            where.get_static_pad("x")
        )
        blured.get_static_pad("src").link(where.get_static_pad("y"))

        out = where

    out.link(sinkconvert)
    sinkconvert.link(sinkfilter)
    sinkfilter.link(sink)


    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", on_bus_message, loop)

    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except KeyboardInterrupt:
        loop.quit()

    pipeline.set_state(Gst.State.NULL)


def on_bus_message(
    bus: Gst.Bus,
    message: Gst.Message,
    loop: GObject.MainLoop
) -> bool:
    mtype = message.type

    if mtype == Gst.MessageType.EOS:
        loop.quit()
    elif mtype == Gst.MessageType.ERROR:
        logger.error("%s: %s", *message.parse_error())
        loop.quit()
    elif mtype == Gst.MessageType.WARNING:
        logger.warning("%s: %s", *message.parse_warning())
    elif mtype == Gst.MessageType.INFO:
        logger.info("%s: %s", *message.parse_info())

    return True


def print_device_caps(
    ctx: click.Context,
    param: click.Parameter,
    value: str,
) -> None:
    """
    Print device capabilities and exit.
    """
    if not value or ctx.resilient_parsing:
        return

    src = Gst.ElementFactory.make("v4l2src")
    src.set_property("device", value)

    src.set_state(Gst.State.READY)
    res = src.get_state(1000)
    pad = src.get_static_pad("src")

    if res.state != Gst.State.READY or pad is None:
        click.echo(f"unable to determine capabilities for device {value!r}")
        ctx.exit(1)

    caps = pad.query_caps(None)
    src.set_state(Gst.State.NULL)

    if caps.is_any():
        click.echo(f"unable to determine capabilities for device {value!r}")
        ctx.exit(1)

    table = Table(title=f"{value!r} Capabilites")

    table.add_column("Media Type")
    table.add_column("Width")
    table.add_column("Height")
    table.add_column("Framerate")

    for c in caps:
        table.add_row(
            c.get_name(),
            str(c.get_value("width")),
            str(c.get_value("height")),
            str(c.get_value("framerate")),
        )

    console = Console()
    console.print(table)

    ctx.exit(0)
