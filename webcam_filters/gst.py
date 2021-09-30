import typing as t
import logging
import os
import sys
import enum

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


RGB_FORMATS = [
    "RGB",

    "RGBx",
    "xRGB",

    "RGBA",
    "ARGB",

    "BGR",

    "BGRx",
    "xBGR",

    "BGRA",
    "ABGR",
]


class HardwareAccelAPI(enum.Enum):
    off = enum.auto()
    vaapi = enum.auto()


def init():
    # hack to let Gst.ElementFactory.make("...") to find custom plugins
    os.environ["GST_PLUGIN_PATH"] = ":".join(
        [GST_PLUGIN_PATH] + os.environ.get("GST_PLUGIN_PATH", "").split(":")
    )

    # hack to ensure interperter path is on PATH so that custom plugins will use the correct interpeter
    os.environ["PATH"] = ":".join(
        [str(Path(sys.executable).parent)] + os.environ.get("PATH", "").split(":")
    )

    # TODO: Find out why this is needed. On some systems (e.g. nixos) forking
    # will cause Python plugins not to be loaded properly. No real harm in
    # disabling it AFAIK.
    os.environ["GST_REGISTRY_FORK"] = "no"

    GObject.threads_init()
    if not Gst.init_check(None):
        raise RuntimeError("failed to initialize gstreamer")


def add_filters(
    input_dev: str,
    output_dev: str,
    input_width: int,
    input_height: int,
    input_framerate: Fraction,
    input_media_type: t.Optional[str],
    background_blur: t.Optional[int],
    selfie_segmentation_model: SelfieSegmentationModel,
    selfie_segmentation_threshold: int,
    hw_accel_api: HardwareAccelAPI,
) -> None:
    """
    Run filters pipeline.
    """
    init()

    caps = query_device_caps(input_dev)

    if caps is None:
        click.echo(f"unable to determine capabilities for device {input_dev!r}")
        raise click.Abort()

    structs = []
    for s in caps:
        if input_media_type is not None and input_media_type != s.get_name():
            continue

        s.fixate_field_nearest_int("width", input_width)
        s.fixate_field_nearest_int("height", input_height)
        s.fixate_field_nearest_fraction(
            "framerate",
            input_framerate.numerator,
            input_framerate.denominator
        )
        structs.append(s)

    if not structs:
        click.echo("unable to find a suitable input format")
        raise click.Abort()

    def struct_sort_key(x):
        _, width = x.get_int("width")
        _, height = x.get_int("height")
        _, fr_numerator, fr_denomantor = x.get_fraction("framerate")
        return (
            abs(input_width - width),
            abs(input_height - height),
            abs(input_framerate - Fraction(fr_numerator, fr_denomantor or 1))
        )

    structs = sorted(structs, key=struct_sort_key)

    s = structs[0]
    new_caps = Gst.Caps.new_empty()
    new_caps.append_structure(s)

    click.echo(
        f"Selected input: media-type={s.get_name()}, width={s.get_value('width')} "
        f"height={s.get_value('height')} framerate={s.get_value('framerate')}"
    )

    enable_hwdec_plugins(hw_accel_api)

    pipeline = Gst.Pipeline.new()

    src = Gst.ElementFactory.make("v4l2src")
    inputfilter = Gst.ElementFactory.make("capsfilter")
    decodebin = Gst.ElementFactory.make("decodebin3")

    if hw_accel_api == HardwareAccelAPI.vaapi:
        # vaapipostproc doesn't seem to support going directly to RGB on some
        # hardware. So prefer direct RGB conversion if possible, otherwise
        # fallback to some variant of RGBA and then use videoconvert to
        # to get to RGB.
        c= ";".join(f"video/x-raw, format={f}" for f in reversed(RGB_FORMATS))
        rgbconvert = Gst.parse_bin_from_description(
            f"capsfilter caps=video/x-raw(memory:VASurface) ! "
            f"vaapipostproc ! {c} ! videoconvert",
            True
        )
    else:
        rgbconvert = Gst.ElementFactory.make("videoconvert")

    rgbfilter = Gst.ElementFactory.make("capsfilter")
    tee = Gst.ElementFactory.make("tee")

    if hw_accel_api == HardwareAccelAPI.vaapi:
        c = ";".join(f"video/x-raw, format={f}" for f in RGB_FORMATS)
        sinkconvert = Gst.parse_bin_from_description(
            f"videoconvert ! {c} ! vaapipostproc",
            True
        )
    else:
        sinkconvert = Gst.ElementFactory.make("videoconvert")

    sinkfilter = Gst.ElementFactory.make("capsfilter")
    sink = Gst.ElementFactory.make("v4l2sink")

    src.set_property("device", input_dev)
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


def query_device_caps(dev: str) -> t.Optional[Gst.Caps]:
    src = Gst.ElementFactory.make("v4l2src")
    src.set_property("device", dev)

    src.set_state(Gst.State.READY)
    res = src.get_state(1000)
    pad = src.get_static_pad("src")

    if res.state != Gst.State.READY or pad is None:
        return None

    caps = pad.query_caps(None)
    src.set_state(Gst.State.NULL)

    if caps.is_any():
        return None

    return caps


def print_device_caps(
    ctx: click.Context,
    param: click.Parameter,
    value: str,
) -> None:
    """
    Print device capabilities and exit.
    """
    init()

    if not value or ctx.resilient_parsing:
        return

    caps = query_device_caps(value)

    if caps is None:
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


def enable_hwdec_plugins(api: HardwareAccelAPI) -> None:
    if api == HardwareAccelAPI.off:
        return

    reg = Gst.Registry.get()

    if api == HardwareAccelAPI.vaapi:
        plugins = [
            "vaapijpegdec",
            "vaapimpeg2dec",
            "vaapih264dec",
            "vaapih265dec",
            "vaapivc1dec",
        ]

        for p in plugins:
            factory = Gst.ElementFactory.find(p)

            if factory is None:
                continue

            factory.set_rank(Gst.Rank.PRIMARY + 1)

            reg.add_feature(factory)
