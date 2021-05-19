#!/bin/bash
set -e

readonly NANO_URI="https://developer.nvidia.com/embedded/L4T/r32_Release_v5.0/sources/T210/public_sources.tbz2"
readonly NANO_SHA="17c209936629f14e06561021e1bbbe5da446ffcab6a40a5c706bb8634902ac79a83c46633591f0ccad4f3cf27f5f2c128546390c7f34b1806501255a69808404"
readonly NX_URI="https://developer.nvidia.com/embedded/L4T/r32_Release_v5.0/sources/T186/public_sources.tbz2"
readonly NX_SHA="c8b2b3c62c7c748c66743d46301510918684261cfc2e5fb4a25ed5617aa403cad78702089b3486eceddfd5f681c45b129f4d4d00efe05f8c8474492c58cc3300"

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

main "$1"