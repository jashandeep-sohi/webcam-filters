|pypi-badge|

webcam-filters
==============

Add filters (background blur, etc) to your webcam on Linux.

Video conferencing applications tend to either lack video effects altogether or
support only a limited set of capabilities on Linux (e.g. Zoom, Google Meets).

Goal here is to provide a virtual webcam via ``v4l2loopback`` with a common
set of filters that can be used everywhere.

Usage
-----
Passthrough (no-op)::

  $ webcam-filters --input-dev /dev/video0 --output-dev /dev/video3

Blur background::

  $ webcam-filters --input-dev /dev/video0 --output-dev /dev/video3 --background-blur 150

Dependencies
------------
Other than the Python dependencies that can be automatically installed by Pip,
there are a few system dependencies that require manual attention.

v4l2loopback
************
`v4l2loopback` kernel module is required to emulate a virtual webcam. See your
distro's docs or v4l2loopback_ on how to install and set it up
(e.g. https://archlinux.org/packages/community/any/v4l2loopback-dkms/).

You'll probably want to create at least one loopback device (that's persistent
on boot)::

  $ sudo tee /etc/modprobe.d/v4l2loopback.conf << "EOF"
  # /dev/video3
  options v4l2loopback video_nr=3
  options v4l2loopback card_label="Virtual Webcam"
  options v4l2loopback exclusive_caps=1
  EOF
  $ sudo modprobe v4l2loopback
  $ v4l2-ctl --device /dev/video3 --info

Gstreamer
*********

- gstreamer-1.0 (e.g. https://archlinux.org/packages/extra/x86_64/gstreamer/)
- gst-plugins-base (e.g. https://archlinux.org/packages/extra/x86_64/gst-plugins-base/)
- gst-python (e.g. https://archlinux.org/packages/extra/x86_64/gst-python/)
- gst-plugins-good (e.g. https://archlinux.org/packages/extra/x86_64/gst-plugins-good/)


Installation
------------
You can either use `pipx` or `pip`. Pipx_ is recommend to keep dependencies
isolated.

Latest stable::

  $ pipx install --system-site-packages webcam-filters
  $ pip install --user webcam-filters

Latest pre-release::

  $ pipx install --system-site-packages --pip-args='--pre' webcam-filters
  $ pip install --user --pre webcam-filters

Git::

  $ url="git+https://github.com/jashandeep-sohi/webcam-filters.git"
  $ pipx install --system-site-packages "$url"
  $ pip install --user "$url"


.. _Pipx: https://github.com/pypa/pipx

.. _v4l2loopback_: https://github.com/umlaeute/v4l2loopback

.. |pypi-badge| image:: https://img.shields.io/pypi/v/webcam-filters
    :alt: PyPI
    :target: https://pypi.org/project/webcam-filters/
