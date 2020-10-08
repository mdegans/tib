#!/bin/bash
set -e

readonly NANO_URI="https://developer.nvidia.com/embedded/L4T/r32_Release_v4.3/Sources/T210/public_sources.tbz2"
readonly NANO_SHA="a7024135b0b0a5eb93d47b39b7b24a7b9af649274352fe71ce281312b146b3d916d5f0db5520dc7d0d1dc17dddf4c6b5a4352d6a174f12176f6d0009f8e05bda"
readonly NX_URI="https://developer.nvidia.com/embedded/L4T/r32_Release_v4.3/Sources/T186/public_sources.tbz2"
readonly NX_SHA="5e6db0c9e739db07b461b041b58b668d20662e2048029f6fa50bb3963f0319715527e9cc3d76e1b97229a3bc3f46ae082a5725d44172550e25e3db1df2bdcbfb"

function download() {
  case "$1" in
    nano)
      echo "Downloading public sources (kernel etc.) Jetson Nano."
      URI="$NANO_URI"
      SHA="$NANO_SHA"
      ;;
    nx)
      echo "Downloading public sources (kernel etc.) for Jetson NX."
      URI="$NX_URI"
      SHA="$NX_SHA"
      ;;
    *)
      echo "Invalid argument. Acceptable: {nano|nx}" 1>&2
      exit 1
  esac
  # download and calculate the sha at the same time
  SHA_ACTUAL="$(wget --https-only -nv --show-progress --progress=bar:force:noscroll -O- ${URI} | tee public_sources.tbz2 | sha512sum -b | cut -d ' ' -f 1)"
  if [ "$SHA" != "$SHA_ACTUAL" ]; then
    echo "$SHA_ACTUAL does not match expected $SHA for $URI" 1>&2
    exit 1
  fi
  echo "Extracting public sources tarball."
  # --no-same-owner important for this tarball in particular
  tar -I lbzip2 -xf public_sources.tbz2
  echo "Public sources tarball sucessfully extracted."
  rm public_sources.tbz2
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