import logging
import uuid
import os

import vakt
from vakt.rules import Eq, Any, NotEq, StartsWith, In, RegexMatch, CIDR, And, Greater, Less


policies = [
    vakt.Policy(
        str(uuid.uuid4()),
        actions=[Eq('get'), Eq('list'), Eq('read')],
        resources=[{'platform': Eq('lib/states'), 'id': Any()}],
        # resources=[{'platform': Eq('lib/states')}],
        subjects=[Eq('user:joe')],
        effect=vakt.DENY_ACCESS,
        # effect=vakt.ALLOW_ACCESS,
        description='Grant read access to all states'
    ),
    vakt.Policy(
        str(uuid.uuid4()),
        actions=[Eq('get'), Eq('list'), Eq('read')],
        resources=[{'platform': Eq('lib/states'), 'id': Eq("one")}],
        subjects=[Eq('user:joe')],
        effect=vakt.ALLOW_ACCESS,
        # effect=vakt.DENY_ACCESS,
        description='Grant read access to all states'
    ),

    # vakt.Policy(
    #     str(uuid.uuid4()),
    #     actions=[Eq('get'), Eq('list'), Eq('read'), Eq('edit')],
    #     resources=[{'platform': Eq('lib/states'), 'id': Any()}],
    #     subjects=[{'role': Eq('admin')}],
    #     effect=vakt.ALLOW_ACCESS,
    #     description='Grant read access to all states'
    # ),
    # vakt.Policy(
    #     str(uuid.uuid4()),
    #     actions=[Eq('get'), Eq('list'), Eq('read'), Eq('edit')],
    #     resources=[{'platform': Eq('lib/states'), 'id': Any()}],
    #     subjects=[{'user': 'joe', 'role': Any()}],
    #     effect=vakt.ALLOW_ACCESS,
    #     description='Grant read access to all states'
    # ),
    # vakt.Policy(
    #     str(uuid.uuid4()),
    #     actions=[Eq('get'), Eq('list'), Eq('read'), Eq('edit')],
    #     resources=[{'platform': Eq('lib/states'), 'id': Eq('one')}],
    #     subjects=[{'name': Eq('joe')}],
    #     effect=vakt.ALLOW_ACCESS,
    #     description='Grant read access to all states'
    # ),

    # vakt.Policy(
    #     str(uuid.uuid4()),
    #     actions=[Eq('get'), Eq('list'), Eq('read')],
    #     resources=[{'platform': Eq('lib/states'), 'id': Eq('aa')}],
    #     subjects=[{'role': Eq('admin')}],
    #     effect=vakt.ALLOW_ACCESS,
    #     description='Grant read access to all states'
    # ),
    # vakt.Policy(
    #     str(uuid.uuid4()),
    #     actions=[Eq('get'), Eq('list'), Eq('read')],
    #     resources=[{'platform': Eq('lib/states'), 'id': Any()}],
    #     subjects=[{'name': Eq('joe')}],
    #     effect=vakt.DENY_ACCESS,
    #     description='Grant read access to all states'
    # ),

    # vakt.Policy(
    #     str(uuid.uuid4()),
    #     actions=[Eq('get'), Eq('list'), Eq('read')],
    #     resources=[StartsWith('yombo/library/states')],
    #     subjects=[{'name': Eq('joe')}, {'role': Eq('Admin')}],
    #     effect=vakt.DENY_ACCESS,
    #     description='Grant read access to all states'
    # ),


    # vakt.Policy(
    #     str(uuid.uuid4()),
    #     actions=[In('delete', 'prune', 'exterminate')],
    #     resources=[RegexMatch(r'repos\/.*?\/.*?')],
    #     subjects=[{'name': Any(), 'role': Eq('admin')}, {'name': Eq('defunkt')}, Eq('defunkt')],
    #     effect=vakt.ALLOW_ACCESS,
    #     description='Grant delete-access for any repository to any User with "admin" role, or to a User named defunkt'
    # ),
    # vakt.Policy(
    #     str(uuid.uuid4()),
    #     actions=[Any()],
    #     resources=[{'category': Eq('administration'), 'sub': In('panel', 'switch')}],
    #     subjects=[{'name': Any(), 'role': NotEq('developer')}],
    #     effect=vakt.ALLOW_ACCESS,
    #     context={'ip': CIDR('127.0.0.1/32')},
    #     description="""
    #     Allow access to administration interface subcategories: 'panel', 'switch' if user is not
    #     a developer and came from local IP address.
    #     """
    # ),
    # vakt.Policy(
    #     str(uuid.uuid4()),
    #     actions=[Eq('fork')],
    #     resources=[StartsWith('repos/DataDog', ci=True)],
    #     subjects=[{'name': Any(), 'stars': And(Greater(50), Less(999))}],
    #     effect=vakt.ALLOW_ACCESS,
    #     description='Allow forking any DataDog repository for users that have > 50 and < 999 stars'
    # ),
]

def main():
    # configure logger
    # root = logging.getLogger()
    # root.setLevel(logging.INFO)
    # root.addHandler(logging.StreamHandler())
    # start server
    storage = vakt.MemoryStorage()
    # policy = vakt.Policy.from_json(
    #     '{"actions": [{"py/object": "vakt.rules.operator.Eq", "val": "get"}, {"py/object": "vakt.rules.operator.Eq", "val": "list"}, {"py/object": "vakt.rules.operator.Eq", "val": "read"}], "context": {}, "description": "Grant read access to all states", "effect": "allow", "meta": {}, "resources": [{"id": {"py/object": "vakt.rules.logic.Any"}, "platform": {"py/object": "vakt.rules.operator.Eq", "val": "lib/states"}}], "subjects": [{"py/object": "vakt.rules.operator.Eq", "val": "user:joe"}], "type": 2, "uid": "7d8b335b-9ee8-420d-94e0-ef17e3b92b15"}')
    # storage.add(p)
    for p in policies:
        # print(f"adding p: {p}")
        # print(p.to_json())
        storage.add(p)
    # print(f"references: {storage.get_all(100, 0)[0]}")
    guard = vakt.Guard(storage, vakt.RulesChecker())

    # inq = vakt.Inquiry(action='get',
    #                    resource={'platform': 'lib/states', 'id': '*'},
    #                    subject={'name': 'larry', 'role': 'admin'},
    #                    context={'referer': 'https://github.com'})
    #
    # print(f"get - larry - admin - * - {bool(guard.is_allowed(inq))}")
    #
    # inq = vakt.Inquiry(action='edit',
    #                    resource={'platform': 'lib/states', 'id': 'one'},
    #                    subject={'name': 'larry', 'role': 'admin'},
    #                    context={'referer': 'https://github.com'})
    #
    # print(f"edit - larry - admin - one - {bool(guard.is_allowed(inq))}")
    #
    inq = vakt.Inquiry(action='get',
                       resource={'platform': 'lib/states', 'id': '*'},
                       subject='user:joe',
                       context={'referer': 'https://github.com'})

    print(f"get - * - user___joe - {bool(guard.is_allowed(inq))}")

    roles = ['one', 'two']
    inq = vakt.Inquiry(action='get',
                       resource={'platform': 'lib/states', 'id': 'one'},
                       subject='user:joe',
                       context={'referer': 'https://github.com'})

    print(f"get - one - user___joe - {bool(guard.is_allowed(inq))}")


    roles = ['one', 'two']
    # for role in roles:
    #     inq = vakt.Inquiry(action='get',
    #                        resource={'platform': 'lib/states', 'id': 'one'},
    #                        subject=f'role:{role}')
    #
    #     print(f"get - one - role___{role} - {bool(guard.is_allowed(inq))}")

    # inq = vakt.Inquiry(action='get',
    #                    resource={'platform': 'lib/states', 'id': 'one'},
    #                    subject={'name': 'joe', 'role': 'one'},
    #                    context={'referer': 'https://github.com'})
    #
    # print(f"edit - joe - user - one - {bool(guard.is_allowed(inq))}")
    #
    # inq = vakt.Inquiry(action='get',
    #                    resource={'platform': 'lib/states', 'id': 'one'},
    #                    subject={'role': 'one'},
    #                    context={'referer': 'https://github.com'})
    #
    # print(f"edit - NOUSER - user - one - {bool(guard.is_allowed(inq))}")



if __name__ == '__main__':
    main()