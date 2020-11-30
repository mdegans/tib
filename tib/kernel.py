#!/usr/bin/python3

# Copyright 2019 Michael de Gans
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# NOTE(mdegans): Why Python?

# https://developers.redhat.com/articles/defensive-coding-guide

# "Once a shell script is so complex that advice in this chapter applies, it is
# time to step back and consider the question: Is there a more suitable
# implementation language available?
#
# For example, Python with its subprocess module can be used to write scripts
# which are almost as concise as shell scripts when it comes to invoking
# external programs, and Python offers richer data structures, with less arcane
# syntax and more consistent behavior.

import logging
import os
import shutil
import subprocess
import tempfile

from utils import (
    backup,
    chdir,
    cli_common,
    makedirs,
    move,
    patch,
    run,
)

from toolchain import get_cross_prefix

from typing import (
    Iterable,
)

__all__ = [
    "build",
]

L4T_PATH = os.path.join(os.getcwd(), "Linux_for_Tegra")
KERNEL_TARBALL = os.path.join(L4T_PATH, "source", "public", "kernel_src.tbz2")
DEFAULT_LOCALVERSION = "-tib"
# this should never need to change on Tegra, but if you want to use this code
# elsewhere, it might be useful (tells make which architecture ot target)
ARCH = "arm64"

logger = logging.getLogger(__name__)


# this is following the instructions from:
# https://docs.nvidia.com/jetson/l4t/index.html#page/Tegra%2520Linux%2520Driver%2520Package%2520Development%2520Guide%2Fkernel_custom.html%23
def build(
    l4t_path=L4T_PATH,
    arch=ARCH,
    cross_prefix=get_cross_prefix(),
    load_kconfig=None,
    localversion=None,
    menuconfig=None,
    module_archive=None,
    patches=tuple(),
    public_sources_sha512=None,
    save_kconfig=None,
):

    logger.info("Preparing to build kernel")

    # set some envs
    os.environ["CROSS_COMPILE"] = cross_prefix
    logger.debug(f"CROSS_COMPILE: {cross_prefix}")
    localversion = localversion if localversion else DEFAULT_LOCALVERSION
    os.environ["LOCALVERSION"] = localversion
    logger.debug(f"LOCALVERSION: {localversion}")

    # set up some initial paths
    logger.debug(f"Linux_for_Tegra path: {l4t_path}")
    l4t_kernel_path = os.path.join(L4T_PATH, "kernel")
    logger.debug(f"L4T kernel path: {l4t_kernel_path}")

    # create a temporary folder that self destructs at the end of the context.
    with tempfile.TemporaryDirectory() as tmp:
        chdir(tmp)

        # Building the kernel

        # 0.25 extract kernel sources and cd to the kernel sources
        run(("tar", "-I", "lbzip2", "-xf", KERNEL_TARBALL)).check_returncode()

        # 0.5 apply patches
        for p in patches:
            patch(p)

        # 0.75 cd to kernel source root
        chdir(os.path.join(tmp, "kernel", "kernel-4.9"))

        # 1. set kernel out path
        kernel_out = os.path.join(tmp, "kernel_out")

        # 2.5 set common make arguments
        make_common = (
            f"ARCH={arch}",
            f"O={kernel_out}",
        )

        # 3. Create the initial config
        config(make_common, kernel_out, load_kconfig)
        os.chdir(kernel_out)

        # 3.5 Customize initial configuration interactively (optional)
        if menuconfig:
            make_menuconfig(make_common)

        # 4 Build the kernel and all modules
        make_kernel(make_common)

        # 5 Backup and replace old kernel with new kernel
        replace_kernel(kernel_out, l4t_kernel_path)

        # 6 Replace dtb folder with dts folder
        replace_dtb(kernel_out, l4t_kernel_path)

        # 7 Install kernel modules
        # set up a temporary rootfs folder instead of a real one just to create
        # the kernel_supplements which will be installed by apply_binaries.sh
        rootfs = os.path.join(tmp, "rootfs")
        logger.debug(f"creating temporary rootfs at: {rootfs}")
        makedirs(rootfs, mode=0o755)
        make_modules_install(make_common, rootfs)

        # 8 Archive modules
        archive_modules(rootfs, module_archive, l4t_kernel_path)

        # 8.5 Archive config
        archive_kconfig(kernel_out, save_kconfig)


def config(make_args, kernel_out, load_kconfig=None, kernel_source_path=None):
    logger.info("Configuring kernel")
    os.mkdir(kernel_out, 0o755)
    if load_kconfig:
        logger.info(f"Using supplied config: {load_kconfig}")
        config_filename = os.path.join(kernel_source_path, ".config")
        shutil.copy(load_kconfig, config_filename)
    else:
        # use the default config
        logger.info(f"Using default config (tegra_defconfig).")
        subprocess.run(
            ("make", *make_args, "tegra_defconfig"),
        ).check_returncode()


def make_menuconfig(make_args: Iterable):
    subprocess.run(
        ("make", *make_args, "menuconfig"),
    ).check_returncode()


def make_kernel(make_args: Iterable):
    jobs = os.cpu_count()
    logger.info(f"Building the kernel using all available cores ({jobs}).")
    targets = ("Image", "dtbs", "modules")
    for target in targets:
        logger.info(f"Making target: {target}")
        subprocess.run(("make", *make_args, f"-j{jobs}", target)).check_returncode()


def replace_kernel(kernel_out, l4t_kernel_path):
    logger.info("Replacing old kernel")
    new_kernel = os.path.join(kernel_out, "arch", "arm64", "boot", "Image")
    if not os.path.isfile(new_kernel):
        raise RuntimeError(f"Can't find new kernel at {new_kernel}.")
    old_kernel = os.path.join(l4t_kernel_path, "Image")
    if os.path.exists(old_kernel):
        backup(old_kernel)
    move(new_kernel, old_kernel)


def replace_dtb(kernel_out, l4t_kernel_path):
    logger.info("Replacing old dtb folder.")
    new_dtb = os.path.join(kernel_out, "arch", "arm64", "boot", "dts")
    if not os.path.isdir(new_dtb):
        raise RuntimeError("Can't find new dtb folder.")
    old_dtb = os.path.join(l4t_kernel_path, "dtb")
    if os.path.exists(old_dtb):
        backup(old_dtb)
    move(new_dtb, old_dtb)


def make_modules_install(make_args: Iterable, rootfs):
    logger.info("Installing kernel modules to temporary rootfs.")
    run(
        (
            "make",
            *make_args,
            "modules_install",
            f"INSTALL_MOD_STRIP=1",
            f"INSTALL_MOD_PATH={rootfs}",
        )
    )


def archive_modules(rootfs, module_archive=None, l4t_kernel_path=None):
    if not module_archive:
        if l4t_kernel_path:
            module_archive = os.path.join(l4t_kernel_path, "kernel_supplements.tbz2")
        else:
            raise ValueError("module_archive or l4t_kernel_path required")
    if os.path.isfile(module_archive):
        logger.info("Backing up old kernel supplements")
        backup(module_archive)
    os.chdir(rootfs)
    logger.info(f"Archiving modules as {module_archive}")
    run(
        (
            "tar",
            "--owner",
            "0",
            "--group",
            "0",
            "-I",
            "lbzip2",
            "-cf",
            module_archive,
            "lib/modules",
        ),
    ).check_returncode()


def archive_kconfig(kernel_out_folder, config_out):
    if config_out:
        used_config = os.path.join(kernel_out_folder, ".config")
        if os.path.exists(config_out):
            backup(config_out)
        move(used_config, config_out)


def cli_main():
    import argparse

    ap = argparse.ArgumentParser(
        description="kernel building script",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    ap.add_argument(
        "--l4t_path",
        help="the path to the Linux_for_Tegra folder to operate on",
        default=L4T_PATH,
    )
    ap.add_argument(
        "--cross-prefix",
        help="sets the CROSS_PREFIX variable",
        default=get_cross_prefix(),
    )
    ap.add_argument(
        "--patches",
        default=tuple(),
        nargs="*",
        help="one or more **kernel** patches to apply at kernel_src.tbz2 root",
    )
    ap.add_argument(
        "--localversion",
        help="kernel name suffix",
        default=DEFAULT_LOCALVERSION,
    )
    ap.add_argument("--save-kconfig", help="save kernel config to this file")
    ap.add_argument("--load-kconfig", help="load kernel config from this file")
    ap.add_argument(
        "--menuconfig",
        help="customize kernel config interactively using a menu "
        "(WARNING: here be dragons! While it's unlikely, you could possibly "
        "damage your Tegra or connected devices if the kernel is "
        "mis-configured).",
        action="store_true",
    )

    # add --log-file and --verbose
    build(**cli_common(ap))


if __name__ == "__main__":
    cli_main()