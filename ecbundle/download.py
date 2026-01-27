# (C) Copyright 2020- ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

import re
from os import getcwd, makedirs, path
from subprocess import check_call
from hashlib import md5

from .bundle import Bundle
from .data import Data
from .logging import colors, debug, error, header, success, warning
from .util import cpu_count, fullpath, symlink_force


class GitURL(object):
    """
    Detect host by given URL
    """

    @classmethod
    def parse(cls, url):
        known_git_hosts = [
            {
                "regex": r"(git.ecmwf.int/scm/)(.+)/(.+)(\.git)?",
                "host": "git.ecmwf.int",
                "remote": 2,
                "project": 3,
            },
            {
                "regex": r"(git.ecmwf.int:7999/)(.+)/(.+)(\.git)?",
                "host": "git.ecmwf.int",
                "remote": 2,
                "project": 3,
            },
            {
                "regex": r"(git.ecmwf.int[:/])(.+)/(.+)(\.git)?",
                "host": "git.ecmwf.int",
                "remote": 2,
                "project": 3,
            },
            {
                "regex": r"(github.com[:/])(.+)/(.+)(\.git)?",
                "host": "github.com",
                "remote": 2,
                "project": 3,
            },
        ]
        for entry in known_git_hosts:
            m = re.search(entry["regex"], url)
            if m:
                host = entry["host"]
                remote = m.group(entry["remote"])
                project = m.group(entry["project"])
                return host + ":" + remote + "/" + project
        return url


ECMWF_BITBUCKET_URL = "ssh://git@git.ecmwf.int"
GITHUB_URL = "https://github.com"


class BundleDownloader(object):
    def __init__(self, **kwargs):
        self.config = kwargs
        # Option to inject a custom ``Git`` object for testing purposes
        from .git import Git

        self.git = kwargs.get("git", Git)

        if "no_colour" in kwargs:
            if kwargs["no_colour"]:
                colors.disable()
            else:
                colors.enable()

    def get(self, key, default=None):
        return self.config.get(key, default)

    def dryrun(self):
        if self.get("dryrun"):
            return self.get("dryrun")
        if self.get("dry_run"):
            return self.get("dry_run")
        return False

    def threads(self):
        t = self.get("threads")
        if t == 0:
            return cpu_count()
        else:
            return t

    def shallow(self):
        return self.get("shallow", False)

    def update(self):
        return self.get("update") or self.forced_update()

    def forced_update(self):
        return self.get("forced_update")

    def src_dir(self):
        return fullpath(self.get("src_dir", "source"))

    def github_token(self):
        return self.get("github_token")

    def bundle(self):
        bundle_path = fullpath(self.get("bundle", None))
        if bundle_path:
            if path.isfile(bundle_path):
                return Bundle(bundle_path, env=True)
            if not path.isdir(bundle_path):
                error(
                    "ERROR: --bundle argument is not a valid bundle directory or file path"
                )
                return None

        filedirs = [bundle_path]
        if getcwd() != bundle_path:
            filedirs.append(getcwd())
        for d in filedirs:
            bundle_path = "/".join([d, "bundle.yml"])
            if path.isfile(bundle_path):
                return Bundle(bundle_path)
        error("ERROR: No bundle file could be found")
        error("       Searched in " + ", ".join(filedirs))
        return None

    def download(self):
        dryrun = self.dryrun()

        downloaded_packages = list()
        skipped_packages = list()
        skipped_optional_packages = list()

        class GitPackage:
            def __init__(self, project, src_dir=None):
                self.url = None
                self.name = project.name()
                self.version = str(project.version())
                self.optional = project.optional()
                if not self.version:
                    error("version not given for package " + self.name)
                self.submodules = project.submodules()

                if project.git():
                    self.url = project.git()
                    self.url = self.url.replace("${BITBUCKET}", ECMWF_BITBUCKET_URL)
                    self.url = self.url.replace("${GITHUB}", GITHUB_URL)
                else:
                    error("git not given for package " + self.name)

                if self.url.startswith("~/"):
                    error(
                        "Given git url %s for project %s is ambiguous as it does not specify "
                        "the user. Please ammend." % (self.url, self.name)
                    )
                    raise RuntimeError()

                elif self.url.startswith("~"):
                    self.url = path.expanduser(self.url)
                self._set_remote(project, src_dir=src_dir)

            def _set_remote(self, project, src_dir=None):
                from .git import Git
                remote = project.remote(default=None)
                if remote is None:
                    if src_dir is None or not path.exists(src_dir):
                        remote = 'origin'
                    else:
                        # look for an existing remote with requested url
                        for remote_name, remote_url in Git.remotes(src_dir).items():
                            if remote_url == self.url:
                                remote = remote_name
                                break
                        if remote is None:
                            # not found: use a bijective alias to url
                            remote = md5(self.url.encode('utf-8')).hexdigest()
                self.remote_str = remote
                self.remote = self.remote_str.replace("~", "")

        def download_one_project(pkg):
            download_dir = self.src_dir()
            src_dir = path.join(download_dir, pkg.name)
            try:
                if path.exists(src_dir):
                    if self.update():
                        header(
                            "Checkout project %s @ %s"
                            % (GitURL.parse(pkg.url), pkg.version)
                        )
                        if self.git.is_dirty(src_dir, dryrun):
                            error(
                                "ERROR: %s sources are in dirty state at %s"
                                % (pkg.name, src_dir)
                            )
                            raise RuntimeError()

                        if not self.git.is_remote(src_dir, pkg.remote, dryrun):
                            warning(
                                "WARNING: %s is a new remote for repository %s."
                                " Be careful what you wish for! (check following lines)"
                                % (pkg.remote_str, pkg.name)
                            )
                            self.git.remote_add(src_dir, pkg.remote, pkg.url, dryrun)

                        remote_url = self.git.remote_url(src_dir, pkg.remote, dryrun)
                        if not remote_url == pkg.url:
                            error(
                                "ERROR: repository %s already defined a remote '%s' with url %s. \n"
                                "Please specify a 'remote' in the bundle with a different name than '%s'"
                                "to match the requested url %s."
                                % (
                                    pkg.name,
                                    pkg.remote,
                                    remote_url,
                                    pkg.remote,
                                    pkg.url,
                                )
                            )
                            raise RuntimeError()

                        if self.git.is_branch(src_dir, pkg.version, dryrun):
                            debug(pkg.version + " is branch")
                            upstream = self.git.branch_upstream(
                                src_dir, pkg.version, dryrun
                            )
                            if not upstream:
                                error(
                                    'ERROR: branch "'
                                    + pkg.version
                                    + '" has no upstream'
                                )
                                raise RuntimeError()
                            if upstream == pkg.remote + "/" + pkg.version:
                                self.git.checkout(src_dir, pkg.version, dryrun)
                                if self.forced_update():
                                    self.git.fetch(
                                        src_dir, pkg.remote, pkg.version, dryrun
                                    )
                                    self.git.reset_hard(
                                        src_dir, pkg.remote, pkg.version, dryrun
                                    )
                                else:
                                    self.git.pull(
                                        src_dir, pkg.remote, pkg.version, dryrun
                                    )
                            else:
                                error(
                                    "ERROR: Branch %s was already tracking "
                                    "%s. Manual intervention needed."
                                    % (pkg.version, upstream)
                                )
                                raise RuntimeError()

                        elif self.git.is_tag(src_dir, pkg.version, dryrun):
                            debug(pkg.version + " is tag")
                            self.git.checkout(src_dir, pkg.version, dryrun)

                        elif self.git.is_commit(src_dir, pkg.version, dryrun):
                            debug(pkg.version + " is commit")
                            self.git.checkout(src_dir, pkg.version, dryrun)

                        else:  # Not present yet!
                            debug(pkg.version + " is yet unknown")
                            self.git.fetch(src_dir, pkg.remote, pkg.version, dryrun)
                            self.git.checkout_new(
                                src_dir, pkg.remote, pkg.version, dryrun
                            )

                else:
                    header("Cloning project %s at version %s" % (pkg.name, pkg.version))
                    clone_url = pkg.url
                    if (
                        GitURL.parse(pkg.url).startswith("github.com")
                        and self.github_token()
                        and pkg.url.startswith("https://")
                    ):
                        clone_url = pkg.url.replace(
                            "https://", f"https://{self.github_token()}@"
                        )
                    self.git.clone(
                        clone_url,
                        src_dir,
                        pkg.version,
                        pkg.remote,
                        dryrun,
                        self.shallow(),
                    )

                if pkg.submodules:
                    self.git.submodule_init(src_dir, dryrun)

                sha1 = self.git.commit_id(src_dir, dryrun)

                downloaded_packages.append((GitURL.parse(pkg.url), pkg.version, sha1))

            except RuntimeError:
                if pkg.optional:
                    debug("Could not download or update optional project %s" % pkg.name)
                    skipped_optional_packages.append(pkg.name)
                    return 0
                error("ERROR: Could not download or update %s ..." % (pkg.name,))
                skipped_packages.append(pkg.name)
                return 1
            return 0

        def download_projects(packages, download_dir):
            from multiprocessing.dummy import Pool as ThreadPool

            threads = self.threads()
            errors = []

            pool = ThreadPool(threads)
            errors = pool.map(download_one_project, packages)
            pool.close()
            pool.join()

            #            for pkg in packages:
            #                errors.append(download_one_project(pkg))

            nb_errors = sum(errors)
            if nb_errors != 0:
                error("Errors encountered: " + str(nb_errors))
                raise RuntimeError("Download failed with %d errors" % (nb_errors,))

        def download_data(data_packages, download_dir):
            for data in data_packages:
                header("Downloading data " + data.name())
                filename = path.basename(data.url())
                do_download = True
                if path.exists(download_dir + "/" + filename):
                    do_download = False
                if do_download:
                    command = ["curl", data.url(), "-o", download_dir + "/" + filename]
                    print("+ " + " ".join(command))
                    check_call(command)
                header("Extracting data " + data.name())
                datadir = download_dir + "/" + data.name()
                if not path.exists(datadir):
                    makedirs(datadir)
                command = ["tar", "xzf", download_dir + "/" + filename, "-C", datadir]
                print("+ " + " ".join(command))
                check_call(command)

        download_dir = self.src_dir()

        git_projects = list()
        symlink_projects = list()
        data = list()

        bundle = self.bundle()
        if not bundle:
            return 1

        errcode = 0
        success("\nDownloading bundle with " + str(self.threads()) + " threads for ")
        header("    " + bundle.file())

        for project in bundle.projects():
            if project.dir():
                symlink_projects.append(project)
            else:
                src_dir = path.join(download_dir, project.name())
                git_projects.append(GitPackage(project, src_dir=src_dir))

        for package in bundle.data():
            data.append(Data(**package.config))

        try:
            download_projects(git_projects, download_dir)
            download_data(data, download_dir)
        except RuntimeError:
            errcode = 1

        if len(downloaded_packages) and not dryrun:
            header("\nFollowing projects are checked out in " + self.src_dir() + ":")
            for url, version, sha1 in downloaded_packages:
                print("    - " + url + " (" + version + ")  [" + sha1 + "]")

        if len(symlink_projects):
            header("\nFollowing projects are symlinked in " + self.src_dir() + ":")

            for project in symlink_projects:
                linkname = self.src_dir() + "/" + project.name()
                # Precedence for targetname:
                #  1. absolute path
                #  2. relative to the bundle file
                #  3. relative to the source directory
                targetname = project.dir()
                if not path.isabs(targetname):
                    targetname = path.join(path.dirname(bundle.file()), project.dir())
                    if not path.exists(targetname):
                        targetname = path.join(self.src_dir(), project.dir())

                if not path.exists(targetname):
                    error(
                        "A directory [%s] is provided for project [%s] but it does not exist."
                        % (targetname, project.name())
                    )
                    errcode = 1
                    continue

                if path.exists(linkname) and not path.islink(linkname):
                    error(
                        "There already exists a directory at %s "
                        "that would be overwritten by a symlink to [%s] .\n"
                        "To avoid accidental deletion, it is left up to you to delete the "
                        "existing directory." % (linkname, targetname)
                    )
                    errcode = 1
                    continue

                symlink_force(targetname, linkname)

                print("    - " + project.name() + " (" + project.dir() + ")")

        if len(skipped_optional_packages):
            header("\nFollowing projects failed to download but are marked optional:")
            for pkg in skipped_optional_packages:
                print("    - " + pkg)

        if len(skipped_packages):
            error("\nFollowing projects are skipped due to errors encountered:")
            for pkg in skipped_packages:
                print("    - " + pkg)

        return errcode
