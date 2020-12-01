#!/bin/bash

# This is a sample script to be run with chroot.py (or otherwise in a chroot)
# to remove and install some apt packages from the rootfs (before first boot)
# You can use a script like this to prepare a system for first run.

set -e

# purge useless packages and configuration
apt-get purge -y --autoremove \
  libreoffice-*

# update packages
apt-get update
apt-get dist-upgrade -y --autoremove

# install packages, cleaning up any no longer needed from above
apt-get install -y --autoremove --no-install-recommends \
  cuda-compiler-10-2 \
  cuda-libraries-dev-10-2 \
  nano \
  python3-wheel \
&& rm -rf /var/lib/apt/lists/*
