#!/usr/bin/python3 -sSE

import os
import subprocess

DTB_MAP = {
    'b00': 'boot/tegra210-p3448-0000-p3449-0000-b00.dtb',
    'a01': 'boot/tegra210-p3448-0000-p3449-0000-a01.dtb',
    'a02': 'boot/tegra210-p3448-0000-p3449-0000-a02.dtb',
}

EXT_PATCH = """--- boot/extlinux/extlinux.conf  2021-03-18 12:27:56.368108662 -0700
+++ boot/extlinux/extlinux.conf  2021-03-18 12:27:56.368108662 -0700
@@ -7,6 +7,7 @@
       MENU LABEL primary kernel
       LINUX /boot/Image
       INITRD /boot/initrd
+      FDT {dtb}
       APPEND ${{cbootargs}} quiet
 
 # When testing a custom kernel, it is recommended that you create a backup of
"""


def patch_extlinux(rootfs_path: str, board_id: str):
    """Patch extlinux.conf with a custom ftd line

    Args:
        dtb_file (str): [description]
    """
    # check we're root
    if os.getuid():
        raise RuntimeError("This script must be run as root.")

    # chekc the dtb argument and paths are valid
    try:
        dtb_filename = DTB_MAP[board_id]
        dtb_fullpath = os.path.join(rootfs_path, dtb_filename)
    except KeyError as e:
        raise RuntimeError(f"Unsupported board id:{board_id}.") from e
    if not os.path.exists(dtb_fullpath):
        raise RuntimeError(f"{dtb_fullpath} does not exist.")
    extlinux_conf = os.path.join(rootfs_path, 'boot/extlinux/extlinux.conf')
    if not os.path.exists(extlinux_conf):
        raise RuntimeError(f"{extlinux_conf} does not exist")

    # patch extlinux.conf
    command = ('patch', '-u', '-p1', '-b', extlinux_conf)
    try:
        subprocess.run(command,
            input=EXT_PATCH.format(dtb=os.path.join(os.pathsep, dtb_filename)),
            universal_newlines=True,
        ).check_returncode()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Could not apply patch.") from e

def cli_main():
    import argparse

    ap = argparse.ArgumentParser(
        description="patch extlinux.conf with built dtb")

    ap.add_argument('rootfs_path', help="rootfs path")
    ap.add_argument('board_id', help="board id", choices=DTB_MAP)

    kwargs = vars(ap.parse_args())

    patch_extlinux(**kwargs)

if __name__ == "__main__":
    cli_main()
