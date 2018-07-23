"""
Access Control List processing as part of the user permission system. Only one instance of the ACL
is used within the Yombo Gateway framework.

Resounce syntax:

* URI/URL: web:/api/v1/some_resource/here
* A method within the gateway: ygw:library.states.some_function
* MQTT: mqtt:/some/topic/or/another

"""
from yombo.core.exceptions import YomboWarning
from yombo.lib.users import Users

class AccessControlList(object):
    """
    A single access control list can contain multiple roles. Users are assigned to roles, not to access
    control lists.
    """

    def __init__(self, parent):
        """
        Setup an ACL instance.

        :param parent: A reference to the users library.
        """
        self._Parent: Users = parent
        self.permissions: dict[list] = {}

    # def add_rule(self, role, path, action, access):
    #     """
    #     Add a rule to the ACL
    #
    #     :param role: Role instance for this rule.
    #     :param path: A resource that is to be matched. devices:*, web:/url/path
    #     :param action: edit, view, delete...etc
    #     :param access: One of 'allow' or 'deny'
    #     """
    #     path = path.lower()
    #     action = action.lower()
    #     access = access.lower()
    #
    #     if access not in ('allow', 'deny'):
    #         raise YomboWarning('access must be one of: allow, deny')
    #
    #     permission = (role.label, path, action)
    #     if permission not in self.permissions[access]:
    #         self.permissions[access].append(permission)
    #
    # def delete_rule(self, role,  path, action, access):
    #     """
    #     Delete a rule from the current role
    #
    #     :param role: Role instance for this rule.
    #     :param path: A resource that is to be matched. devices:*, web:/url/path
    #     :param action: edit, view, delete...etc
    #     :param access: One of 'allow' or 'deny'
    #     """
    #     path = path.lower()
    #     action = action.lower()
    #     access = access.lower()
    #
    #     permission = (role.label, path, action)
    #     if permission in self.permissions[access]:
    #         self.permissions[access].remove(permission)

    def has_access(self, user, path, action):
        """
        Checks if a user can access an path & action combination.

        :return: Boolean
        """
        print("check if user (%s) has '%s' to '%s'" % (user.email, path, action))
        for user_role in user.get_roles():
            print("has_access:user_role: %s %s" % (type(user_role), user_role.label))
            if user_role.label == 'admin':
                return True
            permission = (user_role.label, path, action)
            if permission in self.permissions[access]:
                return True
        return False
