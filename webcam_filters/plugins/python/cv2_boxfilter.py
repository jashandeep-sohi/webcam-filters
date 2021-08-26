import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")

import cv2
import numpy

from gi.repository import Gst, GstBase, GLib, GObject


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

DEFAULT_KSIZE = 10

class BoxFilter(GstBase.BaseTransform):

    __gstmetadata__ = (
        "OpenCV Boxfilter",
        "Filter",
        "Apply boxfilter",
        "Jashandeep Sohi <jashandeep.s.sohi@gmail.com>"
    )

    __gsttemplates__ = (SRC_PAD_TEMPLATE, SINK_PAD_TEMPLATE)

    __gproperties__ = {
        "ksize": (
            int,
            "ksize",
            "ksize",
            0,
            200,
            DEFAULT_KSIZE,
            GObject.ParamFlags.READWRITE
        ),
    }

    def __init__(self):
        super().__init__()
        self.ksize = DEFAULT_KSIZE
        self.set_qos_enabled(True)

    def do_get_property(self, prop: GObject.GParamSpec):
        if prop.name == "ksize":
            return self.ksize
        else:
            raise AttributeError(f"unkown property {prop.name}")

    def do_set_property(self, prop: GObject.GParamSpec, value):
        if prop.name == "ksize":
            self.ksize  = value
        else:
            raise AttributeError(f"unkown property {prop.name}")


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

                in_nd[:] = cv2.boxFilter(in_nd, -1, (self.ksize, self.ksize))

                return Gst.FlowReturn.OK

        except Gst.MapError as e:
            Gst.error("mapping error %s" % e)
            return Gst.FlowReturn.ERROR
        except Exception as e:
            Gst.error("%s" % e)
            return Gst.FlowReturn.ERROR

GObject.type_register(BoxFilter)

__gstelementfactory__ = (
    "cv2_boxfilter",
    Gst.Rank.NONE,
    BoxFilter
)
