#!/bin/bash

set -e

echo "killing blueman with fire"
apt-get purge -y --autoremove blueman
