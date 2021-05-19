#!/bin/bash
set -e

# note: rootfs is the same for every board rn but this might not always be so
readonly NANO_URI="https://developer.nvidia.com/embedded/L4T/r32_Release_v5.0/T210/Tegra_Linux_Sample-Root-Filesystem_R32.5.0_aarch64.tbz2"
readonly NANO_SHA="4ea3d06a6f7279fd2551db408aceded529c798ab59d639b511adabd58586f5c94f05194cf028f9a816250c61222f957aaab8dc3d7e9639f8f53811491f907687"
readonly NX_URI="https://developer.nvidia.com/embedded/L4T/r32_Release_v5.0/T186/Tegra_Linux_Sample-Root-Filesystem_R32.5.0_aarch64.tbz2"
readonly NX_SHA="4ea3d06a6f7279fd2551db408aceded529c798ab59d639b511adabd58586f5c94f05194cf028f9a816250c61222f957aaab8dc3d7e9639f8f53811491f907687"

# Hooray, Nvidia put the apt key someplace handy!
readonly KEY_BSP_URI="https://repo.download.nvidia.com/jetson/jetson-ota-public.asc"
readonly KEY_BSP_SHA="580d5fe3c8d956aa0ee02c93093c51ab5f6f64ad28a68472cc32e481be02dbc952ff4a262afd4f21596d8e8e2fd493131a9ee158a70e49d9500039a316c7cb42"
readonly APT_RELEASE="r32.5"

function download() {
  # download and calculate the sha at the same time
  SHA_ACTUAL="$(wget --https-only -nv --show-progress --progress=bar:force:noscroll -O- $1 | tee $3 | sha512sum -b | cut -d ' ' -f 1)"
  if [ "$2" != "$SHA_ACTUAL" ]; then
    echo "$SHA_ACTUAL does not match expected $2 for $1" 1>&2
    exit 1
  fi
}

function setup() {
  case "$1" in
    nano)
      echo "Downloading rootfs for Jetson Nano."
      URI="$NANO_URI"
      SHA="$NANO_SHA"
      SOC="t210"
      ;;
    nx)
      echo "Downloading rootfs for Jetson NX."
      URI="$NX_URI"
      SHA="$NX_SHA"
      SOC="t194"
      ;;
    *)
      echo "Invalid argument. Acceptable: {nano|nx}" 1>&2
      exit 1
  esac
  download $URI $SHA rootfs.tbz2
  echo "Extracting rootfs tarball."
  sudo tar -I lbzip2 -xpf rootfs.tbz2 -C Linux_for_Tegra/rootfs
  echo "Rootfs tarball sucessfully extracted."
  rm rootfs.tbz2
  if [ "$2" == "--install-key" ]; then
    echo "Getting apt key"
    download $KEY_BSP_URI $KEY_BSP_SHA jetson-ota-public.asc
    echo "Installing apt key in rootfs."
    sudo chown root:root jetson-ota-public.asc
    sudo chmod 644 jetson-ota-public.asc 
    sudo mv jetson-ota-public.asc Linux_for_Tegra/rootfs/etc/apt/trusted.gpg.d/
    echo "creating apt list at .../rootfs/etc/apt/sources.list.d/nvidia-l4t-apt-source.list"
    echo "deb https://repo.download.nvidia.com/jetson/common $APT_RELEASE main" \
      | sudo tee Linux_for_Tegra/rootfs/etc/apt/sources.list.d/nvidia-l4t-apt-source.list
    echo "deb https://repo.download.nvidia.com/jetson/${SOC} $APT_RELEASE main" \
      | sudo tee -a Linux_for_Tegra/rootfs/etc/apt/sources.list.d/nvidia-l4t-apt-source.list
  fi
}

function main() {
  case "$1" in
    nano)
      setup nano "$2"
      ;;
    nx)
      setup nx "$2"
      ;;
    *)
      echo $"Usage: $0 {nano|nx} [--install-key]"
      exit 1
  esac
}

main "$1" "$2"