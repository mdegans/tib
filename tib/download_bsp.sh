#!/bin/bash
set -e

readonly NANO_URI="https://files.mdegans.dev/l4t-mirror/latest/nano/Tegra210_Linux_R32.4.4_aarch64.tbz2"
readonly NANO_SHA="b7a24bc49b00887864841b237d06368af1244a6b5b3e0415ad7fe5019a233b8a6e991f38d8ef2473438481bd208f7ac16ace415602eca59cd3ab07282d0daf90"
readonly NX_URI="https://files.mdegans.dev/l4t-mirror/latest/nx/Tegra186_Linux_R32.4.4_aarch64.tbz2"
readonly NX_SHA="c1b6a6f57c3a41c8d2edc81ed96c8fbec81fdf41fb50c6eb059d89ed8e1bbcfd35b0645b6b4dd16ccb51f4ef32122b70ce34e643fb7d4520937f99561717a3c5"

function download() {
  case "$1" in
    nano)
      echo "Downloading BSP for Jetson Nano."
      URI="$NANO_URI"
      SHA="$NANO_SHA"
      ;;
    nx)
      echo "Downloading BSP for Jetson NX."
      URI="$NX_URI"
      SHA="$NX_SHA"
      ;;
    *)
      echo "Invalid argument. Acceptable: {nano|nx}" 1>&2
      exit 1
  esac
  # Download and calculate the sha at the same time.
  SHA_ACTUAL="$(wget --https-only -nv --show-progress --progress=bar:force:noscroll -O- ${URI} | tee bsp.tbz2 | sha512sum -b | cut -d ' ' -f 1)"
  if [ "$SHA" != "$SHA_ACTUAL" ]; then
    echo "$SHA_ACTUAL does not match expected $SHA for $URI" 1>&2
    exit 1
  fi
  echo "Extracting BSP tarball."
  tar -I lbzip2 -xf bsp.tbz2
  echo "BSP tarball sucessfully extracted."
  sudo chown root:root Linux_for_Tegra/rootfs/
  echo "Changed owner of rootfs to root:root"
  rm bsp.tbz2
  # Remove readme (Because OCD. This ends up in offical Tegra images even.)
  echo "Removing README.txt from rootfs/"
  sudo rm Linux_for_Tegra/rootfs/README.txt
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