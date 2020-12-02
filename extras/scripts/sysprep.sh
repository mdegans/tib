#!/bin/bash

# This is a sample script to be run with chroot.py (or otherwise in a chroot)
# to remove and install some apt packages from the rootfs (before first boot)
# You can use a script like this to prepare a system for first run.

readonly CUDA_VER="10-2"

set -e

# purge useless packages and configuration
apt-get purge -y \
  libreoffice-*

# update packages
apt-get update

# the system can be updated as shown below, however badly written scripts in apt
# packages can fail to install correctly in a chroot. If you get a black screen
# at boot instead of the initial setup, disable the following line.
apt-get dist-upgrade -y

# install packages, cleaning up any no longer needed from above
apt-get install -y --autoremove --no-install-recommends \
  cuda-compiler-$CUDA_VER \
  cuda-libraries-dev-$CUDA_VER \
  nano \
  nvidia-container \
  nvidia-tensorrt \
  python3-dev \
  python3-wheel \
&& rm -rf /var/lib/apt/lists/*
