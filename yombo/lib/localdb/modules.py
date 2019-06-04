# Import python libraries

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.lib.localdb import Modules, ModulesView, ModuleCommits, ModuleInstalled, ModuleRoutingView


class DB_Modules(object):

    @inlineCallbacks
    def get_modules(self, get_all=False):
        if get_all is False:
            records = yield Modules.find(where=["status = ? OR status = ?", 1, 0], orderby="label ASC")
        else:
            records = yield Modules.find(orderby="label ASC")
        return records

    @inlineCallbacks
    def get_modules_view(self, get_all=False, where=None):
        if where is not None:
            records = yield Modules.find(where=where)
        elif get_all is False:
            records = yield ModulesView.find(where=["status = ?", 1])
        else:
            records = yield ModulesView.find(orderby="label ASC")
        return records

    @inlineCallbacks
    def get_module_commits(self, module_id, branch, approved=None, aslist=None):
        print(f"get_module_commits: module_id={module_id}, branch={branch}, aslist={aslist}")
        if approved is None:
            records = yield ModuleCommits.find(where=["module_id = ? and branch = ?", module_id, branch],
                                               group="module_id, branch", orderby="id DESC"
                                               )
        else:
            records = yield ModuleCommits.find(where=["module_id = ? and branch = ? and approved = ?",
                                                      module_id, branch, approved],
                                               group="module_id, branch", orderby="id DESC"
                                               )
        if aslist is True:
            commits = []
            for record in records:
                commits.append(record.commit)
            return commits
        return records

    @inlineCallbacks
    def install_module(self, data):
        results = yield ModuleInstalled(module_id=data["module_id"],
                                        installed_branch=data["installed_branch"],
                                        installed_commit=data["installed_commit"],
                                        install_at=data["install_at"],
                                        last_check_at=data["last_check_at"],
                                        ).save()
        return results

    @inlineCallbacks
    def get_module_routing(self, where=None):
        """
        Used to load a list of deviceType routing information.

        Called by: lib.Modules::load_data

        :param where: Optional - Can be used to append a where statement
        :type returnType: string
        :return: Modules used for routing device message packets
        :rtype: list
        """
        records = yield ModuleRoutingView.all()
        return records

    @inlineCallbacks
    def set_module_status(self, module_id, status):
        """
        Used to set the status of a module. Shouldn't be used by developers.
        Used to load a list of deviceType routing information.

        Called by: lib.Modules::enable, disable, and delete

        :param module_id: Id of the module to updates
        :type module_id: string
        :param status: Value to set the status field.
        :type status: int
        """

        modules = yield Modules.find(where=["id = ?", module_id])
        if modules is None:
            return None
        module = modules[0]
        module.status = status
        results = yield module.save()
        return results