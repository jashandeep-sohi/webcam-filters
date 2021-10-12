from fractions import Fraction
from .click import (
    click,
    print_version,
    print_gstreamer_plugin_path,
    install_completion,
    show_completion,
    EnumChoice,
    FlagChoice,
)
from .mediapipe import (
    SelfieSegmentationModel,
)
from .gst import (
  print_device_caps,
  HardwareAccelAPI,
  Pipeline,
  VaapiFeature,
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
    help="Preferred width.",
    type=int,
    default="1280",
)
@click.option(
    "--input-height",
    help="Preferred height.",
    type=int,
    default="720",
)
@click.option(
    "--input-framerate",
    help="Preferred framerate specified in fractional format (e.g. '30/1').",
    type=Fraction,
    default="30/1",
)
@click.option(
    "--input-media-type",
    help="""
    Input media type (e.g. 'image/jpeg' or 'video/x-raw').
    If specified ONLY that type is allowed. Otherwise, everything is allowed.
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
    type=EnumChoice(SelfieSegmentationModel),
    default=SelfieSegmentationModel.general,
)
@click.option(
    "--selfie-segmentation-threshold",
    help="Selfie segmentation threshold.",
    type=click.FloatRange(min=0, max=1),
    default=0.5,
)
@click.option(
    "--hw-accel-api",
    help="Hardware acceleration API to use.",
    type=EnumChoice(HardwareAccelAPI),
    default=HardwareAccelAPI.off,
)
@click.option(
    "--vaapi-features",
    help=f"""
    FLAG := {' | '.join(str(x.name) for x in reversed(VaapiFeature))}

    Comma seperated list of VAAPI features to enable or disable.
    Prepending a "+" enables that feature, while a "-" disables it.
    """,
    type=FlagChoice(VaapiFeature),
    default="+all",
)
@click.option(
    "--verbose",
    help="Enable verbose output.",
    is_flag=True,
    default=False,
    show_default=False,
)
@click.option(
    "--list-dev-caps",
    help="List device capabilities (width, height, framerate, etc) and exit.",
    type=str,
    is_eager=True,
    callback=print_device_caps,
    show_default=False,
    expose_value=False,
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
def cli(**kwargs) -> None:
    """
    Add video filters to your webcam.
    """
    p = Pipeline(**kwargs)

    p.run()
