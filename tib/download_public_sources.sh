#!/bin/bash
set -e

readonly NANO_URI="https://files.mdegans.dev/l4t-mirror/latest/nano/public_sources.tbz2"
readonly NANO_SHA="99a38dde727321d377b29f7fcfbe3f8f4ed87606e4c53c25182d4dc594345835229111369c881da99e9fc376a706d7a327c8fedb3a3eda314a04bbc02a885bb5"
readonly NX_URI="https://files.mdegans.dev/l4t-mirror/latest/nx/public_sources.tbz2"
readonly NX_SHA="b7999f458f859436732d7ead9df1fc2c918c9753294ea91fcce58aa5d210efd1bcace9fa059f9e8668d36238816dc998cc89fa1a4e61020fe283eb518990703e"

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