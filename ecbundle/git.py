# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

from subprocess import CalledProcessError

from .logging import debug, error, warning
from .util import execute

__all__ = ["Git"]


class Git(object):
    """
    Utility wrapper for commonly used git commands

    Note, all methods are classmethod, so no instantiation is required.
    """

    @classmethod
    def clone(cls, repo_url, src_dir, rev, origin, dryrun, shallow=False):
        retry = False

        if shallow:
            command = [
                "git",
                "-c",
                "advice.detachedHead=false",
                "clone",
                "-o",
                origin,
                "-b",
                rev,
                repo_url,
                src_dir,
                "--depth=1",
            ]
            try:
                execute(command, dryrun=dryrun, silent=True)
                return
            except CalledProcessError:
                warning(
                    "WARNING: Command %s failed for shallow clone.\n"
                    "         Retrying with non-shallow clone" % (" ".join(command),)
                )
                retry = True

        if not shallow or retry:
            try:
                command = ["git", "clone", "-o", origin, repo_url, src_dir]
                execute(command, dryrun=dryrun)

                cls.fetch(src_dir, origin, rev, dryrun)

                command = ["git", "-c", "advice.detachedHead=false", "checkout", rev]
                execute(command, cwd=src_dir, dryrun=dryrun)
            except CalledProcessError:
                raise RuntimeError()

    @classmethod
    def remote_ref_type(cls, src_dir, remote, ref, dryrun):
        command = ["git", "ls-remote", remote, ref]
        try:
            if not dryrun:
                result = execute(command, cwd=src_dir, capture_output=True).split()
                if len(result) > 0:
                    if result[1].startswith("refs/heads/"):
                        return "branch"
                    if result[1].startswith("refs/tags/"):
                        return "tag"
                    if result[1].startswith("refs/pull/"):
                        return "pullrequest"
                return None
            return "branch"
        except CalledProcessError:
            return False

    @classmethod
    def fetch(cls, src_dir, remote, rev, dryrun):
        import os

        shallow = os.path.isfile(src_dir + "/.git/shallow")
        reftype = cls.remote_ref_type(src_dir, remote, rev, dryrun)
        if not reftype:
            shallow = False

        commands = []
        if shallow:
            if reftype == "branch":
                refmap = "+refs/heads/" + rev + ":refs/remotes/" + remote + "/" + rev
                commands.append(
                    ["git", "fetch", "--depth=1", "--update-shallow", remote, refmap]
                )
                # Following are necessary for a shallow clone to track the remote branch
                commands.append(
                    ["git", "config", "--add", "remote." + remote + ".fetch", refmap]
                )
                commands.append(
                    ["git", "config", "--add", "branch." + rev + ".remote", remote]
                )
                commands.append(
                    [
                        "git",
                        "config",
                        "--add",
                        "branch." + rev + ".merge",
                        "refs/heads/" + rev,
                    ]
                )
            elif reftype == "pullrequest":
                refmap = "+refs/" + rev + ":refs/remotes/" + remote + "/" + rev
                commands.append(
                    ["git", "fetch", "--depth=1", "--update-shallow", remote, refmap]
                )
            elif reftype == "tag":
                commands.append(
                    [
                        "git",
                        "fetch",
                        "--depth=1",
                        "--update-shallow",
                        remote,
                        "tag",
                        rev,
                    ]
                )
            else:
                error("ERROR: unknown reftype")
                raise RuntimeError()
        else:
            commands.append(["git", "fetch", "--tags", remote])
            commands.append(
                ["git", "fetch", "--quiet", remote, "+refs/pull/*:refs/pull/*"]
            )

        for command in commands:
            try:
                execute(command, cwd=src_dir, dryrun=dryrun)
            except CalledProcessError:
                raise RuntimeError()

    @classmethod
    def merge(cls, src_dir, origin, branch, dryrun):
        command = ["git", "merge", origin, branch]
        try:
            execute(command, cwd=src_dir, dryrun=dryrun)
        except CalledProcessError:
            raise RuntimeError()

    @classmethod
    def reset_hard(cls, src_dir, origin, branch, dryrun):
        command = ["git", "reset", "--hard", "/".join([origin, branch])]
        try:
            execute(command, cwd=src_dir, dryrun=dryrun)
        except CalledProcessError:
            raise RuntimeError()

    @classmethod
    def pull(cls, src_dir, origin, branch, dryrun):
        command = ["git", "pull", origin, branch]
        try:
            execute(command, cwd=src_dir, dryrun=dryrun)
        except CalledProcessError:
            raise RuntimeError()

    @classmethod
    def is_tag(cls, src_dir, tag, dryrun):
        command = ["git", "rev-parse", "--verify", tag + "^{tag}"]
        try:
            execute(command, cwd=src_dir, silent=True, dryrun=dryrun)
            return True
        except CalledProcessError:
            return False

    @classmethod
    def is_branch(cls, src_dir, branch, dryrun):
        command = ["git", "show-ref", "--verify", "refs/heads/" + branch]
        try:
            execute(command, cwd=src_dir, silent=True, dryrun=dryrun)
            return True
        except CalledProcessError:
            return False

    @classmethod
    def is_commit(cls, src_dir, tag, dryrun):
        command = ["git", "rev-parse", "--verify", tag + "^{commit}"]
        try:
            execute(command, cwd=src_dir, silent=True, dryrun=dryrun)
            return True
        except CalledProcessError:
            return False

    @classmethod
    def branch_upstream(cls, src_dir, branch, dryrun):
        command = [
            "git",
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            branch + "@{upstream}",
        ]
        try:
            return execute(
                command, cwd=src_dir, silent=True, capture_output=True
            ).strip()
        except CalledProcessError:
            return None

    @classmethod
    def checkout(cls, src_dir, rev, dryrun):
        command = ["git", "-c", "advice.detachedHead=false", "checkout", rev]
        try:
            execute(command, cwd=src_dir, dryrun=dryrun)
        except CalledProcessError:
            raise RuntimeError()

    @classmethod
    def checkout_new(cls, src_dir, remote, rev, dryrun):
        if cls.is_tag(src_dir, rev, dryrun):
            debug(rev + " is tag")
            return cls.checkout(src_dir, rev, dryrun)

        if cls.is_commit(src_dir, rev, dryrun):
            debug(rev + " is commit")
            return cls.checkout(src_dir, rev, dryrun)

        command = ["git", "checkout", "-b", rev, "/".join([remote, rev])]
        try:
            execute(command, cwd=src_dir, dryrun=dryrun)
        except CalledProcessError:
            raise RuntimeError()

    @classmethod
    def submodule_init(cls, src_dir, dryrun):
        command = ["git", "submodule", "update", "--init", "--recursive"]
        try:
            execute(command, cwd=src_dir, dryrun=dryrun)
        except CalledProcessError:
            raise RuntimeError()

    @classmethod
    def branch(cls, src_dir, dryrun):
        command = ["git", "symbolic-ref", "--short", "HEAD"]

        try:
            if not dryrun:
                return execute(
                    command, cwd=src_dir, silent=True, capture_output=True
                ).strip()
        except CalledProcessError:
            return None

    @staticmethod
    def remotes(src_dir):
        command = ["git", "remote", "-v"]
        try:
            remotes = execute(command, cwd=src_dir, silent=True, capture_output=True).strip().split('\n')
            remotes = [l.split() for l in remotes]
            return {l[0]:l[1] for l in remotes if l[2] == '(fetch)'}
        except CalledProcessError:
            raise RuntimeError()

    @classmethod
    def is_remote(cls, src_dir, remote, dryrun):
        command = ["git", "ls-remote", remote]
        try:
            execute(command, cwd=src_dir, silent=True, dryrun=dryrun)
            return True
        except CalledProcessError:
            return False

    @classmethod
    def remote_add(cls, src_dir, origin, repo_url, dryrun):
        command = ["git", "remote", "add", origin, repo_url]
        try:
            execute(command, cwd=src_dir, dryrun=dryrun)
        except CalledProcessError:
            raise RuntimeError()

    @classmethod
    def remote_url(cls, src_dir, origin, dryrun):
        command = ["git", "remote", "get-url", origin]
        try:
            return execute(
                command, cwd=src_dir, silent=True, capture_output=True, dryrun=dryrun
            ).strip()
        except CalledProcessError:
            raise RuntimeError()

    @classmethod
    def is_dirty(cls, src_dir, dryrun):
        command = ["git", "status", "--porcelain"]
        try:
            result = execute(
                command, cwd=src_dir, silent=True, capture_output=True, dryrun=dryrun
            ).strip()
            return len(result) != 0
        except CalledProcessError:
            raise RuntimeError()

    @classmethod
    def commit_id(cls, src_dir, dryrun):
        command = ["git", "rev-parse", "--short", "HEAD"]
        try:
            return execute(
                command, cwd=src_dir, silent=True, capture_output=True, dryrun=dryrun
            ).strip()
        except CalledProcessError:
            raise RuntimeError()
