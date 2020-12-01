#!/bin/bash

# fixes the following issue(s)

# * nvidia's `apply_binaries.sh` inconsitently uses `install` and `cp` resulting
# in incorrect permissions for installed .dtb* files in /boot

set -e


# https://unix.stackexchange.com/questions/14345/how-do-i-tell-im-running-in-a-chroot
if [ "$(stat -c %d:%i /)" != "$(stat -c %d:%i /proc/1/root/.)" ]; then
  chown root:root /boot/*.dtb*
  echo "/boot permissions fixed"
else
  echo "This script must be run in a chroot." 1>&2
fi
