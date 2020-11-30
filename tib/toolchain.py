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

import hashlib
import logging
import os
import platform
import shutil
import tempfile
import urllib.request

from utils import (
    cli_common,
    extract,
    join_and_check,
    run,
)

from typing import (
    Optional,
    Tuple,
)

logger = logging.getLogger(__name__)

__all__ = [
    "get_cross_prefix",
    "install_from_tarball",
]

DEFAULT_PREFIX = "/usr/local"
URL_32 = "https://releases.linaro.org/components/toolchain/binaries/7.3-2018.05/aarch64-linux-gnu/gcc-linaro-7.3.1-2018.05-i686_aarch64-linux-gnu.tar.xz"
MD5_32 = "https://releases.linaro.org/components/toolchain/binaries/7.3-2018.05/aarch64-linux-gnu/gcc-linaro-7.3.1-2018.05-i686_aarch64-linux-gnu.tar.xz.asc"
URL_64 = "https://releases.linaro.org/components/toolchain/binaries/7.3-2018.05/aarch64-linux-gnu/gcc-linaro-7.3.1-2018.05-x86_64_aarch64-linux-gnu.tar.xz"
MD5_64 = "https://releases.linaro.org/components/toolchain/binaries/7.3-2018.05/aarch64-linux-gnu/gcc-linaro-7.3.1-2018.05-x86_64_aarch64-linux-gnu.tar.xz.asc"


def get_url_md5() -> Tuple[str, str]:
    """
    :return: platoform appropriate tarball uri and md5 url.
    """
    if platform.machine() == "i386":
        logger.debug("Detected x86 (32 bit).")
        return (URL_32, MD5_32)
    elif platform.machine() == "x86_64":
        logger.debug("Detected x86_64.")
        return (URL_64, MD5_64)
    raise RuntimeError(
        "Unsupported architecture. Only x86 and x86-64 currently supported."
    )


def get_cross_prefix() -> Optional[str]:
    """:returns: the cross prefix for the toolchain in path"""
    logger.debug(f"Checking for cross compiler...")
    gcc = shutil.which(f"aarch64-linux-gnu-gcc")
    if not gcc:
        return
    logger.debug(f"Found gcc cross compiler at {gcc}")
    cross_prefix = os.path.join(
        os.path.dirname(shutil.which(f"aarch64-linux-gnu-gcc")), f"aarch64-linux-gnu-"
    )
    return cross_prefix


# noinspection PyUnresolvedReferences
def install_from_tarball(prefix: os.PathLike) -> str:
    """
    Installs the cross compiler toolchain to `prefix`

    :returns: the cross prefix

    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     cross_prefix = install_from_tarball(tmp)
    ...     bindir = os.path.dirname(cross_prefix)
    ...     os.path.isfile(os.path.join(bindir, 'aarch64-linux-gnu-gcc'))
    True
    """
    logger.debug(f"Installing toolchain to prefix: {prefix}")

    url, md5 = get_url_md5()

    # get the md5 to verify archive tegrity
    with urllib.request.urlopen(md5) as response:
        logger.debug(f"Fetching checksum from {md5}")
        hexdigest = response.read(32).decode()
        logger.debug(f"Got md5sum: {hexdigest}")

    with tempfile.TemporaryDirectory() as extract_dir:
        logger.info("Downloading and verifying toolchain...")
        member_list = extract(
            url,
            extract_dir,
            hasher=hashlib.md5,
            hexdigest=hexdigest,
        )
        # todo: this is a sloppy assumption that the tarball will always be this
        #  format, fix so it's more flexible for possible future changes.:
        if member_list[0].isdir():
            top_level_folder = member_list[0].name
        else:
            raise RuntimeError("Could not find top level folder in tarball.")

        rsync_source = join_and_check(extract_dir, top_level_folder)

        logger.info(f"Installing toolchain.")
        run(
            ("sudo", "rsync", "-a", "--info=progress2", f"{rsync_source}/", prefix)
        ).check_returncode()

    return os.path.join(prefix, "bin", "aarch64-linux-gnu-")


def main(prefix=None) -> int:
    cross_prefix = install_from_tarball(prefix)
    logger.info(f"CROSS_PREFIX={cross_prefix}")
    return 0


def cli_main() -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="toolchain install script",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    ap.add_argument(
        "--prefix",
        help="install prefix for recommended linaro tarball",
        default=DEFAULT_PREFIX,
    )

    # add --log-file and --verbose
    return main(**cli_common(ap))


if __name__ == "__main__":
    import sys

    sys.exit(cli_main())