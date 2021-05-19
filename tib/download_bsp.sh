#!/bin/bash
set -e

readonly NANO_URI="https://developer.nvidia.com/embedded/L4T/r32_Release_v5.0/T210/Tegra210_Linux_R32.5.0_aarch64.tbz2"
readonly NANO_SHA="7af7e7373d1dcb48e6eceffb1ffe2d5f816ed8aea25ac32a1530a3d2762d4bd7b3313a4a7a37af24332e7f5bf6f8571fe1376d210c274133a3049312af011326"
readonly NX_URI="https://developer.nvidia.com/embedded/L4T/r32_Release_v5.0/T186/Tegra186_Linux_R32.5.0_aarch64.tbz2"
readonly NX_SHA="ec2073af9b9614bb54f8a3917f033337952a462464768e0eba29ef4fa6acf6dc0c8fc0e5b50968b7320ba278ddda4de6eba371b78dcd207b1a3429e8d4239564"

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

main "$1"