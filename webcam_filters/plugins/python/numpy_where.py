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

        self._condition =Gst.Pad.new_from_template(SINK_PAD_TEMPLATE, "condition")
        self._x = Gst.Pad.new_from_template(SINK_PAD_TEMPLATE, "x")
        self._y = Gst.Pad.new_from_template(SINK_PAD_TEMPLATE, "y")

        self.add_pad(self._condition)
        self.add_pad(self._x)
        self.add_pad(self._y)

        self._allocator, self._allocator_params = self.get_allocator()

    def do_negotiated_src_caps(self, caps):
        s = caps.get_structure(0)
        self._width = s.get_int("width").value
        self._height = s.get_int("height").value

        self._resbuf = Gst.Buffer.new_allocate(
            self._allocator,
            self._width * self._height * 3,
            self._allocator_params,
        )

        return True

    def do_fixate_src_caps(self, caps):
        return self._condition.get_current_caps()

    def do_aggregate(self, timeout):
        try:
            cbuf = self._condition.pop_buffer()
            xbuf = self._x.pop_buffer()
            ybuf = self._y.pop_buffer()
            resbuf = self._resbuf

            resbuf.pts = cbuf.pts
            resbuf.dts = cbuf.dts

            self.selected_samples(cbuf.pts, cbuf.dts, cbuf.duration, None)

            cbuf_info = cbuf.map(Gst.MapFlags.READ)
            xbuf_info = xbuf.map(Gst.MapFlags.READ)
            ybuf_info = ybuf.map(Gst.MapFlags.READ)
            resbuf_info = resbuf.map(Gst.MapFlags.WRITE)

            with cbuf_info, xbuf_info, ybuf_info, resbuf_info:
                condition = numpy.ndarray(
                    shape=(self._height, self._width, 3),
                    dtype=numpy.dtype("bool"),
                    buffer=cbuf_info.data
                )
                x = numpy.ndarray(
                    shape=(self._height, self._width, 3),
                    dtype=numpy.uint8,
                    buffer=xbuf_info.data
                )
                y = numpy.ndarray(
                    shape=(self._height, self._width, 3),
                    dtype=numpy.uint8,
                    buffer=ybuf_info.data
                )
                res = numpy.ndarray(
                    shape=(self._height, self._width, 3),
                    dtype=numpy.uint8,
                    buffer=resbuf_info.data
                )

                res[:] = numpy.where(condition, x, y)

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
