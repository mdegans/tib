#!/bin/bash
set -e

# note: rootfs is the same for every board rn but this might not always be so
readonly NANO_URI="https://developer.nvidia.com/embedded/L4T/r32_Release_v4.3/t210ref_release_aarch64/Tegra_Linux_Sample-Root-Filesystem_R32.4.3_aarch64.tbz2"
readonly NANO_SHA="c3542aa1b0cdd38aff10975e48cb4f74649eed6c4cb685c1ba2d84c947f9c7210de5d3c88ae4dbf3b3bdc254fbbc058bbb560298fe1bed2249952ed2580d57cb"
readonly NX_URI="https://developer.nvidia.com/embedded/L4T/r32_Release_v4.3/t186ref_release_aarch64/Tegra_Linux_Sample-Root-Filesystem_R32.4.3_aarch64.tbz2"
readonly NX_SHA="c3542aa1b0cdd38aff10975e48cb4f74649eed6c4cb685c1ba2d84c947f9c7210de5d3c88ae4dbf3b3bdc254fbbc058bbb560298fe1bed2249952ed2580d57cb"

function download() {
  case "$1" in
    nano)
      echo "Downloading rootfs for Jetson Nano."
      URI="$NANO_URI"
      SHA="$NANO_SHA"
      ;;
    nx)
      echo "Downloading rootfs for Jetson NX."
      URI="$NX_URI"
      SHA="$NX_SHA"
      ;;
    *)
      echo "Invalid argument. Acceptable: {nano|nx}" 1>&2
      exit 1
  esac
  # download and calculate the sha at the same time
  SHA_ACTUAL="$(wget --https-only -nv --show-progress --progress=bar:force:noscroll -O- ${URI} | tee rootfs.tbz2 | sha512sum -b | cut -d ' ' -f 1)"
  if [ "$SHA" != "$SHA_ACTUAL" ]; then
    echo "$SHA_ACTUAL does not match expected $SHA for $URI" 1>&2
    exit 1
  fi
  echo "Extracting rootfs tarball."
  sudo tar -I lbzip2 -xpf rootfs.tbz2 -C ~/Linux_for_Tegra/rootfs
  echo "Rootfs tarball sucessfully extracted."
  rm rootfs.tbz2
}

function main() {
  case "$1" in
    nano)
      download nano
      ;;
    nx)
      download nx
      ;;
    *)
      echo $"Usage: $0 {nano|nx}"
      exit 1
  esac
}

main $1