#!/bin/bash
set -x

webcam-filters --input-dev /dev/input_video --output-dev /dev/output_video --background-blur $background_blur