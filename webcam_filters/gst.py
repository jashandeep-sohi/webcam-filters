import typing as t
import os
import sys
import enum
import dataclasses

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

    def __str__(self):
      return self.name


class VaapiFeature(enum.Flag):
    jpegdec = enum.auto()
    mpeg2dec = enum.auto()
    h264dec = enum.auto()
    h265dec = enum.auto()
    vc1dec = enum.auto()
    vp8dec = enum.auto()
    vp9dec = enum.auto()

    rgbconvert = enum.auto()
    sinkconvert = enum.auto()

    decode = jpegdec | mpeg2dec | h264dec | h265dec | vc1dec | vp8dec | vp9dec

    all = decode | rgbconvert | sinkconvert


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


@dataclasses.dataclass()
class Pipeline:
    input_dev: str
    output_dev: str
    input_width: int
    input_height: int
    input_framerate: Fraction
    input_media_type: t.Optional[str]
    background_blur: t.Optional[int]
    selfie_segmentation_model: SelfieSegmentationModel
    selfie_segmentation_threshold: int
    hw_accel_api: HardwareAccelAPI
    verbose: bool
    vaapi_features: VaapiFeature

    def run(self):
        init()

        self.enable_hwdec_elements()

        pipeline = self.build_pipeline()

        loop = GObject.MainLoop()

        if self.verbose:
            pipeline.add_property_deep_notify_watch(None, True)

        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_bus_message, loop, pipeline)

        pipeline.set_state(Gst.State.PLAYING)
        try:
            loop.run()
        except KeyboardInterrupt:
            loop.quit()

        pipeline.set_state(Gst.State.NULL)

    def select_input(self) -> Gst.Caps:
        """
        Return Caps for input device that's closest to the desired values.
        """
        dev = self.input_dev
        media_type = self.input_media_type
        width = self.input_width
        height = self.input_height
        framerate = self.input_framerate

        caps = query_device_caps(dev)

        if caps is None:
            click.echo(f"unable to determine capabilities for device {dev!r}")
            raise click.Abort()

        structs = []
        for s in caps:
            if media_type is not None and media_type != s.get_name():
                continue

            s.fixate_field_nearest_int("width", width)
            s.fixate_field_nearest_int("height", height)
            s.fixate_field_nearest_fraction(
                "framerate",
                framerate.numerator,
                framerate.denominator
            )
            structs.append(s)

        if not structs:
            click.echo("unable to find a suitable input format")
            raise click.Abort()

        def struct_sort_key(x):
            _, xwidth = x.get_int("width")
            _, xheight = x.get_int("height")
            _, fr_numerator, fr_denomantor = x.get_fraction("framerate")
            return (
                abs(width - xwidth),
                abs(height - xheight),
                abs(framerate - Fraction(fr_numerator, fr_denomantor or 1))
            )

        structs = sorted(structs, key=struct_sort_key)

        s = structs[0]
        new_caps = Gst.Caps.new_empty()
        new_caps.append_structure(s)

        return new_caps

    def build_pipeline(self) -> Gst.Pipeline:
        input_caps = self.select_input()
        click.echo(f"Selected input: {input_caps}")

        pipeline = Gst.Pipeline.new()

        src = Gst.ElementFactory.make("v4l2src")
        inputfilter = Gst.ElementFactory.make("capsfilter")
        decodebin = Gst.ElementFactory.make("decodebin3")

        if (
            self.hw_accel_api == HardwareAccelAPI.vaapi and
            VaapiFeature.rgbconvert in self.vaapi_features
        ):
            # vaapipostproc doesn't seem to support going directly to RGB on some
            # hardware. So prefer direct RGB conversion if possible, otherwise
            # fallback to some variant of RGBA and then use videoconvert to
            # to get to RGB.
            c= ";".join(f"video/x-raw, format={f}" for f in reversed(RGB_FORMATS))
            rgbconvert = Gst.parse_bin_from_description(
                f"vaapipostproc ! {c} ! videoconvert",
                True
            )
        else:
            rgbconvert = Gst.ElementFactory.make("videoconvert")

        rgbfilter = Gst.ElementFactory.make("capsfilter")
        tee = Gst.ElementFactory.make("tee")

        if (
            self.hw_accel_api == HardwareAccelAPI.vaapi and
            VaapiFeature.sinkconvert in self.vaapi_features
        ):
            c = ";".join(f"video/x-raw, format={f}" for f in RGB_FORMATS)
            sinkconvert = Gst.parse_bin_from_description(
                f"videoconvert ! {c} ! vaapipostproc",
                True
            )
        else:
            sinkconvert = Gst.ElementFactory.make("videoconvert")

        sinkfilter = Gst.ElementFactory.make("capsfilter")
        sink = Gst.ElementFactory.make("v4l2sink")

        src.set_property("device", self.input_dev)
        inputfilter.set_property("caps", input_caps)
        rgbfilter.set_property(
            "caps",
            Gst.Caps.from_string("video/x-raw, format=RGB")
        )
        sinkfilter.set_property(
            "caps",
            Gst.Caps.from_string(f"video/x-raw, format=YUY2")
        )
        sink.set_property("device", self.output_dev)
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

        need_selfie = self.background_blur or False

        if need_selfie:
            selfie_queue = Gst.ElementFactory.make("queue", "selfie_queue")
            selfie = Gst.ElementFactory.make("selfie_seg")
            selfie.set_property("model", self.selfie_segmentation_model)
            selfie.set_property("threshold", self.selfie_segmentation_threshold)
            pipeline.add(selfie_queue, selfie)
            tee.link(selfie_queue)
            selfie_queue.link(selfie)

        if self.background_blur:
            blured_queue = Gst.ElementFactory.make("queue", "blured_queue")
            blured = Gst.ElementFactory.make("cv2_boxfilter")
            blured.set_property("ksize", self.background_blur)
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

        return pipeline


    def enable_hwdec_elements(self) -> None:
        if self.hw_accel_api == HardwareAccelAPI.off:
            return

        reg = Gst.Registry.get()

        if self.hw_accel_api == HardwareAccelAPI.vaapi:
            decoders = [
                x.name for x in VaapiFeature
                if (
                  x != VaapiFeature.decode and
                  x in VaapiFeature.decode and
                  x in self.vaapi_features
                )
            ]

            for d in decoders:
                factory = Gst.ElementFactory.find(f"vaapi{d}")

                if factory is None:
                    click.secho(
                        f"failed to find and enable element 'vaapi{d}'",
                        fg="red"
                    )
                    continue

                factory.set_rank(Gst.Rank.PRIMARY + 1)

                reg.add_feature(factory)

    def on_bus_message(
        self,
        bus: Gst.Bus,
        message: Gst.Message,
        loop: GObject.MainLoop,
        pipeline: Gst.Pipeline,
    ) -> bool:
        mtype = message.type
        src = message.src
        src_path = src.get_path_string()

        if self.verbose:
            click.echo(f"\nsrc: {src_path}")
            click.echo(f"type: {mtype}")

        if mtype == Gst.MessageType.EOS:
            loop.quit()

        elif mtype == Gst.MessageType.ERROR:
            gerror, debug = message.parse_error()
            click.echo(f"Error from {src_path}: {gerror.message}")
            if self.verbose:
                click.echo(f"Debug: {debug}")

            loop.quit()

        elif mtype == Gst.MessageType.WARNING:
            gerror, debug = message.parse_warning()
            click.echo(f"Warning from {src_path}: {gerror.message}")
            if self.verbose:
                click.echo(f"Debug: {debug}")

        elif mtype == Gst.MessageType.INFO:
            gerror, debug = message.parse_info()
            click.echo(f"Info from {src_path}: {gerror.message}")
            if self.verbose:
                click.echo(f"Debug: {debug}")

        elif mtype == Gst.MessageType.PROPERTY_NOTIFY and self.verbose:
            obj, name, value = message.parse_property_notify()

            click.echo(f"{name}: {value}")

        elif mtype == Gst.MessageType.STATE_CHANGED and src == pipeline:
            old, new, pending = message.parse_state_changed()

            click.echo("Pipeline: ", nl=False)
            if new == Gst.State.PAUSED:
                click.echo("PAUSED")
            elif new == Gst.State.READY:
                click.echo("READY")
            elif new == Gst.State.PLAYING:
                click.echo("RUNNING")
            elif new == Gst.State.NULL:
                click.echo("NULL")

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
