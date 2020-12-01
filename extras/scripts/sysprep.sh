#!/bin/bash

# This is a sample script to be run with chroot.py (or otherwise in a chroot)
# to remove and install some apt packages from the rootfs (before first boot)
# You can use a script like this to prepare a system for first run.

set -e

# purge useless packages and configuration
apt-get purge -y \
  libreoffice-*

# update packages
apt-get update

# the system can be updated as shown below, however badly written scripts in apt
# packages can fail to install correctly in a chroot. If you get a black screen
# at boot instead of the initial setup, disable the following line.
# apt-get dist-upgrade -y --autoremove

# install packages, cleaning up any no longer needed from above
apt-get install -y --autoremove --no-install-recommends \
  cuda-compiler-10-2 \
  cuda-libraries-dev-10-2 \
  nano \
  nvidia-container \
  nvidia-tensorrt \
  python3-wheel \
&& rm -rf /var/lib/apt/lists/*
