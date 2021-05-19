#!/bin/bash

# A postinst script in the blueman package breaks apt upgrade in a chroot.
# Since bluetooth is half broken on linux anyway, we'll just remove blueman.
# It can be installed after first boot anyway.

set -e

echo "killing blueman with fire"
apt-get purge -y --autoremove blueman
