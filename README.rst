|pypi-badge| |nix-ci-badge|

webcam-filters
==============

Add filters (background blur, etc) to your webcam on Linux.

Video conferencing applications tend to either lack video effects altogether or
support only a limited set of capabilities on Linux (e.g. Zoom [#]_, Google Meets [#]_).

Goal here is to provide a virtual webcam via ``v4l2loopback`` with a common
set of filters that can be used everywhere.

.. contents:: :local:


Usage
-----
Passthrough (no-op)::

  $ webcam-filters --input-dev /dev/video0 --output-dev /dev/video3

Blur background::

  $ webcam-filters --input-dev /dev/video0 --output-dev /dev/video3 --background-blur 150

Hardware acceleration (via VAAPI)::

  $ webcam-filters --input-dev /dev/video0 --output-dev /dev/video3 --background-blur 150 --hw-accel-api vaapi

Using docker::

  $ docker run -it \
    --device=/dev/video0:/input-dev \
    --device=/dev/video3:/output-dev \
    ghcr.io/jashandeep-sohi/webcam-filters:master --background-blur 50

Dependencies
------------
Other than the Python dependencies that can be automatically installed by Pip,
there are a few system dependencies that require manual attention.

v4l2loopback
************
`v4l2loopback` kernel module is required to emulate a virtual webcam. See your
distro's docs or v4l2loopback_ on how to install and set it up
(e.g. https://archlinux.org/packages/extra/any/v4l2loopback-dkms/).

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
- gst-python (e.g. https://archlinux.org/packages/extra/x86_64/gst-python/)
- gst-plugins-base (e.g. https://archlinux.org/packages/extra/x86_64/gst-plugins-base/)
- gst-plugins-good (e.g. https://archlinux.org/packages/extra/x86_64/gst-plugins-good/)
- Optional:

  - gstreamer-vaapi for hardware acceleration (e.g.
    https://archlinux.org/packages/extra/x86_64/gstreamer-vaapi/)


Installation
------------

Nix
***
The provided Nix_ package bundles all the necessary GStreamer dependencies and
should "just work" on any distro.

Install a specific release version/tag::

  $ nix --experimental-features 'nix-command flakes' \
      profile
      install
      github:jashandeep-sohi/webcam-filters/vx.x.x

Install a specific branch (e.g. ``master``)::

  $ nix --experimental-features 'nix-command flakes' \
      profile
      install
      github:jashandeep-sohi/webcam-filters/master

Hardware Acceleration
.....................
For VAAPI support with Nix on non-NixOS systems use nixGL_::

  $ nix-env \
      --file https://github.com/guibou/nixGL/archive/main.tar.gz \
      --install \
      --attr auto.nixGLDefault \
      --arg enable32bits false
  $ export LIBVA_DRIVER_NAME=iHD # Or whatever works with your GPU
  $ nixGL webcam-filters --input-dev /dev/video0 --output-dev /dev/video3 --hw-accel-api vaapi

On NixOS follow https://nixos.wiki/wiki/Accelerated_Video_Playback


Pipx/Pip
********
You can also use `pipx` or `pip`. Pipx_ is recommend to keep Python dependencies
isolated. Keep in mind this will not install ``gst-python`` or any of the other
GStreamer dependencies, so you'll have to install that yourself.

Latest stable::

  $ pipx install --system-site-packages webcam-filters
  $ # Or
  $ pip install --user webcam-filters

Latest pre-release::

  $ pipx install --system-site-packages --pip-args='--pre' webcam-filters
  $ # Or
  $ pip install --user --pre webcam-filters

Git::

  $ url="git+https://github.com/jashandeep-sohi/webcam-filters.git"
  $ pipx install --system-site-packages "$url"
  $ # Or
  $ pip install --user "$url"

Docker
******
The docker container wraps a Nix installation for those who prefer to have it dockerized.

You can retag the image locally if you don't want to refer to the long name::

  $ docker tag ghcr.io/jashandeep-sohi/webcam-filters:master webcam-filters

You may also build the image locally::

  $ nix --experimental-features 'nix-command flakes' run .#container.copyToDockerDaemon


.. [#] Zoom desktop client supports background blur as of version 5.7.6. Zoom on web does not.

.. [#] Google Meets supports background blur only on Chrome.

.. _Pipx: https://github.com/pypa/pipx

.. _Nix: https://nixos.org/download.html

.. _nixGL: https://github.com/guibou/nixGL

.. _v4l2loopback: https://github.com/umlaeute/v4l2loopback

.. |pypi-badge| image:: https://img.shields.io/pypi/v/webcam-filters
    :alt: PyPI
    :target: https://pypi.org/project/webcam-filters/

.. |nix-ci-badge| image:: https://github.com/jashandeep-sohi/webcam-filters/actions/workflows/update-nix-cache.yaml/badge.svg
    :alt: Update Nix Cache
    :target: https://github.com/jashandeep-sohi/webcam-filters/actions/workflows/update-nix-cache.yaml
