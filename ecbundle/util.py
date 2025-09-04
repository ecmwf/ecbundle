# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

from __future__ import print_function

import time
from subprocess import CalledProcessError, check_call, check_output

from .logging import debug, error, info

__all__ = ["cpu_count", "execute", "fullpath", "Timer"]


try:
    from subprocess import DEVNULL  # py3k
except ImportError:
    import os

    DEVNULL = open(os.devnull, "wb")


def execute(command, **kwargs):
    """
    Execute a given command in a given directory.

    :param command: String or list of strings with the command to execute
    :param cwd: Directory in which to execute command
    :param capture_output: Return output of command as a string
    :param silent: Suppresses output to stdout and stderr
    :param dryrun: Does not actually run command but log it
    """
    cwd = kwargs.pop("cwd", None)
    capture_output = kwargs.pop("capture_output", False)
    silent = kwargs.pop("silent", False)
    dryrun = kwargs.pop("dryrun", False)

    # Some string mangling to support lists and strings
    if isinstance(command, list):
        command = " ".join(command)
    if isinstance(command, str):
        command = command.split(" ")

    # Log the command we're about to execute
    log = debug if silent else info
    if cwd is not None:
        log("+ cd " + cwd)
    log("+ " + " ".join(command))

    try:
        if not dryrun:
            # Silence the command output to stdout/stderr
            if silent:
                kwargs["stderr"] = DEVNULL
                # Don't silence regular output if output is returned
                if not capture_output:
                    kwargs["stdout"] = DEVNULL

            if capture_output:
                kwargs["universal_newlines"] = True
                return check_output(command, cwd=cwd, **kwargs)
            else:
                check_call(command, cwd=cwd, **kwargs)
        else:
            # Return an empty string if a string is expected
            if capture_output:
                return ""
    except CalledProcessError as e:
        cmd_str = " ".join(command)
        dir_str = (" in directory %s" % cwd) if cwd is not None else ""
        if not silent:
            error("ERROR: Command %s failed %s" % (cmd_str, dir_str))
        raise e


def fullpath(path):
    if path:
        import os

        return os.path.abspath(os.path.expanduser(path))
    else:
        return path


def mkdir_p(path):
    import errno
    import os

    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise RuntimeError()


def symlink_force(target, link_name):
    import errno
    import os

    # prefer relative symlink rather than absolute
    # check first if target is absolute or relative
    target_orig = target
    if os.path.isabs(target):
        target = os.path.relpath(target, os.path.dirname(link_name))

    try:
        os.symlink(target, link_name)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST:
            os.remove(link_name)
            os.symlink(target, link_name)
        else:
            raise exc

    # If a relative link is invalid, retry with absolute path if available
    if not os.path.exists(link_name):
        if target != target_orig:
            os.remove(link_name)
            os.symlink(target_orig, link_name)

def copydir(src_dir, target_dir):
    import os
    from subprocess import CalledProcessError, check_call

    if os.path.isdir(target_dir):
        import shutil

        shutil.rmtree(target_dir)

    command = ["cp", "-r", src_dir, target_dir]
    try:
        check_call(command, cwd=os.getcwd(), stdout=DEVNULL, stderr=DEVNULL)
        return True
    except CalledProcessError:
        return False
    command = ["cp", "-r", src_dir, target_dir]
    try:
        check_call(command, cwd=os.getcwd(), stdout=DEVNULL, stderr=DEVNULL)
        return True
    except CalledProcessError:
        return False


class Timer:
    def __init__(self):
        self.start = time.time()

    def restart(self):
        self.start = time.time()

    def elapsed_str(self):
        end = time.time()
        m, s = divmod(end - self.start, 60)
        h, m = divmod(m, 60)
        time_str = "%02d:%02d:%02d" % (h, m, s)
        return time_str


def cpu_count():
    import multiprocessing
    import os

    threads_per_task = multiprocessing.cpu_count()
    tasks_per_node = 1
    hyperthreads = 1

    if "SLURM_JOB_ID" in os.environ:
        slurm_job_id = os.environ["SLURM_JOB_ID"]

        if "SLURM_TASKS_PER_NODE" in os.environ:
            # Value is given as part of the environment, including a multiplier `(xN)` with number of nodes `N` for
            # multi-node jobs
            tasks_per_node = os.environ["SLURM_TASKS_PER_NODE"]
            if "(" in tasks_per_node:
                tasks_per_node = tasks_per_node[: tasks_per_node.index("(")]
            tasks_per_node = int(tasks_per_node)

        else:
            try:
                ntpernode = int(
                    execute(
                        f"squeue -j {slurm_job_id} -O ntpernode -h",
                        capture_output=True,
                        silent=True,
                    )
                )
            except CalledProcessError:
                # Silently ignore if call to squeue fails
                ntpernode = 0

            if ntpernode > 0:
                # This reports `0` if not specified --ntasks-per-node explicitly.
                # Luckily, in such cases, the ENV information is typically up-to-date with sane defaults and we
                # should not even end up here.
                tasks_per_node = ntpernode

        if "SLURM_CPUS_PER_TASK" in os.environ:
            # This is only available if it has been specified explicitly at submission
            threads_per_task = int(os.environ["SLURM_CPUS_PER_TASK"])
        else:
            try:
                threads_per_task = int(
                    execute(
                        f"squeue -j {slurm_job_id} -O cpus-per-task -h",
                        capture_output=True,
                        silent=True,
                    )
                )
            except CalledProcessError:
                # Silently ignore if call to squeue fails
                threads_per_task = 1

    if "EC_threads_per_task" in os.environ.keys():
        threads_per_task = int(os.environ["EC_threads_per_task"])

    if "EC_tasks_per_node" in os.environ.keys():
        tasks_per_node = int(os.environ["EC_tasks_per_node"])

    if "EC_hyperthreads" in os.environ.keys():
        hyperthreads = int(os.environ["EC_hyperthreads"])

    return threads_per_task * tasks_per_node * hyperthreads
