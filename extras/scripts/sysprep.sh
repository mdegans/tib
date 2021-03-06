#!/bin/bash

set -e

# This is a sample script to be run with chroot.py (or otherwise in a chroot)
# to remove and install some apt packages from the rootfs (before first boot)
# You can use a script like this to prepare a system for first run. It:

# * Installs CUDA, creates /usr/local/cuda symlink, and modifes
# `/etc/skel/.profile` to add CUDA_HOME and nvcc to path for all new users

# * Installs TensorRT, nvidia-docker, and some python3 development packages

# * Builds and installs CUDA enhanced OpenCV

# change these if cuda version / apt version changes
readonly CUDA_VER="10.2"
readonly OPENCV_VER="4.5.0"

# these probably shouldn't change
readonly CUDA_HOME_REAL="/usr/local/cuda-${CUDA_VER}"
readonly CUDA_HOME="/usr/local/cuda"
readonly CUDA_VER_APT=${CUDA_VER//[.]/-}
readonly PATH=${CUDA_HOME}/bin:${PATH}

echo "installing apt dependencies"

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
  cuda-compiler-${CUDA_VER_APT} \
  cuda-libraries-dev-${CUDA_VER_APT} \
  nano \
  nvidia-container \
  nvidia-tensorrt \
  python3-dev \
  python3-wheel \
&& rm -rf /var/lib/apt/lists/*

echo "doing cuda post-install setup"
# make /usr/local/cuda link
ln -s $CUDA_HOME_REAL $CUDA_HOME
# patch /etc/skel/.profile
cat >> /etc/skel/.profile <<EOL

# set the cuda home appropriately
export CUDA_HOME=${CUDA_HOME}
# add the cuda bindir so nvcc and other tools are in $PATH
PATH=\${CUDA_HOME}/bin:\${PATH}
EOL

# build and install OpenCV
# this works, but is very slow. Disabling until native cross compilation support
# is added to chroot.py

# cd /tmp
# git clone https://github.com/mdegans/nano_build_opencv.git
# cd nano_build_opencv
# ./build_opencv.sh $OPENCV_VER
# cd ..
# rm -rf nano_build_opencv