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

from ecbundle import BundleBuilder, logger


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
    build_dir = here / "build"
    install_dir = here / "install"
    yield

    # Clean up after us
    if src_dir.exists():
        shutil.rmtree(src_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if install_dir.exists():
        shutil.rmtree(install_dir)


@pytest.fixture
def args(here):
    return {
        "no_colour": True,
        "verbose": False,
        "dryrun": True,
        "dry_run": True,
        "src_dir": "%s" % (here / "source"),
        "build_dir": "%s" % (here / "build"),
        "install_dir": "%s" % (here / "install"),
        "log": "INFO",
        "threads": 1,
        "cache": None,
        "ninja": False,
        "target": [],
        "keep_going": False,
        "retry": False,
        "retry_verbose": False,
        "clean": False,
        "install": False,
        "reconfigure": False,
        "without_tests": False,
        "cmake": None,
        "project1.cmake": None,
        "arch": None,
        "build_type": "BIT",
    }


def test_build_make(args, here, cleanup, watcher):
    src_dir = here / "source"
    build_dir = here / "build"
    install_dir = here / "install"

    # Clean directory
    if src_dir.exists():
        shutil.rmtree(src_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if install_dir.exists():
        shutil.rmtree(install_dir)

    src_dir.mkdir()
    shutil.copy(here / "bundle.yml", src_dir / "bundle.yml")

    with watcher:
        BundleBuilder(**args).build()

    # Test that build infrastructure scripts are generated
    # TODO: Check their content is fine!
    assert (build_dir / "env.sh").exists()
    assert (build_dir / "clean.sh").exists()
    assert (build_dir / "configure.sh").exists()
    assert (build_dir / "build.sh").exists()
    assert (build_dir / "install.sh").exists()

    # Ensure that two base commands are run!
    # TODO: Interception of command execution is still wonky,
    # as it relies on `print('+ ' + ...)` to stdout for capturing by the watcher!
    assert ("%s/configure.sh --when-needed" % build_dir) in watcher.output
    assert ("%s/build.sh --without-configure" % build_dir) in watcher.output

    # Ensure that we are calling make
    with (build_dir / "build.sh").open("r") as f:
        build_script = f.read()
    assert "make -j1" in build_script


def test_build_ninja(args, here, cleanup, watcher):
    src_dir = here / "source"
    build_dir = here / "build"
    install_dir = here / "install"

    args["ninja"] = True

    # Clean directory
    if src_dir.exists():
        shutil.rmtree(src_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if install_dir.exists():
        shutil.rmtree(install_dir)

    src_dir.mkdir()
    shutil.copy(here / "bundle.yml", src_dir / "bundle.yml")

    with watcher:
        BundleBuilder(**args).build()

    # Test that build infrastructure scripts are generated
    # TODO: Check their content is fine!
    assert (build_dir / "env.sh").exists()
    assert (build_dir / "clean.sh").exists()
    assert (build_dir / "configure.sh").exists()
    assert (build_dir / "build.sh").exists()
    assert (build_dir / "install.sh").exists()

    # Ensure that two base commands are run!
    # TODO: Interception of command execution is still wonky,
    # as it relies on `print('+ ' + ...)` to stdout for capturing by the watcher!
    assert ("%s/configure.sh --when-needed" % build_dir) in watcher.output
    assert ("%s/build.sh --without-configure" % build_dir) in watcher.output

    # Ensure that we are calling make
    with (build_dir / "build.sh").open("r") as f:
        build_script = f.read()
    assert "ninja -j1" in build_script


def test_build_custom_arch(args, here, cleanup, watcher):
    src_dir = here / "source"
    build_dir = here / "build"
    install_dir = here / "install"
    arch_dir = src_dir / "arch"
    custom_arch_dir = arch_dir / "custom"

    args["arch"] = "custom"

    # Clean directory
    if src_dir.exists():
        shutil.rmtree(src_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if install_dir.exists():
        shutil.rmtree(install_dir)
    if arch_dir.exists():
        shutil.rmtree(arch_dir)

    src_dir.mkdir()
    arch_dir.mkdir()
    custom_arch_dir.mkdir()

    shutil.copy(here / "bundle.yml", src_dir / "bundle.yml")

    with open(custom_arch_dir / "env.sh", "w") as envfile:
        envfile.write('echo "custom environment for test"')

    with watcher:
        bundle_builder = BundleBuilder(**args)
        assert bundle_builder.arch() is not None
        bundle_builder.build()

    with open(build_dir / "env.sh", "r") as envfile:
        assert ('echo "custom environment for test"') in envfile.read()


def test_build_invalid_arch(args, here, cleanup, watcher):
    src_dir = here / "source"
    build_dir = here / "build"
    install_dir = here / "install"

    args["arch"] = "invalid"

    # Clean directory
    if src_dir.exists():
        shutil.rmtree(src_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if install_dir.exists():
        shutil.rmtree(install_dir)

    src_dir.mkdir()
    shutil.copy(here / "bundle.yml", src_dir / "bundle.yml")

    with watcher:
        bundle_builder = BundleBuilder(**args)
        with pytest.raises(Exception):
            assert bundle_builder.arch()
            assert ('ERROR: arch "invalid" could not be found') in watcher.output
