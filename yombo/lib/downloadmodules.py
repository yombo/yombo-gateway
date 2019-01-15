# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
Responsible for downloading and installing any modules as requested by the configuration. The modules
are downloaded directly from the git repository. The latest approved commit will be set as active and will be
validated during startup.

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
    and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. note::

  * For library documentation, see: `Download Modules @ Library Documentation <https://yombo.net/docs/libraries/download_modules>`_

At startup, it checks if a module should be downloaded / updated. Here is a summary of steps:

Download Steps:

1) List modules set to be installed.
2a) Any new modules are downloaded from the git source.
2b) Any existing modules are pulled and updated (if a new version exists).
3) Load the module


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/downloadmodules.html>`_
"""
# Import python libraries
import git
import os
from time import time

# Import twisted libraries
from twisted.internet import threads, defer
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import MODULE_API_VERSION
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger("library.downloadmodules")


class DownloadModules(YomboLibrary):
    """
    Handle downloading and updating of modules.

    Checks to make sure basic configurations are valid and other pre-startup
    operations have completed before continuing.  The class will generate
    twisted deferred and will hold up the loading process until all the
    modules have been downloaded.
    
    A semaphore is used to allow processing and downloading of 3 modules at
    a time.
    """
    MAX_DOWNLOAD_CONCURRENT = 3  # config: misc:downloadmodulesconcurrent

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo download modules library"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Gets the library setup and preconfigures some items.  Sets up the
        semaphore for queuing downloads.
        """
        self.current_api = f"api_{MODULE_API_VERSION}"
        self.maxDownloadConcurrent = self._Configs.get("misc", "downloadmodulesconcurrent", self.MAX_DOWNLOAD_CONCURRENT)
        self.download_path = self._Atoms.get("app_dir") + "/yombo/modules/"
        self.mysemaphore = defer.DeferredSemaphore(self.maxDownloadConcurrent)  #used to queue deferreds
        self.modules = {}
        yield self.check_modules()

    # @inlineCallbacks
    # def _load_(self, **kwargs):
    #     """
    #     Prepare the cloudfront download location, and :func:`checkModules`
    #     to see if any modules need to be downloaded.
    #     """

    @inlineCallbacks
    def check_modules(self, download=None, anytime=None):
        """
        Check if modules need updating and how many commits they are behind.

        If the module isn't downloaded already, it will download regardless of the download argument.

        If download is True, then they will also be downloaded or updated.

        :param download: If true, will download the modules
        :param anytime: If true, check all modules, not just modules that weren't checked recently.
        """
        if download is None:
            download = True
        if anytime is None:
            anytime = True

        modules = yield self._LocalDB.get_modules_view()
        last_check_time = int(time()) - 3600 * 2

        for module in modules:
            if module.id not in self.modules:
                self.modules[module.id] = {
                    "installed_commit": None,
                    "latest_commit": None,
                    "commits_behind": None,
                    "last_check_at": module.last_check_at,
                }
            if anytime is False:
                if module.last_check_at < last_check_time:
                    continue

        if anytime is False:  # remove any modules that don't need to be checked yet.
            modules = [x for x in modules if not x.last_check_at < last_check_time]

        if len(modules) == 0:
            logger.info("No modules need to be downloaded or updated.", count=len(modules))
            return None

        logger.info("Checking {count} modules for downloads and updates.", count=len(modules))
        for module in modules:
            machine_label = module.machine_label.lower()
            module_id = module.id

            if module.install_branch == "system":
                yield self.touch_database(module, "system", "system")
                continue

            module_path = self.download_path + f"{machine_label}/"
            if os.path.exists(module_path + ".freeze") or module.install_branch == "local":
                logger.info("Skipping download module '{label}'. Reason: .freeze file found", label=machine_label)
                continue

            if not os.path.exists(module_path):
                try:
                    yield self.git_clone(self.download_path, machine_label, module.git_link)
                except git.GitCommandError as e:
                    logger.warn("Unable to clone module '{label}', reason: {e}", label=machine_label, e=e)
                    continue

            repo = git.Repo(module_path)
            self.modules[module_id]["installed_commit"] = repo.head.object.hexsha

            local_branches = self.local_branches(repo)

            try:
                remote_branches = yield self.git_fetch(repo)
            except git.GitCommandError as e:
                logger.warn("Unable to git fetch for module '{label}', reason: {e}",
                            label=machine_label, e=e)
                continue

            # select which module branch to use.  Use api_MODULE_API_VERSION if install_version != "develop"
            if module.install_branch in ("dev", "develop", "development"):
                install_branch = "master"
            else:
                if self.current_api in local_branches:
                    install_branch = self.current_api
                else:
                    if self.current_api in remote_branches:
                        install_branch = self.current_api
                    else:
                        install_branch = "master"

            self.modules[module_id]["last_check_at"] = int(time())

            logger.info("DL Module ({label}): Install branch: {branch}", label=machine_label, branch=install_branch)
            try:
                yield self.git_checkout(repo, install_branch)
            except git.GitCommandError as e:
                logger.warn("Unable to checkout branch for module '{label}', reason: {e}", label=machine_label, e=e)
                return

            commits_behind = len(list(repo.iter_commits(f"{install_branch}..origin/{install_branch}")))
            logger.warn("Module '{label}' is behind master: {commits_behind}",
                        label=module.label, commits_behind=commits_behind)
            self.modules[module.id]['commits_behind'] = commits_behind

            repo = git.Repo(module_path)  # some sort of bug after all the above processes.

            if commits_behind > 0 and download is True:
                try:
                    yield self.git_pull(repo, install_branch)
                except git.GitCommandError as e:
                    logger.warn("Unable to pull branch for module '{label}', reason: {e}", label=machine_label, e=e)
                    return

            self.modules[module.id]['current_commit'] = repo.head.object.hexsha

            if module.require_approved == 0:
                continue
            else:
                installed_hash = yield self.find_approved_commit(module_id, install_branch, repo)
                if installed_hash is False:
                    self._Modules.disabled_modules[module_id] = {"reason": "No approved commit found."}
                    logger.warn("Disabled module '{label}'. Reason: No approved commit found.", label=machine_label)
            yield self.update_database(module, install_branch, repo.head.object.hexsha)

    def get_repo(self, directory):
        """
        Get a git object represting the git repository.

        :param directory:
        :return:
        """
        return git.Repo(directory)

    @inlineCallbacks
    def git_clone(self, parent, folder, source):
        """
        Clone a git repository into the path/folder from the given source.

        :param parent:
        :param folder:
        :param source:
        :return:
        """
        def do_git_clone():
            git.Git(parent).clone(source, folder)

        yield threads.deferToThread(do_git_clone)

    def local_branches(self, repo):
        """
        Get current local branches as a list.

        :param repo:
        :return:
        """
        branches = []
        for head in repo.heads:
            if head.name not in branches:
                branches.append(head.name)
        return branches

    @inlineCallbacks
    def git_fetch(self, repo, remote=None):
        """
        AKA: remote_branches

        Does a fetch against the remote (origin) and returns a dictionary of branches, where the
        key is the branch name. Each data item for the dictionary is the FetchInfo item.

        After calling this function, the repo will be updated so commits behind can also be counted.

        :param repo:
        :param remote:
        :return:
        """
        def do_git_fetch(a_remote):
            results = a_remote.fetch()
            branches = {}
            for item in results:
                branches[item.name.split('/')[1]] = item
            return branches

        if remote is None:
            remote = repo.remote()
        items = yield threads.deferToThread(do_git_fetch, remote)
        return items

    @inlineCallbacks
    def pull_branches(self, repo):
        """
        Pulls all branches from the remote, but only if they are: master or is the current module api version.

        :param repo:
        :return:
        """
        def do_git_checkout(repository, name1, name2):
            repository.git.checkout('-B', name1, name2)

        branches = []
        for head in repo.heads:
            if head.name not in branches:
                branches.append(head.name)

        remote_branches = yield self.git_fetch(repo)

        for branch, item in remote_branches.items():
            if branch in ("master",) or branch == self.current_api:
                if branch not in branches:
                    yield threads.deferToThread(do_git_checkout, repo,
                                                branch, item.name)
                self.git_pull(repo)

    @inlineCallbacks
    def git_checkout(self, repo, branch):
        def do_git_checkout(repository, the_branch):
            repository.git.checkout(the_branch)

        yield threads.deferToThread(do_git_checkout, repo, branch)

    @inlineCallbacks
    def git_pull(self, repo, branch=None):
        def do_git_pull(repository):
            repository.remote().pull()

        if branch is not None:
            yield self.git_checkout(repo, branch)
        yield threads.deferToThread(do_git_pull, repo)


    @inlineCallbacks
    def find_approved_commit(self, module_id, branch, repo):
        appoved_commits = yield self._LocalDB.get_module_commits(module_id, branch, approved=1, aslist=True)
        for commit in repo.iter_commits(branch):
            test_hexsha = commit.hexsha
            if test_hexsha in appoved_commits:
                if repo.head.object.hexsha == test_hexsha:  # we're done
                    return test_hexsha
                else:
                    yield self.git_checkout(repo, test_hexsha)
        return False

    @inlineCallbacks
    def update_database(self, module, branch, commit):
        """
        Update the database to reflect installed module data.

        :param module_id:
        :param branch:
        :param hash:
        :return:
        """
        if module.install_at is None:
            self._LocalDB.install_module(
                {"module_id": module.id,
                 "installed_branch": branch,
                 "installed_commit": commit,
                 "last_check_at": int(time()),
                 "install_at": int(time())
                 })
        else:
            ModuleInstalled = self._LocalDB.get_model_class("ModuleInstalled")
            module_installed = yield ModuleInstalled.find(where=["module_id = ?", module.id], limit=1)
            module_installed.installed_branch = branch
            module_installed.installed_commit = commit
            module_installed.last_check_at = int(time())
            module_installed.save()

    @inlineCallbacks
    def touch_database(self, module, branch, commit):
        """
        Update the database to reflect installed module data.

        :param module_id:
        :param branch:
        :param hash:
        :return:
        """
        if module.install_at is None:
            self._LocalDB.install_module(
                {"module_id": module.id,
                 "installed_branch": branch,
                 "installed_commit": commit,
                 "last_check_at": int(time()),
                 "install_at": int(time())
                 })
        else:
            ModuleInstalled = self._LocalDB.get_model_class("ModuleInstalled")
            module_installed = yield ModuleInstalled.find(where=["module_id = ?", module.id], limit=1)
            module_installed.last_check_at = int(time())
            module_installed.save()
