
from yombo.lib.commands import Command, Commands

from time import time
import pytest

class TestCommands:

    @pytest.fixture
    def empty_commands(self):
        '''Returns a Wallet instance with a balance of 20'''
        return Commands()

    def test_create_commands(self, empty_commands):
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!11")
        assert empty_commands._FullName == 'yombo.gateway.lib.Commands'
        assert empty_commands._Name == 'Commands'

    def test_create_commands_init(self, empty_commands):
        empty_commands._init_()
        assert empty_commands.commands == {}
        assert isinstance(empty_commands.command_search_attributes, list)

class TestCommand:
    def test_create_command(self):
        record = {
            'id': "testid1",
            'label': "Test Cmd 1",
            'machine_label': 'test_label_1',
            'description': "Test Cmd 1",
            'voice_cmd': None,
            'always_load': 1,
            'public': 0,
            'status': 0,
            'created': int(time()) - 100,
            'updated': int(time())
        }

        command = Command(record)
        assert command.__str__() == record['id']

        assert command.command_id == record['id']
        assert command.label == record['label']
        assert command.cmd == record['machine_label']
        assert command.machine_label == record['machine_label']
        assert command.description == record['description']
        assert command.voice_cmd == record['voice_cmd']
        assert command.always_load == record['always_load']
        assert command.public == record['public']
        assert command.status == record['status']
        assert command.created == record['created']
        assert command.updated == record['updated']
        assert command.machine_label == record['machine_label']
