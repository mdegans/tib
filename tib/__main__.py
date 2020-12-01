import logging
import os
import sys
import tib

from typing import (
    Iterable,
    Text,
    Tuple,
    Union,
    Sequence,
)

Path = Union[Text, os.PathLike]

__all__ = [
    "main",
    "cli_main",
]

logger = logging.getLogger(tib.__name__)

# Nvidia's disk image creation script
HOME = "/home/ubuntu"
L4T_PATH = f"{HOME}/Linux_for_Tegra"
IMAGE_SCRIPT = f"{L4T_PATH}/tools/jetson-disk-image-creator.sh"
APPLY_BINARIES = f"{L4T_PATH}/apply_binaries.sh"
ROOTFS_PATH = f"{L4T_PATH}/rootfs"
KERNEL_PY = os.path.join(tib.runner.THIS_DIR, "kernel.py")
CHROOT_PY = os.path.join(tib.runner.THIS_DIR, "chroot.py")
IMAGE_OUT = f"{HOME}/sdcard.img"
SOURCE_DIR = f"{L4T_PATH}/source"
KERNEL_PATCH_DIR = f"/tmp/kernel_patches"
EXAMPLES = """Examples:

Building a more or less stock SD card image:
  tib nano (or) tib nx

Building with some custom kernel patches and enable them in an interactive menu:
  tib nano --patches camera.patch pwm.patch --menuconfig

Customize the kernel using menuconfig:
  tib nano --menuconfig
"""


def main(
    scripts: Iterable[Path],
    chroot_scripts: Iterable[Path],
    patches: Iterable[Path],
    enter_chroot: bool,
    menuconfig: bool,
    mem: int,
    verbose: int,
    out: str,
    no_cleanup: bool,
    board: str,
    revision: str,
):
    """
    Create a flashable Tegra SD Card image.
    """
    scripts = (
        # dependencies script (build-essential, etc...)
        (
            os.path.join(tib.runner.THIS_DIR, "install_deps.sh"),
            tuple(),
        ),
        # the utils script (just runs doctests)
        # this is needed by some other scripts.
        (
            os.path.join(tib.runner.THIS_DIR, "utils.py"),
            tuple(),
        ),
        # the BSP script
        (
            os.path.join(tib.runner.THIS_DIR, "download_bsp.sh"),
            (board,),
        ),
        # the rootfs script
        (
            os.path.join(tib.runner.THIS_DIR, "download_rootfs.sh"),
            (board, "--install-key" if patches or menuconfig else "--no-key"),
        ),
        # the kernel download script
        (
            os.path.join(tib.runner.THIS_DIR, "download_public_sources.sh"),
            (board,),
        ),
        # the toolchain download/install script
        (
            os.path.join(tib.runner.THIS_DIR, "toolchain.py"),
            ("--verbose",) if verbose else tuple(),
        ),
        # user supplied scripts
        *((os.path.abspath(s), tuple()) for s in scripts),
    )
    # TODO(mdegans): add more runners, such as WLS2
    runner_cls = tib.runner.MultipassRunner
    with runner_cls(verbose=verbose, no_cleanup=no_cleanup, mem=mem) as runner:
        # run most scripts, including user scripts
        for script, args in scripts:
            runner.run_script(script, *args).check_returncode()
        # make patch dir and copy patches to Linux_for_Tegra/source/patches
        runner.run(("mkdir", "-m", "700", KERNEL_PATCH_DIR)).check_returncode()
        # build a new kernel if necessary
        if patches or menuconfig:
            args = []
            if patches:
                inner_patches = []  # VM path to patches
                for patch in patches:
                    dest = f"{KERNEL_PATCH_DIR}/{os.path.basename(patch)}"
                    runner.transfer_to(patch, dest)
                    inner_patches.append(dest)
                args.extend(("--patches", *inner_patches))
            if verbose:
                args.append("--verbose")
            if menuconfig:
                args.append("--menuconfig")
            logger.info("Building Linux kernel.")
            runner.run_script(KERNEL_PY, *args).check_returncode()
        # apply binaries in target overlay mode, so the kernel  and kernel
        # modules we built get installed.
        command = ["sudo", APPLY_BINARIES]
        if patches or menuconfig:
            # this is needed in case of a custom kernel
            command.append("--target-overlay")
        logger.info("Applying binaries to rootfs.")
        runner.run(command).check_returncode()
        # if needed, copy the chroot script to the filesystem
        if chroot_scripts:
            for script in chroot_scripts:
                dest_script = f"{runner.scriptdir}/{os.path.basename(script)}"
                runner.transfer_to(script, dest_script)
                runner.run_script(
                    CHROOT_PY, ROOTFS_PATH, "--script", dest_script
                ).check_returncode()
        if enter_chroot:
            runner.run_script(CHROOT_PY, ROOTFS_PATH, "--enter")
        # assemble the command to run the image building script.
        command = [
            "sudo",
            IMAGE_SCRIPT,
            "-o",
            IMAGE_OUT,
            "-b",
            "jetson-nano" if board == "nano" else "jetson-xavier-nx-devkit",
        ]
        # the nano needs special treatment
        if board == "nano":
            sku_map = {
                "a01": "100",
                "a02": "200",
                "b00": "300",
            }
            command.extend(("-r", sku_map[revision]))
        logger.info("Assembling SD Card Image.")
        runner.run(command).check_returncode()
        logger.info(f"Transferring {IMAGE_OUT} in VM to {out} on host")
        runner.transfer_from(IMAGE_OUT, out)

    return 0


def cli_main():
    """
    Command line entrypoint
    """
    import argparse

    class Formatter(
        argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter
    ):
        pass

    ap = argparse.ArgumentParser(
        description="Create a custom, flashable, Tegra SD Card image",
        formatter_class=Formatter,
        epilog=EXAMPLES,
    )

    ap.add_argument(
        "board",
        default="nano",
        choices=("nano", "nx"),
        help="board to build an image for",
    )

    ap.add_argument(
        "-v",
        "--verbose",
        default=0,
        type=int,
        choices=range(0, 3),
        help="logging level",
    )

    ap.add_argument(
        "-l",
        "--log-file",
        default=os.path.join(os.getcwd(), "tib.log"),
        help="where to store log file",
    )

    ap.add_argument(
        "--no-cleanup",
        action="store_true",
        help="do not delete VM when done",
    )

    ap.add_argument(
        "-m",
        "--mem",
        default="8G",
        help="memory use cap for VM",
    )

    ap.add_argument(
        "-r",
        "--revision",
        choices=("a01", "a02", "b00"),
        default="b00",
        help="jetson nano revision",
    )

    ap.add_argument("-o", "--out", default="sdcard.img", help="sdcard image filename")

    ap.add_argument(
        "--scripts",
        default=tuple(),
        nargs="+",
        help="script(s) to copy and run inside the VM",
    )

    ap.add_argument(
        "--enter-chroot",
        action="store_true",
        help="enter a chroot to edit the rootfs interactively",
    )

    ap.add_argument(
        "--chroot-scripts",
        nargs="+",
        help="script(s) to run inside the rootfs (as aarch64)",
    )

    ap.add_argument(
        "--patches",
        default=tuple(),
        nargs="+",
        help="one or more **kernel** patches to apply at kernel_src.tbz2 root",
    )

    ap.add_argument(
        "--menuconfig",
        help="customize kernel config interactively using a menu "
        "(WARNING: here be dragons! While it's unlikely, you could possibly "
        "damage your Tegra or connected devices if the kernel is "
        "mis-configured).",
        action="store_true",
    )

    kwargs = vars(ap.parse_args())

    # configure logging
    fh = logging.FileHandler(kwargs["log_file"])
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter("%(asctime)s::%(levelname)s::%(name)s::%(message)s")
    )
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter())
    ch.setLevel(logging.DEBUG if kwargs["verbose"] else logging.INFO)
    # noinspection PyArgumentList
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=(fh, ch),
    )

    del kwargs["log_file"]

    return main(**kwargs)


if __name__ == "__main__":
    sys.exit(cli_main())