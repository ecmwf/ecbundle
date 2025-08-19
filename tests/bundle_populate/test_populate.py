# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.


import shutil
from os import chmod
from pathlib import Path

import pytest
from conftest import Watcher

from ecbundle import Populator, logger


@pytest.fixture
def watcher():
    return Watcher(logger=logger)


@pytest.fixture
def here():
    return Path(__file__).parent.resolve()


@pytest.fixture
def populate(here):
    """
    Add a dummy populate script.
    """

    src_dir = here / "source"
    if not src_dir.exists():
        src_dir.mkdir()

    project_dir = src_dir / "project1"
    if not project_dir.exists():
        project_dir.mkdir()

    populate_script = """#!/usr/bin/env bash
echo "ARTIFACTS_DIR=$ARTIFACTS_DIR"
echo "POPULATE_OPTION_1=$POPULATE_OPTION_1"
echo "POPULATE_OPTION_2=$POPULATE_OPTION_2"
"""

    script_path = project_dir / "populate"
    if not script_path.exists():
        with open(script_path, "w") as file:
            file.write(populate_script)
        chmod(script_path, 0o755)

    yield src_dir, project_dir

    # Clean up after ourselves
    if src_dir.exists():
        shutil.rmtree(src_dir)


@pytest.fixture
def args(here):
    return {
        "src_dir": "%s" % (here / "source"),
        "dryrun": False,
        "capture_output": True,
    }


def test_populate(here, args, populate, watcher):
    src_dir, project_dir = populate
    shutil.copy(here / "bundle.yml", src_dir / "bundle.yml")

    with watcher:
        Populator(**args).create()

    assert f"{project_dir}/populate" in watcher.output
    assert f"ARTIFACTS_DIR={src_dir}/artifacts" in watcher.output
    assert "POPULATE_OPTION_1=0" in watcher.output
    assert "POPULATE_OPTION_2=A" in watcher.output


@pytest.mark.parametrize(
    "populate_option",
    [{"non_zero_option_1": True}, {"option_2": "B"}, {"set_both_options": "B"}],
)
def test_populate_options(here, args, populate, watcher, populate_option):
    src_dir, project_dir = populate
    shutil.copy(here / "bundle.yml", src_dir / "bundle.yml")

    args.update(populate_option)
    with watcher:
        Populator(**args).create()

    assert f"{project_dir}/populate" in watcher.output
    assert f"ARTIFACTS_DIR={src_dir}/artifacts" in watcher.output

    if any(opt in populate_option for opt in ["non_zero_option_1", "set_both_options"]):
        assert "POPULATE_OPTION_1=1" in watcher.output
    else:
        assert "POPULATE_OPTION_1=0" in watcher.output

    if any(opt in populate_option for opt in ["option_2", "set_both_options"]):
        assert 'POPULATE_OPTION_2="B"' in watcher.output
    else:
        assert "POPULATE_OPTION_2=A" in watcher.output
