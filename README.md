# ecbundle - Bundle management tool for CMake projects

[![license](https://img.shields.io/github/license/ecmwf/ecbundle)](https://www.apache.org/licenses/LICENSE-2.0.html)
[![build](https://github.com/ecmwf/ecbundle/actions/workflows/build.yml/badge.svg)](https://github.com/ecmwf/ecbundle/actions/workflows/build.yml)
[![codecov](https://codecov.io/gh/ecmwf/ecbundle/branch/main/graph/badge.svg?token=1DRF2I4INS)](https://codecov.io/gh/ecmwf/ecbundle)


ecbundle is a set of python tools that help in configuring, building and installing packages in a consistent manner to build a standalone program or service. ecbundle-compatible packages are required to be nestable CMake projects.


## What is a Bundle?

A bundle in this context has the meaning of a single CMake project with other CMake projects added as subdirectories.
A typical directory structure could be:

    bundle/
        CMakeLists.txt
        project1/
            CMakeLists.txt
            ...
        project2/
            CMakeLists.txt
            ...

The content of file `bundle/CMakeLists.txt` defines a new "bundle" CMake project and most simply contains

    cmake_minimum_required( VERSION 3.12 FATAL_ERROR )
    project( bundle )
    add_subdirectory( project1 )
    add_subdirectory( project2 )

An installed bundle is expected to be used as a standalone service, program, or set of tools similar to a macOS bundle.
It is not expected that the libraries installed as part of the bundle, themselves will be linked to by external downstream executables, though it is technically possible.

#### Bundle Pros:

- Easy to install:
  - Only one large project to configure/build/install and guarantee that all packages are available.
  - All packages are compiled in compatible manner with custom configuration options specifically for the bundle application: with/without MPI, with/without OpenMP, with/without Fortran support, ...
- Easy to develop for multiple packages in the software stack:
  - CMake holds a dependency graph between the packages.
  - Each package does not need to be installed separately
  - We can develop working with the build-tree only
  - Editing a dependency source-file guarantees to trigger recompilation of code that uses it (and not more) in downstream packages.

#### Bundle Cons:

- Not possible to use different build-type for each package
- Configuration/compilation may possibly take much longer than really needed if you only develop in the most downstream project, and never need to edit any dependency package.


## What does ecbundle do?

- Parses a YAML file (`bundle.yml`) which describes all packages that make up the bundle, and important configuration options.
- Downloads all the packages via `git` in a bundle `source` directory.
- Creates a new bundle CMake project that adds the packages as nested projects.
- Configures, compiles, and (optionally) installs the bundle CMake project.
- Hooks are available to pass architecture specific toolchains and environment variables before configuring and building the bundle (e.g. `module load ...`)


## Installation of ecbundle

#### Option 1:  using pip

```bash
pip3 install git+https://github.com/ecmwf/ecbundle
```

This can also be done within a python virtual environment

```bash
python3 -m venv ecbundle_venv
source ecbundle_venv/bin/activate
pip install git+https://github.com/ecmwf/ecbundle
```

#### Option 2: from source

```bash
git clone https://github.com/ecmwf/ecbundle
export PATH=$(pwd)/ecbundle/bin:${PATH}
```


## Using ecbundle

#### 1.  Create a `bundle.yml` file in a new directory my_bundle
An example bundle to build the ECMWF atlas project with its minimal dependencies:
```yaml
---
name    : my_bundle                    # The name given to the bundle
version : 2022.1                       # A version given to the bundle
cmake   : ENABLE_OMP=ON                # Globally enable OpenMP by default

projects :

  - ecbuild :
      git     : https://github.com/ecmwf/ecbuild
      version : 3.6.5
      bundle  : false                # (do not build/install, only download)

  - eckit :
      git     : https://github.com/ecmwf/eckit
      version : 1.18.2
      cmake   : >                    # Turn off some unnecessary eckit features
                ENABLE_ECKIT_CMD=OFF
                ENABLE_ECKIT_SQL=OFF

  - fckit :
      git     : https://github.com/ecmwf/fckit
      version : 0.9.5
      require : eckit

  - atlas :
      git     : https://github.com/ecmwf/atlas
      version : 0.27.0
      require : eckit fckit

options:

  - with-mpi :
      help  : Enable MPI [ON|OFF]
      cmake : ENABLE_MPI={{value}}

  - with-omp :
      help  : Enable OpenMP [ON|OFF]
      cmake : ENABLE_OMP={{value}}

  - with-fortran :
      help  : Disable Fortran API
      cmake : ATLAS_ENABLE_FORTRAN={{value}} BUILD_fckit={{value}}
```
The options section is provided to give users easy access to the most important configuration options specifically for this bundle.
In this example we want to give users easy control to build the Fortran parts and OpenMP control.


#### 2. Create the bundle project
With `ecbundle` available in the PATH, we can go into the `my_bundle` directory and execute

```bash
ecbundle create
```

This will download all the projects listed in the `bundle.yml` file into a subdirectory `source`.
Additionally a file `source/CMakeLists.txt` is created that defines the bundle project.

#### 3. Build/Install the bundle project

Simply execute

```bash
ecbundle build
```

There are various build options that are also shown when executing

```bash
ecbundle build --help
```

Most important options:

- `--prefix=<install-prefix>` : location to install bundle
- `--build-type=<build-type>` : Any of [Debug|Release|RelWithDebInfo] or other available build types
- `--ninja` : Use "Ninja" instead of "Unix Makefiles" as the underlying build system

The "options" section in the `bundle.yml` file is parsed as well, which gives users easy access to common configuration options.
Extra CMake options can be passed as well with argument
`--cmake="VAR1=VALUE1 VAR2=VALUE2"`.

Various build configurations can easily coexist by specifying different build-dirs with the `--build-dir=<build-dir>` argument.

Adding the `--install` argument also installs the project, by default in a `install` directory parallel to the `source` directory, but can also be controlled with the `--prefix` argument.

A configure/build/install log is also installed in
```bash
<prefix>/share/<bundle-name>/build.log
```

##### Specifying an architecture specific environment and toolchain

ecbundle provides hooks to store platform and architecture specific configurations.
As a user you then need to specify the `--arch=<path-to-arch-dir>` argument which points to a directory containing a file named `env.sh`.

The `env.sh` file gets "sourced" before configuring and building.
It is to be used to setup the environment:
- Modules to be loaded if applicable (e.g. `module load intel/2021.4`)
- Set environment variables for compilers (`CC`, `CXX`, `FC`)
- Set environment variables to find third-party packages, if not set by modules (`MPI_HOME`, `FFTW_DIR`, ...)

Optionally there can also be three CMake specific files in this directory to tweak configuration:
- `toolchain.cmake` : automatically configure CMake with this [cmake-toolchain]( https://cmake.org/cmake/help/latest/manual/cmake-toolchains.7.html), useful for e.g. cross compilation
- `init.cmake` : execute the content of this file after bundle project has been initialized but before any of the projects have been added
- `final.cmake` : execute the content of this file after all projects have been added

All the files in the `arch` directory are also automatically installed in
```bash
<prefix>/share/<bundle-name>/arch
```
This is useful to retrieve the environment, sometimes required to run the application correctly.


## Developer workflow

The `ecbundle build` command creates build-dir and will contain symbolic links to the files from the arch directory. Also four executable shell files are created:
- `configure.sh` : Perform the CMake configuration step with customized build options. `env.sh` is sourced internally.
- `build.sh` : Compile the bundle. `configure.sh` is called internally if needed.
- `install.sh`: Install the bundle. `build.sh` is called internally if needed.
- `clean.sh` : In the build-dir, remove all files except these four and the symbolic links to the files from the arch directory.

As a developer it is typically sufficient to execute
```bash
<path-to-build-dir>/build.sh
```
from any location, after editing source files to get a quick edit/compile/test turnover.

Testing can be done with `ctest`. It is sometimes required to source the `env.sh` to be able to correctly run the tests (e.g. having mpirun in the PATH or other modules loaded).
```
cd <path-to-build-dir>
source env.sh
ctest <ctest-arguments>
```

## Documentation

### 1. Bundle keywords

```yaml
---
name      : <name>                                 # 1.  [required] Name of bundle
version   : <major>[.<minor>[.<patch>[.<tweak>]]]  # 2.  [optional] Version of bundle (if not specified, use "0.0.0" )
languages : C CXX Fortran                          # 3.  [optional] Choice of languages to initialize bundle project. If not specified, the CMake default is "C CXX"
cmake     : <var1>=<val1> <var2>=<val2>            # 4.  [optional] Space separated list of cmake variables that will be encoded in created CMakeLists.txt

projects :                                         # 5.  [required] List of projects

  - <project> :                                    # 6.  [required] Name of project
      git      : <git-url>                         # 7.  [required] URL where git repository is hosted
      version  : <git-tag>|<git-branch>            # 8.  [required] Git branch or tag to checkout
      bundle   : false                             # 9.  [optional] Flag to only download project and not add as bundle

  - <project> :
      git      : <git-url>
      version  : <tag>|<branch>
      cmake    : <var1>=<val1> <var2>=<val2>       # 10. [optional] Space separated list of cmake variables that will be encoded in created CMakeLists.txt
      optional : true                              # 11. [optional] Flag to allow this project to fail download, e.g. with denied download permissions.

  - <project> :
      git      : <git-url>
      version  : <tag>|<branch>
      require  : <project1> <project2>             # 12. [optional] Make dependencies between projects available. Currently this is not used, but could be in the future.

  - <project> :
      dir      : <path-to-package>                 # 13. [required] Instead of "git", specify path to existing project. Absolute path or relative path to 'source' dir expected.
                                                   #     'version' is not required
  - <project> :
      git      : <git-url>
      version  : <tag>|<branch>
      subdir   : <subdir>                          # 14. [required] The project is not at the root of the git repository, but a subdirectory relative to the root.

options :                                          # 15. [optional] List of options

  - <option> :                                     # 16. [required] Name of option. This option will be enabled via `ecbundle build --<option>
      cmake : <var1>=<val1> <var2>=<val2>          # 17. [required] Space separated list of cmake variables that will be encoded in build-dir in `configure.sh`
      help : <help-string>                         # 18. [required] Description of option

  - <option> :                                     # 19. [required] Name of option.  This option will be modified with `ecbundle build --<option>=<value>
      cmake : <var1>={{value}}                     # 20. [required] Space separated list of cmake variables that will be encoded in build-dir in `configure.sh`
                                                   #                {{value}} is a placeholder for the command-line provided <value>
      help : <help-string>
```

### 2. Overriding bundle keywords with environment variables

It is possible to override some of the keywords in the bundle using environment variables.
In following listed variables `<BUNDLE-NAME>` and `<PROJECT-NAME>` are the uppercased bundle name and project name respectively with "-" replaced by "_".

- `<BUNDLE-NAME>_<PROJECT-NAME>_GIT`     : Override `git` keyword of a project (see #7)
- `<BUNDLE-NAME>_<PROJECT-NAME>_VERSION` : Override `version` keyword of a project (see #8)
- `<BUNDLE-NAME>_<PROJECT-NAME>_CMAKE`   : Override `cmake` keyword of a project (see #10)
- `<BUNDLE-NAME>_<PROJECT-NAME>_DIR`     : Override `dir` keyword of a project, and ignore the `git` and `version` keyword if present.

This may be useful to use in simple bash scripts without manipulating the yaml file directly.


Contributing
============

The main repository is hosted on GitHub, testing, bug reports and contributions are highly welcomed and appreciated:

https://github.com/ecmwf/ecbundle

Please see the [Contributing](CONTRIBUTING.rst) document for the best way to help.

Main contributors:

- Willem Deconinck - [ECMWF](https://ecmwf.int)
- Michael Lange - [ECMWF](https://ecmwf.int)

See also the [contributors](https://github.com/ecmwf/ecbundle/contributors) for a more complete list.


License
=======

Copyright 2020 European Centre for Medium-Range Weather Forecasts (ECMWF)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

In applying this licence, ECMWF does not waive the privileges and immunities
granted to it by virtue of its status as an intergovernmental organisation nor
does it submit to any jurisdiction.
