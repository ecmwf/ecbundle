# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

import re
import string
import sys
from os import chmod, getcwd, listdir, path, readlink
from shutil import copyfile
from subprocess import CalledProcessError, check_call

from .bundle import Bundle
from .logging import colors, error, header, success
from .util import Timer, fullpath, mkdir_p, symlink_force

__all__ = ["BundleBuilder"]


SCRIPT_NAME = path.basename(sys.argv[0])
SCRIPT_DIR = path.dirname(path.abspath(__file__))


class NinjaBackend:
    def cmake_generator(self):
        return "-G Ninja"

    def executable(self):
        return "ninja"

    def keep_going(self):
        return "-k0"

    def verbose(self):
        return "-v"

    def threads(self, n):
        return "-j" + str(n)

    def targets(self, targets):
        return " ".join([str(i) for i in targets])

    def rerun_cmake_if_needed(self):
        return self.executable() + " build.ninja"

    def file(self):
        return "build.ninja"

    def command(self, threads, targets, verbose=False, keep_going=False):
        command_list = [self.executable(), self.threads(threads), self.targets(targets)]
        if verbose:
            command_list.append(self.verbose())
        if keep_going:
            command_list.append(self.keep_going())
        return " ".join(command_list)

    def install(self, threads):
        return " ".join([self.executable(), self.threads(threads), "install"])


class MakeBackend:
    def cmake_generator(self):
        return ""

    def executable(self):
        return "make"

    def keep_going(self):
        return "-k"

    def verbose(self):
        return "VERBOSE=1 --no-print-directory"

    def threads(self, n):
        return "-j" + str(n)

    def targets(self, targets):
        return " ".join([str(i) for i in targets])

    def rerun_cmake_if_needed(self):
        return self.executable() + " cmake_check_build_system"

    def file(self):
        return "Makefile"

    def command(self, threads, targets, verbose=False, keep_going=False):
        command_list = [self.executable(), self.threads(threads), self.targets(targets)]
        if verbose:
            command_list.append(self.verbose())
        if keep_going:
            command_list.append(self.keep_going())
        return " ".join(command_list)

    def install(self, threads):
        return " ".join([self.executable(), self.threads(threads), "install/fast"])


clean_sh = string.Template(
    """#!/usr/bin/env bash

# Clean script
#
# All files and directories will be removed that are not globbed by
#     - *backup*
#     - *.sh
#     - init.cmake
#     - final.cmake
#     - toolchain.cmake

SCRIPT_DIR="$( cd $( dirname "${BASH_SOURCE[0]}" ) && pwd -P )"
SCRIPT_NAME="$( basename "${BASH_SOURCE[0]}" )"

set -exa
cd ${SCRIPT_DIR}

find . -maxdepth 1 -mindepth 1 -not -name '*.sh' -a -not -name '*backup*' \
  -a -not -name 'init.cmake' -a -not -name 'final.cmake' -a -not -name 'toolchain.cmake' \
-print0 | xargs -0 rm -rf --

"""
)

####################################################################################################

configure_sh = string.Template(
    """#!/usr/bin/env bash

# Configure script, generated by ecbundle version ${ecbundle_version}
#
# The environment in the file "env.sh" will be sourced
# before the build is configured

SCRIPT_DIR="$( cd $( dirname "${BASH_SOURCE[0]}" ) && pwd -P )"
cd ${SCRIPT_DIR}

LOG_FILE=${SCRIPT_DIR}/build.log
exec 1> >(tee -a "$LOG_FILE") 2>&1
shopt -s expand_aliases
alias trace_on='set -x'
alias trace_off='{ PREV_STATUS=$? ; set +x; sync; } 2>/dev/null; (exit $PREV_STATUS)'

### Environment
echo "=============================================================="
echo "                           ENVIRONMENT                        "
echo "=============================================================="
echo
echo
echo "DATE: $(date +%FT%TZ)"
echo
echo
trace_on
SOURCE_DIR=${src_dir}
INSTALL_DIR=${install_dir}
BUILD_DIR=${SCRIPT_DIR}
BUILD_TYPE=${build_type}
trace_off

if [[ -f ${BUILD_DIR}/toolchain.cmake ]]; then
   export CMAKE_TOOLCHAIN_FILE=${BUILD_DIR}/toolchain.cmake
   echo "+ export CMAKE_TOOLCHAIN_FILE=${CMAKE_TOOLCHAIN_FILE}"
fi

trace_on
ECBUNDLE_CONFIGURE=ON
ECBUILD_CONFIGURE=ON # deprecated, use ECBUNDLE_CONFIGURE
source ${BUILD_DIR}/env.sh
trace_off


echo
echo
echo "=============================================================="
echo "                       CONFIGURATION                          "
echo "=============================================================="
echo
echo

CMAKE_ARGS="${CMAKE_ARGS} -DCMAKE_BUILD_TYPE=${BUILD_TYPE}"
CMAKE_ARGS="${CMAKE_ARGS} -DCMAKE_INSTALL_PREFIX=${INSTALL_DIR}"
# The CMAKE_TOOLCHAIN_FILE env var is sufficient for CMake 3.21 and over
[[ ! -z "${CMAKE_TOOLCHAIN_FILE}" ]] && CMAKE_ARGS="${CMAKE_ARGS} -DCMAKE_TOOLCHAIN_FILE=${CMAKE_TOOLCHAIN_FILE}"

START=$(date +%s)

if [ ! -f ${build_file} ] || [ "$1" != "--when-needed" ]; then
    trace_on
    cmake ${SOURCE_DIR} \
          ${CMAKE_ARGS} \
          ${cmake_args}
    trace_off
else
    ${rerun_cmake_if_needed}
fi

{ set +x; } 2>/dev/null
END=$(date +%s)
DIFF=$(( $END - $START ))
echo; echo "Configuration took $DIFF seconds"
"""
)

####################################################################################################

build_sh = string.Template(
    """#!/usr/bin/env bash

# Build script, generated by ecbundle version ${ecbundle_version}
#
# When the build is not configured, the script
# "configure.sh" will be called first.

set -ea

SCRIPT_DIR="$( cd $( dirname "${BASH_SOURCE[0]}" ) && pwd -P )"
LOG_FILE=${SCRIPT_DIR}/build.log

cd ${SCRIPT_DIR}

if [ ! -f ${build_file} ] || [ "$1" != "--without-configure" ]; then
   ./configure.sh --when-needed
fi

exec 1> >(tee -a "$LOG_FILE") 2>&1

source ./env.sh

set +x
echo
echo
echo "=============================================================="
echo "                            BUILD                             "
echo "=============================================================="
echo
echo
START=$(date +%s)

set -x

${build}

{ set +x; } 2>/dev/null
END=$(date +%s)
DIFF=$(( $END - $START ))
echo; echo "Build took $DIFF seconds"
"""
)

####################################################################################################

install_sh = string.Template(
    """#!/usr/bin/env bash

# Install script, generated by ecbundle version ${ecbundle_version}

#
# Optional argument:
#    --fast  :  Install without dependency checks
#               (Useful when project is just built)

set -ea

SCRIPT_DIR="$( cd $( dirname "${BASH_SOURCE[0]}" ) && pwd -P )"
LOG_FILE=${SCRIPT_DIR}/build.log

cd ${SCRIPT_DIR}

if [ "$1" != "--fast" ]; then
 ./build.sh
fi

exec 1> >(tee -a "$LOG_FILE") 2>&1

### Environment
source ./env.sh

set +x
echo
echo
echo
echo "=============================================================="
echo "                           INSTALL                            "
echo "=============================================================="
echo
echo
echo
START=$(date +%s)
set -x

${install}

{ set +x; } 2>/dev/null

echo

INSTALL_DIR=${install_dir}
mkdir -p ${INSTALL_DIR}/share/${bundle_name}/arch/
for file in env.sh toolchain.cmake init.cmake final.cmake
do
  if [ -f $file ]; then
    echo Installing: ${INSTALL_DIR}/share/${bundle_name}/arch/$file
    chmod 644 $file
    cp $file ${INSTALL_DIR}/share/${bundle_name}/arch/
  fi
done
echo Installing: ${INSTALL_DIR}/share/${bundle_name}/build.log
chmod 644 ${LOG_FILE}
cp ${LOG_FILE} ${INSTALL_DIR}/share/${bundle_name}/build.log



END=$(date +%s)
DIFF=$(( $END - $START ))
echo; echo "Install took $DIFF seconds"
"""
)


class BundleBuilder(object):
    def __init__(self, **kwargs):
        self.config = kwargs

        if "no_colour" in kwargs:
            if kwargs["no_colour"]:
                colors.disable()
            else:
                colors.enable()

    def get(self, key, default=None):
        key = key.replace("-", "_")
        return self.config[key] if self.config.get(key) is not None else default

    def src_dir(self):
        return fullpath(self.get("src_dir", "source"))

    def build_dir(self):
        return fullpath(self.get("build_dir", "build"))

    def install_dir(self):
        return fullpath(self.get("install_dir", "install"))

    def threads(self):
        return self.get("threads", 1)

    def targets(self):
        return self.get("target", [])

    def build_type(self):
        return self.get("build_type", "BIT")

    def backend(self):
        if self.get("ninja", False):
            return NinjaBackend()
        else:
            return MakeBackend()

    def verbose(self):
        return self.get("verbose", False)

    def keep_going(self):
        return self.get("keep_going", False)

    def retry(self):
        return self.get("retry", False)

    def retry_verbose(self):
        return self.get("retry_verbose", False)

    def log(self):
        default = "DEBUG" if self.verbose() else None
        value = self.get("log", default)
        if value:
            value = value.upper()
        return value

    def cache(self):
        return fullpath(self.get("cache", None))

    def bundle(self):
        return Bundle(self.src_dir() + "/bundle.yml", env=False)

    def arch(self):
        arch = self.get("arch", None)

        if not arch:
            return None

        arch_path = None
        src_dir = self.src_dir()
        arch_dirs = [src_dir + "/arch", getcwd()]
        arch_check_files = []
        arch_check_files.append(arch)
        arch_check_files.append("/".join([arch, "env.sh"]))
        for p in arch_dirs:
            arch_check_files.append("/".join([p, arch]))
            arch_check_files.append("/".join([p, arch, "env.sh"]))
            arch_check_files.append("/".join([p, arch, "default", "env.sh"]))
        for f in arch_check_files:
            if path.isfile(f):
                arch_path = fullpath(f)
                return arch_path

        error(
            'ERROR: arch "' + arch + '" could not be found in ' + str(arch_dirs) + ".\n"
        )
        raise RuntimeError()

    def list_archs(self):
        import os

        rootdir = self.src_dir() + "/arch"
        for dirpaths, dirnames, filenames in os.walk(rootdir, followlinks=True):
            if not dirnames:
                print(dirpaths.replace(rootdir + "/", "").replace("/default", ""))

    def no_colour(self):
        return self.get("no_colour", False)

    def without_tests(self):
        return self.get("without_tests", False)

    def cmake_args(self):
        keys = ["cmake"]
        for project in self.bundle().projects():
            keys.append(project.name() + ".cmake")

        return_cmake_args = ""
        for key in keys:
            if self.get(key):
                # split values by whitespace while respecting double quotes or single quotes
                # Example 1
                #      --cmake="LAPACK_LIBRARIES=\"lib1 lib2\" ENABLE_TESTS=OFF"
                # results in
                #      values = [ 'LAPACK_LIBRARIES="lib1 lib2"' , 'ENABLE_TESTS=OFF' ]
                # cmake: -DLAPACK_LIBRARIES="lib1 lib2" -DENABLE_TESTS=OFF
                #
                # Example 2
                #      --cmake="LAPACK_LIBRARIES='lib1 lib2' ENABLE_TESTS=OFF"
                # results in
                #      values = [ "LAPACK_LIBRARIES='lib1 lib2'" , 'ENABLE_TESTS=OFF' ]
                # cmake arguments:
                #      -DLAPACK_LIBRARIES='lib1 lib2' -DENABLE_TESTS=OFF
                #
                # Example 3
                #      --cmake='LAPACK_LIBRARIES="lib1 lib2" ENABLE_TESTS=OFF'
                # results in
                #      values = [ 'LAPACK_LIBRARIES="lib1 lib2"' , 'ENABLE_TESTS=OFF' ]
                # cmake arguments:
                #      -DLAPACK_LIBRARIES="lib1 lib2" -DENABLE_TESTS=OFF
                #
                #
                # WARNING: following would not be OK:
                #      --cmake='LAPACK_LIBRARIES=\"lib1 lib2\" ENABLE_TESTS=OFF'
                # results in
                #      values = [ 'LAPACK_LIBRARIES=\\"lib1 lib2\\"' , 'ENABLE_TESTS=OFF' ]
                # cmake arguments:
                #      -DLAPACK_LIBRARIES=\"lib1 lib2\" -DENABLE_TESTS=OFF
                values = re.findall(
                    r'(?:[^\s"\']|["\'](?:\\.|[^"\'])*["\'])+', self.get(key)
                )
                for value in values:
                    return_cmake_args += " -D" + value
        return return_cmake_args

    def create_scripts(self):

        src_dir = self.src_dir()
        build_dir = self.build_dir()
        install_dir = self.install_dir()

        build1 = self.backend().command(
            self.threads(),
            self.targets(),
            keep_going=self.keep_going(),
            verbose=self.verbose(),
        )
        build2 = self.backend().command(
            self.threads(),
            self.targets(),
            keep_going=False,
            verbose=(self.verbose() or self.retry_verbose()),
        )

        build = """
${build1}
"""
        if self.retry() or self.retry_verbose():
            build = """
set +e
${build1}
build_rc=$?
set -e
if [[ ${build_rc} != 0 ]]; then  # Retry if build failed
    set +x
    echo
    echo
    echo
    echo "=============================================================="
    echo "                    COMPILATION ERRORS                        "
    echo "=============================================================="
    echo
    echo
    echo
    set -x
    ${build2}
fi
"""
        build = string.Template(build).safe_substitute(build1=build1, build2=build2)
        cmake_args = " " + self.backend().cmake_generator()

        if self.log():
            cmake_args += " -DECBUILD_LOG_LEVEL=" + self.log()

        options = self.bundle().options()
        for opt in options:
            arg = self.get(opt.key())
            if arg:
                if opt.cmake():
                    cmake_args += " " + " ".join(["-D" + o for o in opt.cmake(arg)])

        if self.without_tests():
            cmake_args += " -DENABLE_TESTS=OFF"

        if self.no_colour():
            cmake_args += " -DECBUILD_NO_COLOUR=ON"

        cmake_args += self.cmake_args()

        mkdir_p(build_dir)

        arch = self.arch()
        if arch:
            print("Detected architecture " + arch)
            arch_dir = path.dirname(arch)
            for f in listdir(arch_dir):
                symlink_force(arch_dir + "/" + f, build_dir + "/" + f)
        else:
            with open(build_dir + "/env.sh", "w") as env:
                env.write("# Empty environment\n")

        mappings = dict(
            bundle_name=self.bundle().name(),
            src_dir=src_dir,
            install_dir=install_dir,
            build_type=self.build_type(),
            cmake_args=cmake_args,
            build_file=self.backend().file(),
            rerun_cmake_if_needed=self.backend().rerun_cmake_if_needed(),
            build=build,
            install=self.backend().install(self.threads()),
        )
        scripts = [
            ("clean.sh", clean_sh),
            ("configure.sh", configure_sh),
            ("build.sh", build_sh),
            ("install.sh", install_sh),
        ]
        for script in scripts:
            script_path = build_dir + "/" + script[0]
            with open(script_path, "w") as scriptfile:
                scriptfile.write(script[1].safe_substitute(mappings))
            chmod(script_path, 0o755)

    def backup_scripts(build):
        backup_dir = None
        build_dir = build.build_dir()

        if path.isdir(build_dir):
            backup = path.isfile(build_dir + "/build.sh")
            if backup:
                from datetime import datetime

                date = datetime.now().strftime("%Y-%m-%d.%H:%M:%S")
                backup_dir = build_dir + "/backup." + date
                mkdir_p(backup_dir)
                files = ["clean.sh", "configure.sh", "build.sh", "install.sh", "env.sh"]
                for f in files:
                    if path.isfile(build_dir + "/" + f):
                        copyfile(build_dir + "/" + f, backup_dir + "/" + f)
                    if path.islink(build_dir + "/" + f):
                        copyfile(readlink(build_dir + "/" + f), backup_dir + "/" + f)

        return backup_dir

    def build(self, **kwargs):
        """
        Invoke the bundle build according to stored arguments.
        """
        build_dir = self.build_dir()
        clean_sh = build_dir + "/clean.sh"
        configure_sh = build_dir + "/configure.sh"
        build_sh = build_dir + "/build.sh"
        install_sh = build_dir + "/install.sh"

        backup_dir = self.backup_scripts()
        self.create_scripts()

        header("\nCreated build scripts in build-dir:")
        print("    " + build_dir)

        if backup_dir:
            header("\nNote: Existing build scripts have been copied to:")
            print("    " + backup_dir)

        def print_file(filepath):
            with open(filepath, "r") as f:
                for line in f.readlines():
                    print("    " + line.rstrip())
                print("")

        print("")
        header("To configure:")
        print("    " + configure_sh + "\n")

        header("To configure and build:")
        print("    " + build_sh + "\n")

        header("To configure, build and install:")
        print("    " + install_sh + "\n")

        totaltimer = Timer()

        timers = []
        if self.config["clean"]:
            command = [clean_sh]
            print("+ " + " ".join(command))
            if not self.config["dryrun"]:
                try:
                    print(command)
                    check_call(command)
                except CalledProcessError:
                    error(
                        "ERROR: Command "
                        + " ".join(command)
                        + " failed from directory \n"
                        + getcwd()
                    )
                    raise RuntimeError()
            else:
                print_file(clean_sh)

        command = [configure_sh]
        if not self.config["reconfigure"]:
            command.append("--when-needed")
        print("+ " + " ".join(command))
        if not self.config["dryrun"]:
            timer = Timer()
            try:
                check_call(command)
                elapsed = timer.elapsed_str()
                success("Time elapsed for configure: %s\n" % elapsed)
                timers.append(("configure", elapsed))
                configured = True
            except CalledProcessError:
                error(
                    "ERROR: Command "
                    + " ".join(command)
                    + " failed from directory \n"
                    + getcwd()
                )
                error(
                    "\nTime elapsed for failed configuration: %s\n"
                    % timer.elapsed_str()
                )
                raise RuntimeError()
        else:
            print_file(configure_sh)

        command = [build_sh, "--without-configure"]
        print("+ " + " ".join(command))
        if not self.config["dryrun"]:
            timer = Timer()
            try:
                check_call(command)
                elapsed = timer.elapsed_str()
                success("Time elapsed for build: %s\n" % elapsed)
                timers.append(("build", elapsed))
            except CalledProcessError:
                error(
                    "ERROR: Command "
                    + " ".join(command)
                    + " failed in directory \n"
                    + getcwd()
                )
                error("\nTime elapsed for failed build: %s\n" % timer.elapsed_str())
                raise RuntimeError()
        else:
            print_file(build_sh)

        installed = False
        if self.config["install"]:
            command = [install_sh, "--fast"]
            print("+ " + " ".join(command))
            if not self.config["dryrun"]:
                timer = Timer()
                try:
                    check_call(command)
                    elapsed = timer.elapsed_str()
                    success("Time elapsed for install: %s\n" % elapsed)
                    timers.append(("install", elapsed))
                    installed = True

                except CalledProcessError:
                    error(
                        "ERROR: Command "
                        + " ".join(command)
                        + " failed in directory \n"
                        + getcwd()
                    )
                    error(
                        "\nTime elapsed for failed install: %s\n" % timer.elapsed_str()
                    )
                    raise RuntimeError()
            else:
                print_file(install_sh)

        if not self.config["dryrun"]:
            actions = ""
            if configured and not installed:
                actions += "configure and "
            if configured and installed:
                actions += "configure, "
            actions += "build "
            if installed:
                actions += "and install"

            header(
                "Total time elapsed to " + actions + ": %s\n" % totaltimer.elapsed_str()
            )
            for t in timers:
                print("    - " + "{: <10}".format(t[0]) + "   " + t[1])

            if not installed:
                header("\nTo install:")
                print("    " + install_sh + " --fast\n")

            if not self.config["without_tests"]:
                header("\nTo test:")
                print("    ( cd " + build_dir + "; . env.sh; ctest )\n")
