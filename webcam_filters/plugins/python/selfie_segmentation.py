import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")

import numpy

from gi.repository import Gst, GstBase, GLib, GObject

from mediapipe.python.solutions.selfie_segmentation import SelfieSegmentation


GObject.threads_init()
Gst.init(None)

SRC_CAPS = Gst.Caps(Gst.Structure(
    "video/x-raw",
    format="RGB",
    width=Gst.IntRange(range(1, GLib.MAXINT)),
    height=Gst.IntRange(range(1, GLib.MAXINT)),
    framerate=Gst.FractionRange(
        Gst.Fraction(1, 1),
        Gst.Fraction(GLib.MAXINT, 1)
    )
))

SINK_CAPS = Gst.Caps(Gst.Structure(
    "video/x-raw",
    format="RGB",
    width=Gst.IntRange(range(1, GLib.MAXINT)),
    height=Gst.IntRange(range(1, GLib.MAXINT)),
    framerate=Gst.FractionRange(
        Gst.Fraction(1, 1),
        Gst.Fraction(GLib.MAXINT, 1)
    )
))

SRC_PAD_TEMPLATE = Gst.PadTemplate.new(
    "src",
    Gst.PadDirection.SRC,
    Gst.PadPresence.ALWAYS,
    SRC_CAPS
)

SINK_PAD_TEMPLATE = Gst.PadTemplate.new(
    "sink",
    Gst.PadDirection.SINK,
    Gst.PadPresence.ALWAYS,
    SINK_CAPS
)

DEFAULT_MODEL = 0
DEFAULT_THRESHOLD = 0.5


class SelfieSegmenter(GstBase.BaseTransform):

    __gstmetadata__ = (
        "Selfie Segmenter",
        "Filter",
        "Perform selfie segmentation using mediapipe model",
        "Jashandeep Sohi <jashandeep.s.sohi@gmail.com>"
    )

    __gsttemplates__ = (SRC_PAD_TEMPLATE, SINK_PAD_TEMPLATE)

    __gproperties__ = {
        "model": (
            int,
            "Segmentation model",
            "Segmentation model (0=general, 1=landscape)",
            0,
            1,
            DEFAULT_MODEL,
            GObject.ParamFlags.READWRITE
        ),
        "threshold": (
            float,
            "Segmentation threshold",
            "Segmentation  threshold",
            0.0,
            1.0,
            DEFAULT_THRESHOLD,
            GObject.ParamFlags.READWRITE
        )
    }

    def __init__(self):
        super().__init__()
        self.model = DEFAULT_MODEL
        self.threshold = DEFAULT_THRESHOLD
        self.set_qos_enabled(True)

    def do_get_property(self, prop: GObject.GParamSpec):
        if prop.name == "model":
            return self.model
        elif prop.name == "threshold":
            return self.threshold
        else:
            raise AttributeError(f"unkown property {prop.name}")

    def do_set_property(self, prop: GObject.GParamSpec, value):
        if prop.name == "model":
            self.model  = value
        elif prop.name == "threshold":
            self.threshold  = value
        else:
            raise AttributeError(f"unkown property {prop.name}")

    def do_start(self):
        self.mp_seg = SelfieSegmentation(model_selection=self.model)

        return True

    def do_transform_caps(
        self,
        direction: Gst.PadDirection,
        caps: Gst.Caps,
        filter_: Gst.Caps
    ) -> Gst.Caps:
        """
         Given a pad in this direction and the given caps, what caps are
         allowed on the other pad in this element.
        """
        if direction == Gst.PadDirection.SRC:
            outcaps = SRC_CAPS
        else:
            outcaps = SINK_CAPS

        if filter_:
            outcaps = outcaps.intersect(filter_)

        return outcaps

    def do_fixate_caps(self, direction, caps, othercaps):
        if direction == Gst.PadDirection.SRC:
            return othercaps.fixate()
        else:
            return caps.fixate()

    def do_set_caps(self, incaps, outcaps):
        s = incaps.get_structure(0)
        self.width = s.get_int("width").value
        self.height = s.get_int("height").value

        return True

    def do_transform_ip(self, inbuf):
        try:
            inbuf_info = inbuf.map(Gst.MapFlags.READ | Gst.MapFlags.WRITE)
            with inbuf_info:
                in_nd = numpy.ndarray(
                    shape=(self.height, self.width, 3),
                    dtype=numpy.uint8,
                    buffer=inbuf_info.data
                )

                in_nd.flags.writeable = False
                result = self.mp_seg.process(in_nd)
                in_nd.flags.writeable = True
                self.mp_seg.reset()

                mask = -(result.segmentation_mask >= self.threshold).view("uint8")

                numpy.stack((mask, mask, mask), -1, in_nd)

                return Gst.FlowReturn.OK

        except Gst.MapError as e:
            Gst.error("mapping error %s" % e)
            return Gst.FlowReturn.ERROR
        except Exception as e:
            Gst.error("%s" % e)
            return Gst.FlowReturn.ERROR

GObject.type_register(SelfieSegmenter)

__gstelementfactory__ = (
    "selfie_seg",
    Gst.Rank.NONE,
    SelfieSegmenter
)
