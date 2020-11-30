#!/bin/bash
set -e

readonly NANO_URI="https://developer.nvidia.com/embedded/L4T/r32_Release_v4.3/t210ref_release_aarch64/Tegra210_Linux_R32.4.3_aarch64.tbz2"
readonly NANO_SHA="43c2ef83e438114dbca75a6b56dbace9c83b1c58e67301451868055cdfda24f41d003281dcdbd82253469682a0efcdefd9b6117a8be3fbb1ba20a293c1219604"
readonly NX_URI="https://developer.nvidia.com/embedded/L4T/r32_Release_v4.3/t186ref_release_aarch64/Tegra186_Linux_R32.4.3_aarch64.tbz2"
readonly NX_SHA="00a3fe01958e8c1c3a9dd1af2700fe822c8729bfc5cea0c49c5ea89eeea23603829aa04906deb280d7f81fc552664843452aad84a48f8991307358d6cf337c1d"

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
  rm bsp.tbz2
  # Remove readme (Because OCD. This ends up in offical Tegra images even.)
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