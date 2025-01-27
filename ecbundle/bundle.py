# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

import os
from collections import OrderedDict

from .data import Data
from .logging import error, header, success
from .option import Option
from .parse import parse_yaml_file, splitted, to_yaml_str
from .project import Project
from .util import fullpath, mkdir_p, symlink_force

__all__ = ["Bundle", "BundleCreator"]


class Bundle(object):
    """
    Definition of a Bundle of software projects that depend on each
    other and can be downloaded and compiled safely together.
    """

    def __init__(self, filepath, env=True):
        self.filepath = filepath
        self.config = parse_yaml_file(self.filepath)
        if env:
            self.environment_overwrite()

    def get(self, key, default=None):
        return self.config[key] if key in self.config else default

    def name(self):
        return self.get("name", default="bundle")

    def version(self):
        return str(self.get("version", default="0.0.0"))

    def languages(self):
        return self.get("languages")

    def cmake(self):
        if self.get("cmake"):
            split = [c.strip() for c in splitted(self.get("cmake"))]
            return [c for c in split if c]
        else:
            return []

    def projects(self):
        pconf = self.get("projects", [])
        return [
            Project(name=key, **dict(val.items()))
            for p in pconf
            for (key, val) in p.items()
        ]
        # Python 2:
        # return [Project(name=p.items()[0][0], **p.items()[0][1]) for p in pconf]

    def data(self):
        dconf = self.get("data", [])
        return [
            Data(name=key, **dict(val.items()))
            for d in dconf
            for (key, val) in d.items()
        ]
        # Python 2:
        # return [Data(name=d.items()[0][0], **d.items()[0][1]) for d in dconf]

    def options(self):
        optconf = self.get("options", [])
        return [
            Option(name=key, **dict(val.items()))
            for opt in optconf
            for (key, val) in opt.items()
        ]
        # Python 2:
        # return [Option(name=opt.items()[0][0], **opt.items()[0][1]) for opt in optconf]

    def file(self):
        return self.filepath

    def __str__(self):
        return str(self.config)

    def __repr__(self):
        return str(self.config)

    def yaml(self):
        return to_yaml_str(self.config)

    def environment_overwrite(self):
        import os

        BUNDLE = self.name().replace("-", "_").upper()

        skip_projects = []

        for i, p in enumerate(self.projects()):
            pname = p.name()
            PNAME = pname.replace("-", "_").upper()
            NAME = BUNDLE + "_" + PNAME

            pconf = self.config["projects"][i][p.name()]
            VERSION = NAME + "_VERSION"
            if os.getenv(VERSION):
                pconf["version"] = os.getenv(VERSION)

            CMAKE = NAME + "_CMAKE"
            if os.getenv(CMAKE):
                pconf["cmake"] = os.getenv(CMAKE)

            GIT = NAME + "_GIT"
            if os.getenv(GIT):
                pconf["git"] = os.getenv(GIT)

            SKIP = BUNDLE + "_SKIP_" + PNAME
            if os.getenv(SKIP):
                skip_projects.append(i)

            DIR = NAME + "_DIR"
            if os.getenv(DIR):
                pconf["dir"] = os.getenv(DIR)

        for i in reversed(skip_projects):
            self.config["projects"].pop(i)


class BundleCreator(object):
    def __init__(self, **kwargs):
        self.config = kwargs

    def get(self, key, default=None):
        return self.config[key] if self.config[key] is not None else default

    def dryrun(self):
        if self.get("dryrun"):
            return self.get("dryrun")
        if self.get("dry_run"):
            return self.get("dry_run")
        return False

    def src_dir(self):
        return fullpath(self.get("src_dir", "source"))

    def bundle(self):
        bundle_path = fullpath(self.get("bundle", None))
        if bundle_path:
            if os.path.isfile(bundle_path):
                return Bundle(bundle_path, env=True)
            if not os.path.isdir(bundle_path):
                error(
                    "ERROR: --bundle argument is not a valid bundle directory or file path"
                )
                return None

        filedirs = [bundle_path, os.getcwd()]
        for d in filedirs:
            bundle_path = "/".join([d, "bundle.yml"])
            if os.path.isfile(bundle_path):
                return Bundle(bundle_path)
        error("ERROR: No bundle file could be found")
        error("       Searched in " + ", ".join(filedirs))
        return None

    def create(self):
        bundle = self.bundle()
        if not bundle:
            return 1

        success("\nCreating bundle for ")
        header("    " + bundle.file())

        src_dir = self.src_dir()
        mkdir_p(src_dir)

        bundle_yml_file = src_dir + "/bundle.yml"

        if self.bundle_needs_updating():
            symlink_force(bundle.file(), bundle_yml_file)
            symlink_force(os.path.dirname(bundle.file()) + "/arch", src_dir + "/arch")

            self.create_cmakelists_from_bundle()

            success("\nBundle created at src-dir")
            header("    " + src_dir + "\n")

        else:
            success("\nBundle does not need updating at src-dir")
            header("    " + src_dir + "\n")

        self.print_projects()
        return 0

    def print_projects(self):
        print("\nprojects:")
        for project in self.bundle().projects():
            if (
                not os.path.exists(self.src_dir() + "/" + project.name())
                and project.optional()
            ):
                continue
            msg = "    - " + project.name()
            if os.path.islink(self.src_dir() + "/" + project.name()):
                if project.dir():
                    msg += " (symbolic link to [" + project.dir() + "])"
                else:
                    msg += " (symbolic link to ["
                    msg += os.readlink(self.src_dir() + "/" + project.name())
                    msg += "])"
            elif project.version():
                msg += " (" + project.version() + ")"
            print(msg)

    def bundle_needs_updating(self):
        src_dir = self.src_dir()
        bundle_yml_path = src_dir + "/bundle.yml"
        bundle_cmake_path = src_dir + "/CMakeLists.txt"

        if os.path.exists(bundle_yml_path):
            if os.path.exists(bundle_cmake_path):
                if os.path.getmtime(bundle_cmake_path) < os.path.getmtime(
                    bundle_yml_path
                ):
                    return True

                tmp_cmake_path = self.create_cmakelists_from_bundle(
                    "CMakeLists.txt.tmp"
                )
                with open(tmp_cmake_path, "r") as tmp_cmake_file:
                    tmp_cmake_from_file = tmp_cmake_file.read()
                with open(bundle_cmake_path, "r") as bundle_cmake_file:
                    bundle_cmake_from_file = bundle_cmake_file.read()
                os.remove(tmp_cmake_path)

                if bundle_cmake_from_file == tmp_cmake_from_file:
                    return False

        return True

    def create_cmakelists_from_bundle(self, name="CMakeLists.txt"):
        bundle = self.bundle()
        ecbuild_in_bundle = False
        for project in bundle.projects():
            if project.name() == "ecbuild":
                ecbuild_in_bundle = True

        bundle_path = self.src_dir() + "/" + name
        bundle_file = open(bundle_path, "wt")

        bundle_file.write(
            """
# ecbundle automatically generated this file from file """
            + bundle.file()
            + """.

cmake_minimum_required( VERSION 3.12 FATAL_ERROR )
"""
        )
        bundle_file.write(
            """
####################################################################

macro( ecbundle_add_project package_name )
    #
    #   add_subdirectory depending on BUILD_${package_name}
    #
    set( BUILD_${package_name} ON CACHE BOOL "" )

    if( BUILD_${package_name} )
        set( dir ${ARGV1} )
        if( NOT dir )
            set( dir ${package_name} )
        endif()
        add_subdirectory( ${dir} )
     endif()
endmacro()

macro( ecbundle_set key value )
    set( ${key} ${value} CACHE STRING "" )
    if( "${${key}}" STREQUAL "${value}" )
       message("  - ${key} = ${value}" )
    else()
       message("  - ${key} = ${${key}} [default=${value}]" )
    endif()
endmacro()
"""
        )
        cmake_args = OrderedDict()

        def ecbundle_set(key, value):
            value = value.replace("${SOURCE_DIR}", "${CMAKE_CURRENT_SOURCE_DIR}")
            value = value.replace("${INSTALL_DIR}", "${CMAKE_INSTALL_PREFIX}")
            bundle_file.write("ecbundle_set( " + key + " " + value + " )\n")

        def add_cmake_arg(cmake_arg):
            key, value = cmake_arg.split("=", 1)
            if key not in cmake_args:
                cmake_args[key] = value
            else:
                if value != cmake_args[key]:
                    error(
                        "CMake option "
                        + key
                        + " is attempted to be set to value "
                        + value
                        + " while it was already previously set to "
                        + cmake_args[key]
                    )

        for cmake_arg in bundle.cmake():
            add_cmake_arg(cmake_arg)

        for project in bundle.projects():
            if project.bundle():
                if project.cmake():
                    for cmake_arg in project.cmake():
                        add_cmake_arg(cmake_arg)

        if cmake_args:
            bundle_file.write(
                """
####################################################################

message( "" )"""
            )
            bundle_version_str = " [" + bundle.version() + "]"
            if bundle.version() == "0.0.0":
                bundle_version_str = ""
            bundle_file.write(
                """
message( """
                + '"'
                + bundle.name()
                + bundle_version_str
                + """\" )"""
            )
            bundle_file.write(
                """
message( "  - source     : ${CMAKE_CURRENT_SOURCE_DIR}" )
message( "  - build      : ${CMAKE_CURRENT_BINARY_DIR}" )
message( "  - install    : ${CMAKE_INSTALL_PREFIX}"     )
message( "  - build type : ${CMAKE_BUILD_TYPE}"       )
message( "" )
message( "Bundle variables set for this build:" )

"""
            )
            for key, value in cmake_args.items():
                ecbundle_set(key, value)

        bundle_file.write(
            """message("")

####################################################################
"""
        )
        if ecbuild_in_bundle:
            bundle_file.write(
                """
find_package( ecbuild 3.0 REQUIRED HINTS ${CMAKE_CURRENT_SOURCE_DIR}/ecbuild )"""
            )
        else:
            bundle_file.write(
                """
find_package( ecbuild 3.0 QUIET )"""
            )
        if bundle.languages() is None:
            languages = ""
        else:
            languages = " LANGUAGES " + bundle.languages()
        bundle_file.write(
            """
project( """
            + bundle.name()
            + """ VERSION """
            + self.bundle().version()
            + languages
            + """ )

## Initialize
include(${CMAKE_CURRENT_BINARY_DIR}/init.cmake OPTIONAL)

## Projects

"""
        )

        for project in bundle.projects():
            if project.bundle():
                args = project.name()
                if project.subdir():
                    subdir = project.name() + "/" + project.subdir()
                    args += " " + subdir
                if not project.optional() or os.path.exists(
                    self.src_dir() + "/" + project.name()
                ):
                    bundle_file.write("ecbundle_add_project( " + args + " )\n")

        bundle_file.write(
            """
## Finalize
include(${CMAKE_CURRENT_BINARY_DIR}/final.cmake OPTIONAL)
"""
        )
        if ecbuild_in_bundle:
            bundle_file.write(
                """
ecbuild_install_project(NAME ${PROJECT_NAME})
ecbuild_print_summary()
"""
            )
        else:
            bundle_file.write(
                """
if( ecbuild_FOUND )
  ecbuild_install_project(NAME ${PROJECT_NAME})
  ecbuild_print_summary()
endif()
"""
            )

        bundle_file.close()

        return bundle_path
