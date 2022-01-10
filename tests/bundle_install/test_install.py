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

from ecbundle import BundleBuilder, BundleCreator, logger


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
        "bundle": "%s" % here,
    }


def test_build_install(args, here, cleanup, watcher):
    src_dir = here / "source"
    build_dir = here / "build"
    install_dir = here / "install"

    args["dryrun"] = False
    args["dry_run"] = False

    # Clean directory
    if src_dir.exists():
        shutil.rmtree(src_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if install_dir.exists():
        shutil.rmtree(install_dir)

    src_dir.mkdir()
    shutil.copy(here / "bundle.yml", src_dir / "bundle.yml")

    def create_install_target(dir):
        # Without any "install()" in CMake the install target doens't exist.
        # We create a "final.cmake" file that gets included by the bundle
        # if it exists and add install target inside.
        with open(dir / "final.cmake", "w") as final_file:
            final_file.write(
                """
            install(FILES CMakeLists.txt DESTINATION ".")
            """
            )

    with watcher:
        BundleCreator(**args).create()
        args["dryrun"] = True
        BundleBuilder(**args).build()
        create_install_target(build_dir)
        args["dryrun"] = False
        args["install"] = True
        BundleBuilder(**args).build()

    # Test that build infrastructure scripts are generated
    # TODO: Check their content is fine!
    assert (build_dir / "env.sh").exists()
    assert (build_dir / "clean.sh").exists()
    assert (build_dir / "configure.sh").exists()
    assert (build_dir / "build.sh").exists()
    assert (build_dir / "install.sh").exists()
    assert (build_dir / "build.log").exists()
    assert (install_dir / "share/test-bundle-simple/arch/env.sh").exists()
    assert (install_dir / "share/test-bundle-simple/build.log").exists()
