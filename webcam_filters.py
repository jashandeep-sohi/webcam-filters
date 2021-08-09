import sys
import time

import av
import cv2
import mediapipe
import numpy
import typer

from enum import Enum
from typing import Optional

from mediapipe.python.solutions.selfie_segmentation import SelfieSegmentation

if sys.version_info >= (3, 8):
    from importlib import metadata
else:
    import importlib_metadata as metadata


__version__ = metadata.version(__name__)

cli = typer.Typer()


class SelfieSegmentationModel(str, Enum):
    general = "general"
    landscape = "landscape"


def version_callback(value: bool):
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@cli.command()
def main(
    input_dev: str = typer.Option(
        ..., help="input device (e.g. real webcam at /dev/video0)"
    ),
    input_width: int = typer.Option(
        1280, help="input width"
    ),
    input_height: int = typer.Option(
        720, help="input height"
    ),
    input_fps: float = typer.Option(
        30, help="input FPS"
    ),
    input_format: str = typer.Option(
        "mjpeg", help="input format"
    ),
    output_dev: str = typer.Option(
        ..., help="output device (e.g. v4l2loopback at /dev/video3)"
    ),
    background_blur: int = typer.Option(
        0, help="background blur intensity", min=0, max=200
    ),
    selfie_segmentation_model: SelfieSegmentationModel = typer.Option(
        SelfieSegmentationModel.general, help="model used for selfie segmentation"
    ),
    max_target_latency: int = typer.Option(
        10,  help="maximum latency in nano-seconds to aim for", min=0
    ),
    version: Optional[bool] = typer.Option(
      None, "--version", help="show version", callback=version_callback, is_eager=True
    )
):
    in_con = av.open(
        input_dev,
        mode="r",
        format="video4linux2,v4l2",
        options={
            "video_size": f"{input_width}x{input_height}",
            "framerate": f"{input_fps}",
            "input_format": f"{input_format}",
        }
    )

    out_con = av.open(
        output_dev,
        mode="w",
        format="video4linux2,v4l2",
    )

    in_stream = in_con.streams.video[0]
    out_stream = out_con.add_stream("rawvideo", rate=input_fps)
    out_stream.width = input_width
    out_stream.height = input_height
    out_stream.pix_fmt = "yuv420p"

    model_selection = 0 if selfie_segmentation_model == SelfieSegmentationModel.general else 1
    selfie_seg = SelfieSegmentation(model_selection=model_selection)

    latency = 0
    for in_frame in in_con.decode(in_stream):
        start_time = time.perf_counter_ns()

        if latency > max_target_latency:
            latency = 0
            continue

        in_img = in_frame.to_ndarray(format="rgb24")
        out_img = in_img

        if background_blur > 0:
            in_img.flags.writeable = False
            result = selfie_seg.process(in_img)
            in_img.flags.writeable = True

            condition = numpy.stack((result.segmentation_mask,) * 3, axis=-1) > 0.1
            bg_img = cv2.boxFilter(out_img, -1, (background_blur, background_blur))
            out_img = numpy.where(condition, in_img, bg_img)

        out_frame = av.VideoFrame.from_ndarray(out_img)
        out_con.mux(out_stream.encode(out_frame))

        latency = time.perf_counter_ns() - start_time
