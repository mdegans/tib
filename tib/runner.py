import contextlib
import itertools
import logging
import multiprocessing
import os
import shutil
import subprocess
import sys

import tib

from typing import (
    Iterable,
    Optional,
    Sequence,
    Text,
    Union,
)

Path = Union[Text, os.PathLike]


__all__ = [
    "find_multipass",
    "MultipassRunner",
    "MULTIPASS_URI",
]

logger = logging.getLogger(__name__)

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
MULTIPASS_URI = "https://multipass.run/"


def find_multipass() -> str:
    """
    Find multipass.

    Raises:
        FileNotFoundError
    """
    logger.debug("Looking for multipass")
    multipass = shutil.which("multipass")
    if not multipass:
        raise FileNotFoundError(
            f"Multipass not found. Installation instructions: {MULTIPASS_URI}"
        )
    logger.debug(f"Found multipass: {multipass}")
    return multipass


class MultipassRunner(contextlib.AbstractContextManager):
    """
    Start a VM and run commands in it
    """

    # where scripts are copied to
    scriptdir = "/tmp/scriptdir"

    def __init__(
        self,
        cpus: int = multiprocessing.cpu_count(),
        disk="64G",
        mem="8G",
        name="tib",
        verbose=0,
        image="18.04",
        no_cleanup=False,
    ):
        self._multipass = find_multipass()
        self._cpus = cpus
        self._disk = disk
        self._mem = mem
        self._name = name
        self._verbose = verbose
        self._image = image
        self.no_cleanup = no_cleanup

    def __enter__(self):
        logger.info("Setting up VM.")
        # base command
        command = [
            self._multipass,
            "launch",
            "--cpus",
            self._cpus,
            "--disk",
            self._disk,
            "--mem",
            self._mem,
            "--name",
            self._name,
        ]
        # verbose options
        for _ in range(self._verbose):
            command.append("--verbose")
        # append the final positional argument
        command.append(self._image)
        # convert all arguments to string
        command = [str(e) for e in command]
        try:
            tib.utils.run(command).check_returncode()
        except Exception as e:
            # go directly to exit, to make sure the vm gets deleted
            logger.error(
                "Error starting VM. Check output of multipass command. "
                "Often, the VM may already exist. "
                "Try 'multipass delete --purge tib' "
                "and then try again."
            )
            raise
        logger.info("VM Ready.")
        # return self as the context
        return self

    def __exit__(self, exc_type, exc, exc_tb):
        if not self.no_cleanup:
            logger.info("Cleaning up")
            command = (self._multipass, "delete", "--purge", self._name)
            tib.utils.run(command)
            logger.info("VM Deleted.")
        if exc_type is KeyboardInterrupt:
            logger.info("Cancelled.")
            # suppress error
            return True

    def run(
        self, command: Iterable[str], *args, **kwargs
    ) -> subprocess.CompletedProcess:
        """run a command in the runner"""
        command = list(command)
        program = os.path.basename(command[0])
        logger.debug(f"Running in VM: {' '.join(command)}")
        # the '--' is required to pass arguments
        command = (self._multipass, "exec", self._name, "--", *command)
        return subprocess.run(command, *args, **kwargs)
        # this works, but breaks with ncurses.
        # with subprocess.Popen(command, stdout=subprocess.PIPE, stdin=subprocess.STD_INPUT_HANDLE) as process:
        #     for line in process.stdout:
        #         logger.debug(f'{program}:{line.decode().rstrip()}')
        # return subprocess.CompletedProcess(
        #     process.args, process.returncode, process.stdout, process.stderr)

    def run_script(
        self, script: str, *args, mode="700", **kwargs
    ) -> subprocess.CompletedProcess:
        script = os.path.abspath(script)
        # make sure the workdir exists, and if not create it with mode
        self.run(("mkdir", "-p", "-m", mode, self.scriptdir))
        # calculate the path join (we can't use os.path.join because it would
        # not work on Windows)
        # FIXME(mdegans): use os.path.join on other platforms
        dest = f"{self.scriptdir}/{os.path.basename(script)}"
        self.transfer_to(script, dest)
        # make sure the copied script is executable
        self.run(("chmod", "+x", dest))
        # run the actual script with any arguments
        return self.run((dest, *args), **kwargs)

    def transfer_to(self, *args: Sequence[Path], **kwargs):
        args = list(args)
        sources = args[:-1]
        # prefix dest with the vm name so name:path
        dest = f"{self._name}:{args[-1]}"
        logger.debug(f"copying {sources} to {dest}")
        for source in sources:
            tib.utils.run(
                (self._multipass, "transfer", source, dest)
            ).check_returncode()

    def transfer_from(self, *args: Iterable[Path], **kwargs):
        args = list(args)
        sources = args[:-1]
        # prefix sources with the vm name so name:path
        sources = [f"{self._name}:{p}" for p in sources]
        dest = args[-1]
        command = (self._multipass, "transfer", *sources, dest)
        tib.utils.run(command).check_returncode()

    def mount(self, source: Path, target: Path):
        command = (self._multipass, "mount", source, f"{self._name}:{target}")
        tib.utils.run(command).check_returncode()


if __name__ == "__main__":
    # simple test code

    # since this uses assert, don't run with python optimizations
    # (that disables assert checks)
    logging.basicConfig(level=logging.DEBUG)
    multipass = find_multipass()
    scripts_and_arguments = (
        # echo.sh just runs echo with input arguments
        ("echo.sh", ("one", "two")),
        ("echo.sh", ("un", "deux")),
    )
    with MultipassRunner(multipass) as runner:
        # test run
        runner.run(("echo", "testing simple command"))
        # test run_script (and transfer_to)
        for script, args in scripts_and_arguments:
            script = os.path.join(THIS_DIR, script)
            # test kwargs work
            cp = runner.run_script(script, *args, stdout=subprocess.PIPE)
            # we should be echoed the same args we passed in by the
            assert " ".join(args).encode() in cp.stdout
            cp.check_returncode()
