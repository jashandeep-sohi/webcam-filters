import typing as t

from .click import (
    click,
    print_version,
    print_gstreamer_plugin_path,
    install_completion,
    show_completion,
)
from .mediapipe import (
    SelfieSegmentationModel,
)
from .gst import (
  add_filters,
  print_device_caps,
)


@click.command()
@click.option(
    "--input-dev",
    help="Input device (e.g. real webcam at /dev/video0).",
    type=str,
    required=True,
)
@click.option(
    "--input-width",
    help="Input width.",
    type=int,
    default=None,
)
@click.option(
    "--input-height",
    help="Input height.",
    type=int,
    default=None,
)
@click.option(
    "--input-framerate",
    help="Input framerate specified in fractional format (e.g. '30/1').",
    type=str,
    default=None,
)
@click.option(
    "--input-media-type",
    help="""
    Input media type (e.g. 'image/jpeg' or 'x-raw-video').
    Use --list-dev-caps to see all available formats.
    """,
    type=str,
    default=None,
)
@click.option(
    "--output-dev",
    help="Output device (e.g. virtual webcam at /dev/video3).",
    type=str,
    required=True,
)
@click.option(
    "--background-blur",
    help="Background blur intensity.",
    type=click.IntRange(0, 200),
    default=None,
)
@click.option(
    "--selfie-segmentation-model",
    help="Mediapipe model used for selfie segmentation",
    type=click.Choice([x.name for x in SelfieSegmentationModel]),
    default=SelfieSegmentationModel.general.name,
)
@click.option(
    "--selfie-segmentation-threshold",
    help="Selfie segmentation threshold.",
    type=click.FloatRange(min=0, max=1),
    default=0.5,
)
@click.option(
    "--list-dev-caps",
    help="List device capabilities (width, height, framerate, etc) and exit.",
    type=str,
    is_eager=True,
    callback=print_device_caps,
    show_default=False,
)
@click.option(
    "--gst-plugin-path",
    help="Show Gstreamer plugin path and exit.",
    is_flag=True,
    is_eager=True,
    callback=print_gstreamer_plugin_path,
    expose_value=False,
    show_default=False,
)
@click.option(
    "--install-completion",
    help="Install auto completion for the current shell and exit.",
    is_flag=True,
    is_eager=True,
    callback=install_completion,
    expose_value=False,
    show_default=False,
)
@click.option(
    "--show-completion",
    help="Show auto completion for the current shell and exit.",
    is_flag=True,
    is_eager=True,
    callback=show_completion,
    expose_value=False,
    show_default=False,
)
@click.option(
    "--version",
    help="Show version and exit.",
    is_flag=True,
    is_eager=True,
    callback=print_version,
    expose_value=False,
    show_default=False,
)
def cli(
    input_dev: str,
    input_width: t.Optional[int],
    input_height: t.Optional[int],
    input_framerate: t.Optional[str],
    input_media_type: t.Optional[str],
    output_dev: str,
    background_blur: t.Optional[int],
    selfie_segmentation_model: str,
    selfie_segmentation_threshold: int,
    **kwargs
) -> None:
    """
    Add video filters to your webcam.
    """
    selfie_seg_model = SelfieSegmentationModel[selfie_segmentation_model]
    add_filters(
        input_dev,
        output_dev,
        input_width,
        input_height,
        input_framerate,
        input_media_type,
        background_blur,
        selfie_seg_model,
        selfie_segmentation_threshold,
    )
