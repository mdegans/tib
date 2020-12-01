#!/bin/bash

# This is a sample script to be run with chroot.py (or otherwise in a chroot)
# to remove and install some apt packages from the rootfs (before first boot)

set -e

# update package set
apt-get update

# it's possible to do a full apt-get upgrade here if desired, but this can cause
# breakage in some instances

# purge useless packages and configuration
apt-get purge -y \
  libreoffice-*

# install packages, cleaning up any no longer needed from above
apt-get install -y --autoremove --no-install-recommends \
  cuda-compiler-10-2 \
  cuda-libraries-dev-10-2 \
  nano \
  python3-wheel \
&& rm -rf /var/lib/apt/lists/*
