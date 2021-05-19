#!/bin/bash

# This is a sample script to be run with chroot.py (or otherwise in a chroot)
# to remove and install some apt packages from the rootfs (before first boot)

set -e

export DEBIAN_FRONTEND=noninteractive

# update package set
apt-get update

# install packages, cleaning up any no longer needed from above
apt-get install -y --autoremove --no-install-recommends \
  deepstream-5.0

# clean up apt lists
rm -rf /var/lib/apt/lists/*
