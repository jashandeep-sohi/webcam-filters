import gi
import time

gi.require_version("Gst", "1.0")
gi.require_version("GstBase", "1.0")

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

SRC_PAD_TEMPLATE = Gst.PadTemplate.new_with_gtype(
    "src",
    Gst.PadDirection.SRC,
    Gst.PadPresence.ALWAYS,
    SRC_CAPS,
    GstBase.AggregatorPad.__gtype__
)


SINK_PAD_TEMPLATE = Gst.PadTemplate.new_with_gtype(
    "sink",
    Gst.PadDirection.SINK,
    Gst.PadPresence.ALWAYS,
    SINK_CAPS,
    GstBase.AggregatorPad.__gtype__
)


class Where(GstBase.Aggregator):

    __gstmetadata__ = (
        "OpenCV Boxfilter",
        "Filter",
        "Apply boxfilter",
        "Jashandeep Sohi <jashandeep.s.sohi@gmail.com>"
    )

    __gsttemplates__ = (
        SRC_PAD_TEMPLATE,
        SINK_PAD_TEMPLATE,
    )

    def __init__(self):
        super().__init__()
        self.add_pad(Gst.Pad.new_from_template(SINK_PAD_TEMPLATE, "condition"))
        self.add_pad(Gst.Pad.new_from_template(SINK_PAD_TEMPLATE, "x"))
        self.add_pad(Gst.Pad.new_from_template(SINK_PAD_TEMPLATE, "y"))

    def do_negotiated_src_caps(self, caps):
        s = caps.get_structure(0)
        self.width = s.get_int("width").value
        self.height = s.get_int("height").value

        return True

    def do_fixate_src_caps(self, caps):
        return self.get_static_pad("condition").get_current_caps()

    def do_aggregate(self, timeout):
        try:
            cbuf = self.get_static_pad("condition").pop_buffer()
            xbuf = self.get_static_pad("x").pop_buffer()
            ybuf = self.get_static_pad("y").pop_buffer()

            cbuf_info = cbuf.map(Gst.MapFlags.READ)
            xbuf_info = xbuf.map(Gst.MapFlags.READ)
            ybuf_info = ybuf.map(Gst.MapFlags.READ)

            with cbuf_info, xbuf_info, ybuf_info:
                condition = numpy.ndarray(
                    shape=(self.height, self.width, 3),
                    dtype=numpy.dtype("bool"),
                    buffer=cbuf_info.data
                )
                x = numpy.ndarray(
                    shape=(self.height, self.width, 3),
                    dtype=numpy.uint8,
                    buffer=xbuf_info.data
                )
                y = numpy.ndarray(
                    shape=(self.height, self.width, 3),
                    dtype=numpy.uint8,
                    buffer=ybuf_info.data
                )

                res = numpy.where(condition, x, y)

                resbuf = Gst.Buffer.new_wrapped(bytes(res.data))

                resbuf.pts = cbuf.pts
                resbuf.dts = cbuf.dts

                self.finish_buffer(resbuf)

                return Gst.FlowReturn.OK

        except Gst.MapError as e:
            Gst.error("mapping error %s" % e)
            return Gst.FlowReturn.ERROR
        except Exception as e:
            Gst.error("%s" % e)
            return Gst.FlowReturn.ERROR

GObject.type_register(Where)

__gstelementfactory__ = (
    "numpy_where",
    Gst.Rank.NONE,
    Where
)
