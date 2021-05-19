import errno
import logging
import os
import sys

import tib

from typing import (
    Iterable,
    Optional,
    Text,
    Union,
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
PATCH_EXTLINUX_PY = os.path.join(tib.runner.THIS_DIR, "patch_extlinux.py")
IMAGE_OUT = f"{HOME}/sdcard.img"
SOURCE_DIR = f"{L4T_PATH}/source"
KERNEL_PATCH_DIR = "/tmp/kernel_patches"
KERNEL_CONF_DIR = "/tmp/kernel_configs"
EXAMPLES = """Examples:

Building a more or less stock SD card image:
  tib nano (or) tib nx

Building with some custom kernel patches and enable them in an interactive menu:
  tib nano --patches camera.patch pwm.patch --menuconfig

Customize the kernel using menuconfig:
  tib nano --menuconfig
"""

# TODO(mdegans): refactor this
def main(
    scripts: Iterable[Path],
    chroot_scripts: Iterable[Path],
    kernel_patches: Iterable[Path],
    enter_chroot: bool,
    menuconfig: bool,
    save_kconfig: Optional[str],
    load_kconfig: Optional[str],
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
    # quickly check scripts and other input files exist (fail fast)
    # this could move to an argparse action
    scripts = tuple(scripts)
    if chroot_scripts:
        chroot_scripts = tuple(chroot_scripts)
    else:
        chroot_scripts = tuple()
    kernel_patches = tuple(kernel_patches)
    for script in (*scripts, *chroot_scripts, *kernel_patches):
        # https://stackoverflow.com/questions/36077266/how-do-i-raise-a-filenotfounderror-properly
        if not os.path.isfile(script):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), script)
    if load_kconfig:
        if not os.path.isfile(load_kconfig):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), script)
    # prepend our scripts
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
            (board, "--install-key" if kernel_patches or menuconfig else "--no-key"),
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
        # build a new kernel if necessary
        if kernel_patches or menuconfig:
            args = []
            # make patch dir and copy patches to Linux_for_Tegra/source/patches
            if kernel_patches:
                # create patch dir
                runner.run(("mkdir", "-m", "700", KERNEL_PATCH_DIR)).check_returncode()
                inner_patches = []  # VM paths to patches
                # copy all patches and append them to args
                for patch in kernel_patches:
                    dest = f"{KERNEL_PATCH_DIR}/{os.path.basename(patch)}"
                    runner.transfer_to(patch, dest)
                    inner_patches.append(dest)
                args.extend(("--patches", *inner_patches))
            if verbose:
                args.append("--verbose")
            if load_kconfig or save_kconfig:
                # create kernel config dir
                runner.run(("mkdir", "-m", "700", KERNEL_CONF_DIR)).check_returncode()
            if load_kconfig:
                # transfer the kernel config to the VM and add the flags
                dest = f"{KERNEL_CONF_DIR}/kconfig_in"
                runner.transfer_to(load_kconfig, dest)
                args.extend(("--load-kconfig", dest))
            if save_kconfig:
                # add the flags to store the kconfig, we'll transfer it back
                # after the kernel is done building (not just configuring, so
                # if a config is saved, it must at least be a good config)
                kernel_config_out = f"{KERNEL_CONF_DIR}/kconfig_out"
                args.extend(("--save-kconfig", kernel_config_out))
            if menuconfig:
                args.append("--menuconfig")
            logger.info("Building Linux kernel.")
            runner.run_script(KERNEL_PY, *args).check_returncode()
            if save_kconfig:
                # we have a config that sucessfully built a kernel. Transfer it.
                runner.transfer_from(kernel_config_out, save_kconfig)
        # apply nvidia software to the rootfs
        command = ["sudo", APPLY_BINARIES]
        if kernel_patches or menuconfig:
            # apply binaries in target overlay mode, so the kernel and kernel
            # modules we built get installed.
            command.append("--target-overlay")
        logger.info("Applying binaries to rootfs.")
        runner.run(command).check_returncode()
        # we need to patch extlinux.conf with the dtb if we've patched kernel
        # TODO(mdegans): nx support
        if kernel_patches and board == 'nano':
            logger.info("patching extlinux.conf")
            runner.run_script(PATCH_EXTLINUX_PY, ROOTFS_PATH, revision,
                sudo=True,
            ).check_returncode()
        # if needed, copy the chroot script to the filesystem
        if chroot_scripts:
            # TODO(mdegans): move to runner?
            for script in chroot_scripts:
                dest_script = f"{runner.scriptdir}/{os.path.basename(script)}"
                runner.transfer_to(script, dest_script)
                runner.run(("chmod", "+x", dest_script))
                runner.run_script(
                    CHROOT_PY, ROOTFS_PATH, "--script", dest_script
                ).check_returncode()
        # if we've built a new kernel, patch extlinux.conf to use the dtb
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
        "--kernel-patches",
        default=tuple(),
        nargs="+",
        help="one or more **kernel** patches to apply at kernel_src.tbz2 root",
    )

    # TODO(mdegans)
    # ap.add_argument(
    #     "--rootfs-patches",
    #     default=tuple(),
    #     nargs="+",
    #     help="one or more **rootfs** patches to apply relative to /"
    # )

    ap.add_argument(
        "--menuconfig",
        help="customize kernel config interactively using a menu "
        "(WARNING: here be dragons! While it's unlikely, you could possibly "
        "damage your Tegra or connected devices if the kernel is "
        "mis-configured).",
        action="store_true",
    )

    ap.add_argument(
        "--save-kconfig",
        help="filename to save kernel config to (save your menuconfig choices)",
    )

    ap.add_argument(
        "--load-kconfig",
        help="filename to load kernel config from (load menuconfig choices)",
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