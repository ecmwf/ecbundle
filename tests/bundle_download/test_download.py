# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.


import os
from pathlib import Path
from shutil import rmtree

import pytest
from conftest import Watcher

from ecbundle import BundleDownloader, Git, logger

os.environ["BITBUCKET"] = "ssh://git@git.ecmwf.int"


@pytest.fixture
def watcher():
    return Watcher(logger=logger)


@pytest.fixture
def here():
    return Path(__file__).parent.resolve()


@pytest.fixture
def project1_dir(here):
    """
    Create empty source/project1 directory
    """
    project_dir = here / "source/project1"
    if project_dir.exists():
        project_dir.rmdir()
    project_dir.mkdir(parents=True)
    yield

    # Clean up after us
    rmtree(here / "source")


@pytest.fixture
def project1_subdir1_dir(here):
    """
    Create empty source/project1/subdir1 directory
    """
    project_dir = here / "source/project1/subdir1"
    if project_dir.exists():
        project_dir.rmdir()
    project_dir.mkdir(parents=True)
    yield

    # Clean up after us
    rmtree(here / "source")


@pytest.fixture
def args(here):
    return {
        "no_colour": True,
        "verbose": False,
        "dryrun": True,
        "dry_run": True,
        "bundle": "%s" % here,
        "src_dir": "%s" % (here / "source"),
        "update": False,
        "forced_update": False,
        "threads": 1,
        "shallow": False,
        "github_token": "",
    }


class CleanRepo(Git):
    """
    Custom Git object to mimick existing git repos
    """

    @classmethod
    def is_dirty(cls, *args, **kwargs):
        return False

    @classmethod
    def is_remote(cls, *args, **kwargs):
        return True

    @classmethod
    def is_branch(cls, *args, **kwargs):
        return False

    @classmethod
    def is_tag(cls, *args, **kwargs):
        return False

    @classmethod
    def is_commit(cls, *args, **kwargs):
        return False

    @classmethod
    def remote_url(cls, src_dir, origin, dryrun):
        return "ssh://git@git.ecmwf.int/user/" + Path(src_dir).name


def test_download_simple(args, here, watcher):
    """
    Simple bundle creation test that git clones a single project.
    """
    with watcher:
        BundleDownloader(**args).download()

    assert (
        "git clone -o ec-user ssh://git@git.ecmwf.int/user/project1" in watcher.output
    )
    assert "git -c advice.detachedHead=false checkout 0.0.1" in watcher.output


def test_download_shallow(args, here, watcher):
    """
    Simple bundle creation test that shallow clones a single project.
    """
    args["bundle"] = "%s" % (here / "bundle.yml")
    args["shallow"] = True

    with watcher:
        BundleDownloader(**args).download()

    expected = "git -c advice.detachedHead=false clone -o ec-user -b 0.0.1 "
    "ssh://git@git.ecmwf.int/user/project1 %s/project1 --depth=1" % args["src_dir"]
    assert expected in watcher.output


def test_download_multi(args, here, watcher):
    """
    Simple bundle creation test with multiple projects.
    """
    args["bundle"] = "%s" % (here / "bundle_multi.yml")

    with watcher:
        BundleDownloader(**args).download()

    assert (
        "git clone -o ec-user ssh://git@git.ecmwf.int/user/project1" in watcher.output
    )
    assert "git -c advice.detachedHead=false checkout 0.0.1" in watcher.output
    assert (
        "git clone -o ec-user ssh://git@git.ecmwf.int/user/project2" in watcher.output
    )
    assert "git -c advice.detachedHead=false checkout 0.0.2" in watcher.output


def test_download_update_fetch(args, here, project1_dir, watcher):
    """
    Test repository update for existing project (fetch and checkout)
    """
    args["update"] = True
    args["bundle"] = "%s" % (here / "bundle.yml")

    with watcher:
        BundleDownloader(git=CleanRepo, **args).download()

    # Expect a clean new fetch
    assert "git fetch --tags ec-user" in watcher.output
    assert "git checkout -b 0.0.1 ec-user/0.0.1" in watcher.output


def test_download_update_branch(args, here, project1_dir, watcher):
    """
    Test repository branch update for existing project (checkout and pull)
    """
    args["update"] = True
    args["bundle"] = "%s" % (here / "bundle.yml")

    class CleanBranchRepo(CleanRepo):
        @classmethod
        def branch_upstream(cls, *args, **kwargs):
            return "ec-user/0.0.1"

        @classmethod
        def is_branch(cls, *args, **kwargs):
            return True

        @classmethod
        def remote_url(cls, src_dir, origin, dryrun):
            return "ssh://git@git.ecmwf.int/user/" + Path(src_dir).name

    with watcher:
        BundleDownloader(git=CleanBranchRepo, **args).download()

    assert "git -c advice.detachedHead=false checkout 0.0.1" in watcher.output
    assert "git pull ec-user 0.0.1" in watcher.output


def test_download_force_update_branch(args, here, project1_dir, watcher):
    """
    Test forced-update for existing project branch (fetch and hard reset)
    """
    args["update"] = True
    args["forced_update"] = True
    args["bundle"] = "%s" % (here / "bundle.yml")

    class CleanBranchRepo(CleanRepo):
        @classmethod
        def branch_upstream(cls, *args, **kwargs):
            return "ec-user/0.0.1"

        @classmethod
        def is_branch(cls, *args, **kwargs):
            return True

        @classmethod
        def remote_url(cls, src_dir, origin, dryrun):
            return "ssh://git@git.ecmwf.int/user/" + Path(src_dir).name

    with watcher:
        BundleDownloader(git=CleanBranchRepo, **args).download()

    assert "git -c advice.detachedHead=false checkout 0.0.1" in watcher.output
    assert "git fetch --tags ec-user" in watcher.output
    assert "git reset --hard ec-user/0.0.1" in watcher.output


def test_download_submodules(args, here, watcher):
    """
    Simple bundle creation test with multiple projects that have submodules.
    """
    args["bundle"] = "%s" % (here / "bundle_submodules.yml")

    with watcher:
        BundleDownloader(**args).download()

    assert (
        "git clone -o ec-user ssh://git@git.ecmwf.int/user/project1" in watcher.output
    )
    assert "git -c advice.detachedHead=false checkout 0.0.1" in watcher.output
    assert (
        "git clone -o ec-user ssh://git@git.ecmwf.int/user/project2" in watcher.output
    )
    assert "git -c advice.detachedHead=false checkout 0.0.2" in watcher.output
    assert (
        "git clone -o ec-user ssh://git@git.ecmwf.int/user/project3" in watcher.output
    )
    assert "git -c advice.detachedHead=false checkout develop" in watcher.output
    assert watcher.output.count("git submodule update --init --recursive") == 2


def test_download_submodules_shallow(args, here, watcher):
    """
    Simple bundle creation test using shallow clones with multiple projects that have submodules.
    """
    args["bundle"] = "%s" % (here / "bundle_submodules.yml")
    args["shallow"] = True

    with watcher:
        BundleDownloader(**args).download()

    def expected_command(project, rev):
        base = "git -c advice.detachedHead=false clone -o ec-user"
        version = f"-b {rev}"
        remote = "ssh://git@git.ecmwf.int/user/" + project
        local = here / "source/" / project
        tail = "--depth=1"
        return f"{base} {version} {remote} {local} {tail}"

    assert expected_command("project1", "0.0.1") in watcher.output
    assert expected_command("project2", "0.0.2") in watcher.output
    assert expected_command("project3", "develop") in watcher.output

    assert watcher.output.count("git submodule update --init --recursive") == 2


def test_download_fail_optional(args, here, watcher):
    """
    Test download of an optional project that fails
    """
    args["dryrun"] = False
    args["dry_run"] = False
    args["bundle"] = "%s" % (here / "bundle_optional.yml")

    with watcher:
        BundleDownloader(**args).download()

    assert (
        "git clone -o ec-user ssh://git@git.ecmwf.int/user/project1" in watcher.output
    )
    assert "Could not download or update optional project project1" in watcher.output
    assert (
        "Following projects failed to download but are marked optional:"
        in watcher.output
    )
    assert "    - project1" in watcher.output


def test_download_https(args, here, watcher):
    """
    Simple bundle creation test that git clones a single project using https and token.
    """

    args["bundle"] = "%s" % (here / "bundle_https.yml")
    args["github_token"] = "secrettoken"

    with watcher:
        BundleDownloader(**args).download()

    assert (
        "git clone -o ec-user https://secrettoken@github.com/user/project1.git"
        in watcher.output
    )
    assert "git -c advice.detachedHead=false checkout 0.0.1" in watcher.output


def test_symlink_cloned_project_subdir(args, here, project1_subdir1_dir, watcher):
    """
    Add cloned project subdir as a symlinked bundle entry
    """
    args["bundle"] = "%s" % (here / "bundle_cloned_subdir.yml")

    with watcher:
        BundleDownloader(**args).download()

    assert ("Following projects are symlinked in") in watcher.output
    assert "- subdir1 (project1/subdir1)" in watcher.output


def test_symlink_symlinked_project_subdir(args, here, project1_subdir1_dir, watcher):
    """
    Add symlinked project subdir as a symlinked bundle entry
    """
    args["bundle"] = "%s" % (here / "bundle_symlinked_subdir.yml")

    with watcher:
        BundleDownloader(**args).download()

    assert ("Following projects are symlinked in") in watcher.output
    assert "- subdir1 (symlink_project1/subdir1)" in watcher.output
