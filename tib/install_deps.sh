#!/bin/bash
set -e

readonly DEBIAN_FRONTEND=noninteractive

function install_deps() {
  sudo apt-get update
  # NOTE: python (2) is needed for jetson-disk-image-creator.sh
  sudo apt-get install -y --no-install-recommends --autoremove \
      binfmt-support \
      build-essential \
      lbzip2 \
      libncurses5-dev \
      python \
      qemu-user-static \
      quilt \
      wget \
    && sudo rm -rf /var/lib/apt/lists
}

install_deps
