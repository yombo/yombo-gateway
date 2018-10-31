# Import python libraries
from collections import OrderedDict
from os import listdir, remove, rename
from os.path import isfile, join
from sqlite3 import IntegrityError
from time import time

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks
from twisted.internet.utils import getProcessOutput

# Import Yombo libraries
from yombo.core.log import get_logger
# Import 3rd-party libs
from yombo.ext.twistar.registry import Registry
from yombo.lib.localdb import Device, Command, DeviceType
from yombo.utils import sleep

logger = get_logger('library.localdb._tools')


class DB_Tools(object):
    def get_model_class(self, class_name):
        return globals()[class_name]()

    @inlineCallbacks
    def _load_db_model(self):
        """
        Inspect the DB and generate a model.

        :return:
        """
        tables = yield self.dbconfig.select('sqlite_master', select='tbl_name', where=['type = ?', 'table'])
        for table in tables:
            columns = yield self.dbconfig.pragma('table_info(%s)' % table['tbl_name'])
            self.db_model[table['tbl_name']] = OrderedDict()
            for column in columns:
                self.db_model[table['tbl_name']][column['name']] = column

    @inlineCallbacks
    def load_test_data(self):
        logger.info("Loading databsae test data")

        command = yield Command.find('command1')
        if command is None:
            command = yield Command(id='command1', machine_label='6on', label='O6n', public=1, status=1, created_at=1,
                                    updated_at=1).save()

        device = yield Device.find('device1')
        if device is None:
            device = yield Device(id='device1', machine_label='on', label='Lamp1', gateway_id='gateway1',
                                  device_type_id='devicetype1', pin_required=0, pin_timeout=0, status=1, created_at=1,
                                  updated_at=1, description='desc', notes='note').save()
            # variable = yield Variable(variable_type='device', variable_id="variable_id1", foreign_id='deviceVariable1', device_id=device.id, weigh=0, machine_label='device_var_1', label='Device Var 1', value='somevalue1', updated_at=1, created_at=1).save()

        deviceType = yield DeviceType.find('devicetype1')
        if deviceType is None:
            deviceType = yield DeviceType(id=device.device_type_id, machine_label='x10_appliance', label='Lamp1',
                                          device_class='x10', description='x10 appliances', status=1, created_at=1,
                                          updated_at=1).save()
            args = {'device_type_id': device.id, 'command_id': command.id}
            yield self.dbconfig.insert('command_device_types', args)

        device = yield Device.find('device1')
        # results = yield Variable.find(where=['variable_type = ? AND foreign_id = ?', 'device', device.id])

    #          results = yield DeviceType.find(where=['id = ?', device.device_variables().get()

    def add_bulk_queue(self, table, queue_type, data, id_col=None, insert_blind=None):
        if id_col is None:
            id_col = 'id'
        self.db_bulk_queue_id_cols[table] = id_col

        if queue_type not in ('update', 'insert', 'delete'):
            return
        if table not in self.db_bulk_queue:
            self.db_bulk_queue[table] = {
                'insert': {},
                'insert_blind': [],
                'update': {},
                'delete': [],
            }

        if queue_type == 'insert':
            if insert_blind is True:
                self.db_bulk_queue[table]['insert_blind'].append(data)
            else:
                self.db_bulk_queue[table][queue_type][data[id_col]] = data
        elif queue_type == 'update':
            if data[id_col] in self.db_bulk_queue[table]['insert']:
                for key, value in data.items():
                    self.db_bulk_queue[table]['insert'][data[id_col]][key] = value
            elif data[id_col] in self.db_bulk_queue[table]['update']:
                for key, value in data.items():
                    self.db_bulk_queue[table]['update'][data[id_col]][key] = value
            else:
                self.db_bulk_queue[table][queue_type][data[id_col]] = data
        elif queue_type == 'delete':
            self.db_bulk_queue[table][queue_type].append(data[id_col])

    @inlineCallbacks
    def save_bulk_queue(self):
        # print("saving bulk data: %s" % self.db_bulk_queue)
        for table in self.db_bulk_queue.keys():
            # print("saving bulk table: %s" % table)
            queues = self.db_bulk_queue[table]
            for queue_type in queues.keys():
                if len(self.db_bulk_queue[table][queue_type]) > 0:
                    db_data = self.db_bulk_queue[table][queue_type].copy()
                    self.db_bulk_queue[table][queue_type].clear()
                    if queue_type == 'insert':
                        send_data = []
                        for key, value in db_data.items():
                            send_data.append(value)
                        try:
                            yield self.insert_many(table, send_data)
                        except IntegrityError as e:
                            logger.warn("Error trying to insert_many in bulk save: {e}", e=e)
                            logger.warn("Table: {table}, data: {send_data}", table=table, send_data=send_data)
                    elif queue_type == 'update':
                        send_data = []
                        for key, value in db_data.items():
                            send_data.append(value)
                        try:
                            yield self.update_many(table, send_data, self.db_bulk_queue_id_cols[table])
                        except IntegrityError as e:
                            logger.warn("Error trying to update_many in bulk save: {e}", e=e)
                            logger.warn("Table: {table}, data: {send_data}", table=table, send_data=send_data)
                    elif queue_type == 'delete':
                        try:
                            yield self.delete_many(table, db_data)
                        except IntegrityError as e:
                            logger.warn("Error trying to delete_many in bulk save: {e}", e=e)
                            logger.warn("Table: {table}, data: {send_data}", table=table, send_data=send_data)

    @inlineCallbacks
    def make_backup(self):
        """
        Makes a backup of the database file. This only keeps 20 backups and typically only happens once a day.

        :return:
        """
        db_file = self._Atoms.get('working_dir') + "/etc/yombo.db"
        db_backup_path = self._Atoms.get('working_dir') + "/bak/db/"
        db_backup_files = [f for f in listdir(db_backup_path) if isfile(join(db_backup_path, f))]
        start_time = time()
        for i in range(20, -1, -1):  # reversed range
            current_backup_file_name = "yombo.db.%s" % i
            if current_backup_file_name in db_backup_files:
                if i == 20:
                    remove(db_backup_path + current_backup_file_name)
                else:
                    next_backup_file_name = "yombo.db.%s" % str(i + 1)
                    rename(db_backup_path + current_backup_file_name, db_backup_path + next_backup_file_name)

        yield getProcessOutput("sqlite3", [db_file, ".backup %syombo.db.1" % db_backup_path])
        self._Events.new('localdb', 'dbbackup', time() - start_time)

    @inlineCallbacks
    def cleanup_database(self, section=None):
        """
        Cleans out old data and optimizes the database.
        :return:
        """
        if self.cleanup_database_running is True:
            logger.info("Cleanup database already running.")
        self.cleanup_database_running = True

        if section is None:
            section = 'all'
        timer = 0

        # Delete old device commands
        if section in ('device_commands', 'all'):
            yield sleep(5)
            start_time = time()
            for request_id in list(self._Devices.device_commands.keys()):
                device_command = self._Devices.device_commands[request_id]
                if device_command.finished_at is not None:
                    if device_command.finished_at > start_time - 3600:  # keep 60 minutes worth.
                        found_dc = False
                        for device_id, device in self._Devices.devices.items():
                            if request_id in device.device_commands:
                                found_dc = True
                                break
                        if found_dc is False:
                            yield device_command.save_to_db()
                            del self._Devices.device_commands[request_id]
            yield self.dbconfig.delete('device_commands', where=['created_at < ?', time() - (86400 * 45)])
            timer += time() - start_time

        # Lets delete any device status after 90 days. Long term data should be in the statistics.
        if section in ('device_status', 'all'):
            yield sleep(5)
            start_time = time()
            yield self.dbconfig.delete('device_status', where=['set_at < ?', time() - (86400 * 90)])
            timer += time() - start_time

        # Cleanup events.
        if section in ('events', 'all'):
            yield sleep(5)
            for event_type, event_data in self._Events.event_types.items():
                for event_subtype, event_subdata in event_data.items():
                    if event_subdata['expires'] == 0:  # allow data collection for forever.
                        continue
                    yield sleep(1)  # There's no race
                    start_time = time()
                    results = yield self.dbconfig.delete(
                        'events',
                        where=[
                            'event_type = ? AND event_subtype = ? AND created_at < ?',
                            event_type, event_subtype, time() - (86400 * event_subdata['expires'])])
                    timer += time() - start_time

        # Clean notifications
        if section in ('notifications', 'all'):
            yield sleep(1)
            start_time = time()
            for id in list(self._Notifications.notifications.keys()):
                if self._Notifications.notifications[id].expire_at == "Never":
                    continue
                if start_time > self._Notifications.notifications[id].expire_at:
                    del self._Notifications.notifications[id]
            yield self.dbconfig.delete('notifications', where=['expire_at < ?', time()])
            timer += time() - start_time

        if section in ('states', 'all'):
            yield sleep(5)
            sql = "DELETE FROM states WHERE created_at < %s" % str(int(time()) - 86400 * 180)
            start_time = time()
            yield Registry.DBPOOL.runQuery(sql)
            timer += time() - start_time
            yield sleep(5)
            start_time = time()
            sql = """DELETE FROM states WHERE id IN
                  (SELECT id
                   FROM states AS s
                   WHERE s.name = states.name
                   ORDER BY created_at DESC
                   LIMIT -1 OFFSET 100)"""
            yield Registry.DBPOOL.runQuery(sql)
            timer += time() - start_time

        self._Events.new('localdb', 'cleaning', (section, timer))

        if section == 'all':
            yield sleep(5)
            self.make_backup()
            yield sleep(10)
            yield self.dbconfig.vaccum()

        self.cleanup_database_running = False
