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

import getpass
import hashlib
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile

from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    MutableMapping,
    Optional,
    Sequence,
    Text,
    TYPE_CHECKING,
    Union,
)

if TYPE_CHECKING:
    from argparse import ArgumentParser
else:
    ArgumentParser = None

__all__ = [
    "chmod",
    "cli_common",
    "copy",
    "download",
    "ensure_sudo",
    "extract",
    "join_and_check",
    "makedirs",
    "move",
    "real_username",
    "remove",
    "rename",
    "run",
    "verify",
    "yes_or_no",
]


logger = logging.getLogger(__name__)


def real_username() -> str:
    """:returns: the real username running the script"""
    return os.environ["SUDO_USER"] if "SUDO_USER" in os.environ else getpass.getuser()


def yes_or_no(input_text) -> bool:
    """prompts for a yes or no choices for |input_text|.
    :returns: true if yes, false if no"""
    choice = ""
    while not choice.startswith(("y", "n")):
        choice = input(f"{input_text} (y/n)").lower()
    return True if choice.startswith("y") else False


def chdir(path):
    """wraps os.chdir() and logs to debug level"""
    logger.debug(f"Working directory: {path}")
    os.chdir(path)


def chmod(path, mode):
    """wraps os.chmod() and logs to debug level"""
    logger.debug(f"setting {path} to mode {str(oct(mode)[2:])}")
    return os.chmod(path, mode)


def makedirs(path, **kwargs):
    """wraps os.makedirs() and logs to debug level"""
    logger.debug(f"Creating {path}.")
    return os.makedirs(path, **kwargs)


def copy(src, dest, **kwargs):
    """wraps shutil.copy() and logs to debug level"""
    logger.debug(f"copying {src} to {dest}")
    return shutil.copy(src, dest, **kwargs)


def remove(path):
    """wraps os.remove() (or os.rmdir) and logs to debug level
    also deletes empty directories"""
    logger.debug(f"removing {path}")
    try:
        os.remove(path)
    except IsADirectoryError:
        try:
            os.rmdir(path)
        except FileNotFoundError as err:
            logger.error(f"{path} not found", err)
        except OSError as err:
            logger.error(f"{path} not empty", err)


def run(*args, **kwargs) -> subprocess.CompletedProcess:
    """wraps subprocess.run but also logs the command"""
    command = tuple(args[0])
    logger.debug(f"Running: {' '.join(command)}")
    return subprocess.run(command, *args[1:], **kwargs)


def backup(path) -> str:
    """renames a path with a backup timestamp"""
    path_backup = f"{path}.backup.{int(time.time())}"
    logger.info(f"Backing up {path} to {path_backup}")
    shutil.move(path, path_backup)
    return path_backup


def move(source, dest):
    """wraps shutil.move() and logs to backup"""
    logger.debug(f"moving {source} to {dest}")
    shutil.move(source, dest)


rename = move


def patch(*patches, at_path=None):
    """
    Apply patch(es) `at_path` using quilt.
    Create a 'patches' folder it it doesn't exist and appends to a series file.

    Args:
        patches (Iterable[str]): the .patch files to apply
        at_path (str): the path root to apply the patches
            defaults to os.getcwd()
    """
    if not at_path:
        at_path = os.getcwd()
    patchdir = os.path.join(at_path, "patches")
    makedirs(patchdir, exist_ok=True)
    series = os.path.join(patchdir, "series")
    with open(series, "a") as series_file:
        for patch in patches:
            basename = os.path.basename(patch)
            logger.debug(f"Adding patch: {basename} to {patchdir}")
            copy(patch, patchdir)
            series_file.write(basename + "\n")
    logger.info("Applying patches.")
    run(("quilt", "push")).check_returncode()


def join_and_check(path, *paths: Iterable[str]) -> str:
    """joins a path with os.path.join and ensures it os.path.exists()"""
    path = os.path.join(path, *paths)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{os.path.join(*paths)} not found in {path}."
        )  # pylint: disable=no-value-for-parameter
    return path


def mount(
    source,
    target,
    type_: Optional[str] = None,
    options: Optional[Iterable[str]] = None,
) -> subprocess.CompletedProcess:
    logger.info(f"Mounting {target}")
    command = ["mount"]
    if type_:
        command.extend(("-t", str(type_)))
    if options:
        command.append("-o")
        command.append(",".join(sorted(options)))
    command.extend((source, target))
    return run(command)


def umount(target) -> subprocess.CompletedProcess:
    """
    unmounts a target path
    :arg target: the target to unmount
    :return: subprocess.CompletedProcess of the unmount command
    """
    logger.info(f"Unmounting: {target}")
    return run(("umount", target))


def ensure_sudo() -> str:
    """ensures user is root and SUDO_USER is in os.environ,
    :returns: the real username (see real_username())
    """
    # if we aren't root, or don't have access to host environment variables...
    username = real_username()
    uid = os.getuid()  # pylint: disable=no-member
    if username == "root":
        # this could happen with sudo su, for example
        raise EnvironmentError("Could not look up SUDO_USER")
    if uid != 0:
        raise PermissionError("this script needs sudo")
    return username


def download(
    url: Text,
    path: str,
    hexdigest: Optional[str] = None,
    hasher: Optional[Callable[[bytes], Any]] = None,
    chunk_size=2 ** 20,
) -> Text:
    """
    Downloads a file at |url| to |path|.
    :arg url: as str, bytes
    :arg path: destination path. str, bytes, os.PathLike will all work
    :param hexdigest: Expected hash from hasher
    :param hasher: hasher to use (eg. "hashlib.md5" hashlib)
    :param chunk_size: chunk size (in bytes) to download in
    :return: destination filename
    """
    # todo: progress reporting
    url_path = urllib.parse.urlparse(url).path
    filename = os.path.basename(url_path)
    local_dest = os.path.join(path, filename)

    # download file in chunks while updating hasher
    logger.debug(f"Downloading {url} to {local_dest}")

    if hasher and hexdigest:
        hasher = hasher()
        logger.debug(f"Using {hasher.name} to verify download.")
        logger.debug(f"Expecting hex digest: {hexdigest}")

    with urllib.request.urlopen(url) as response, open(local_dest, "wb") as f:
        chunk = response.read(chunk_size)
        while chunk:
            f.write(chunk)
            if hasher and hexdigest:
                hasher.update(chunk)
            chunk = response.read(chunk_size)

    # verify hasher result against
    if hasher and hexdigest:
        if hasher.hexdigest() != hexdigest:
            raise RuntimeError(
                f"Hash verification failed for {url}. "
                f"expected: {hexdigest} but got {hasher.hexdigest()}"
            )

    return local_dest


# noinspection PyPep8Naming
def extract(
    file_or_url: str,
    path: str,
    hexdigest: Optional[str] = None,
    hasher: Optional[Callable] = None,
    **kwargs,
) -> Union[List[zipfile.ZipInfo], List[tarfile.TarInfo]]:
    """
    (Downloads) and extracts a file or url to path.
    :param file_or_url: file or url to extract
    :param path: path to extract to
    :param kwargs: passed to download()
    :param hexdigest: Expected hash from hasher
    :param hasher: hasher to use (eg. "hashlib.md5" hashlib)
    :returns: an archive file member list
    """

    if file_or_url.endswith(".zip"):
        ArkFile = zipfile.ZipFile
    elif file_or_url.endswith(("tar.gz", "tar.bz2", "tar.xz", ".tbz2")):
        ArkFile = tarfile.TarFile
    else:
        raise ValueError(f"{file_or_url} has unsupported archive type.")

    with tempfile.TemporaryDirectory() as tmp:
        if file_or_url.startswith(("http", "ftp")):
            file_or_url = download(file_or_url, tmp, hexdigest, hasher, **kwargs)
        elif hasher and hexdigest:
            verify(file_or_url, hexdigest, hasher, **kwargs)

        logger.debug(f"Extracting {file_or_url} to {path}")
        with ArkFile.open(
            file_or_url
        ) as archive:  # pylint: disable=no-value-for-parameter
            member_list = archive.getmembers()
            def is_within_directory(directory, target):
                
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
            
                prefix = os.path.commonprefix([abs_directory, abs_target])
                
                return prefix == abs_directory
            
            def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
            
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
            
                tar.extractall(path, members, numeric_owner=numeric_owner) 
                
            
            safe_extract(archive, path)
            return member_list


# noinspection PyUnresolvedReferences
def verify(
    file: Union[str, os.PathLike], hexdigest: str, hasher: Callable, chunk_size=2 ** 25
):
    """verifies a downloaded file using hashlib"""
    logger.debug(f"Using {hasher.name} to verify archive.")
    logger.debug(f"Expecting hex digest: {hexdigest}")
    with open(file, "rb") as f:
        chunk = f.read(chunk_size)
        while chunk:
            hasher.update(chunk)
            chunk = f.read(chunk_size)
    if hasher.hexdigest() != hexdigest:
        raise RuntimeError(
            f"Hash verification failed for {file}. "
            f"expected: {hexdigest} but got {hasher.hexdigest()}"
        )


def configure_logging(kwargs: MutableMapping) -> MutableMapping:
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
    del kwargs["verbose"], kwargs["log_file"]
    return kwargs


def cli_common(ap: ArgumentParser) -> Dict:
    """
    Appends --verbose and --log-file to an argument parser and returns
    kwargs ready to unpack into a main function.

    :arg ap: the argparse.ArgumentParser to append options to
    """
    ap.add_argument(
        "-l",
        "--log-file",
        help="where to store log file",
        default=os.path.join(
            os.getcwd(),
            "tib.log",
        ),
    )
    ap.add_argument(
        "-v",
        "--verbose",
        help="prints DEBUG log level (logged anyway in " "--log-file)",
        action="store_true",
    )

    # parse the arguments, getting the result back in dict format
    kwargs = vars(ap.parse_args())

    return configure_logging(kwargs)


if __name__ == "__main__":
    import doctest

    doctest.testmod(optionflags=doctest.ELLIPSIS)
