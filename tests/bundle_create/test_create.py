# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.


import shutil
from pathlib import Path

import pytest
from conftest import Watcher

from ecbundle import BundleCreator, logger


@pytest.fixture
def watcher():
    return Watcher(logger=logger)


@pytest.fixture
def here():
    return Path(__file__).parent.resolve()


@pytest.fixture
def cleanup(here):
    """
    Remove any created ``source`` directories
    """
    src_dir = here / "source"
    yield

    # Clean up after us
    if src_dir.exists():
        shutil.rmtree(src_dir)


def test_create_simple(here, cleanup):
    """
    Test creation of the agglomerated bundle in ``./source``.
    """
    src_dir = here / "source"
    args = {
        "no_colour": True,
        "verbose": False,
        "dryrun": True,
        "dry_run": True,
        "bundle": "%s" % here,
        "src_dir": "%s" % src_dir,
        "update": False,
        "forced_update": False,
        "threads": 1,
        "shallow": False,
    }

    # Clean directory
    if src_dir.exists():
        shutil.rmtree(src_dir)
    src_dir.mkdir()

    BundleCreator(**args).create()

    assert (src_dir / "CMakeLists.txt").exists()
    assert (src_dir / "bundle.yml").exists()


def test_create_optional_fail(here, cleanup):
    """
    Test creation of the agglomerated bundle in ``./source`` with
    failing optional package .
    """
    src_dir = here / "source"
    args = {
        "no_colour": True,
        "verbose": False,
        "dryrun": True,
        "dry_run": True,
        "src_dir": "%s" % src_dir,
        "update": False,
        "forced_update": False,
        "threads": 1,
        "shallow": False,
        "bundle": (here / "bundle-optional.yml"),
    }

    # Clean directory
    if src_dir.exists():
        shutil.rmtree(src_dir)
    src_dir.mkdir()

    BundleCreator(**args).create()

    assert (src_dir / "CMakeLists.txt").exists()
    assert (src_dir / "bundle.yml").exists()
    assert (
        "ecbundle_add_project( project1 )" in (src_dir / "CMakeLists.txt").read_text()
    )
    assert (
        "ecbundle_add_project( project2 )"
        not in (src_dir / "CMakeLists.txt").read_text()
    )


def test_create_optional_success(here, cleanup):
    """
    Test creation of the agglomerated bundle in ``./source`` with
    successful optional package .
    """
    src_dir = here / "source"
    args = {
        "no_colour": True,
        "verbose": False,
        "dryrun": True,
        "dry_run": True,
        "src_dir": "%s" % src_dir,
        "update": False,
        "forced_update": False,
        "threads": 1,
        "shallow": False,
        "bundle": (here / "bundle-optional.yml"),
    }

    # Clean directory
    if src_dir.exists():
        shutil.rmtree(src_dir)
    src_dir.mkdir()

    # Fake download by creating corresponding directories
    (src_dir / "project1").mkdir()
    (src_dir / "project2").mkdir()

    BundleCreator(**args).create()

    assert (src_dir / "CMakeLists.txt").exists()
    assert (src_dir / "bundle.yml").exists()
    assert (
        "ecbundle_add_project( project1 )" in (src_dir / "CMakeLists.txt").read_text()
    )
    assert (
        "ecbundle_add_project( project2 )" in (src_dir / "CMakeLists.txt").read_text()
    )
    

def test_create_existing_symlink(here, cleanup, watcher):
    """
    Test creation of the agglomerated bundle in ``./source`` with a
    symlink already present.
    """
    src_dir = here / "source"
    args = {
        "no_colour": True,
        "verbose": False,
        "dryrun": True,
        "dry_run": True,
        "bundle": "%s" % here,
        "src_dir": "%s" % src_dir,
        "update": False,
        "forced_update": False,
        "threads": 1,
        "shallow": False,
    }

    # Clean directory
    if src_dir.exists():
        shutil.rmtree(src_dir)
    src_dir.mkdir()
    
    # Create a symlink to a fake path in source
    (src_dir / "project1").symlink_to("../non-existent-fake-path")

    with watcher:
        BundleCreator(**args).create()

    assert (src_dir / "CMakeLists.txt").exists()
    assert (src_dir / "bundle.yml").exists()
    assert "- project1" in watcher.output
    assert "[../non-existent-fake-path]" in watcher.output
