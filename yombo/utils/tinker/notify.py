import pyinotify

wm = pyinotify.WatchManager()  # Watch Manager
mask = pyinotify.IN_MOVED_TO | pyinotify.IN_CREATE | pyinotify.IN_MODIFY  # watched events

class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        print(f"Creating: {event.pathname}")

    def process_IN_MOVED_TO(self, event):
        print(f"IN_MOVED_TO: {event.pathname}")

    def process_IN_MODIFY(self, event):
        print(f"Modified: {event.pathname}")

handler = EventHandler()
notifier = pyinotify.Notifier(wm, handler)
wdd = wm.add_watch('/home/mitch/Yombo/yombo-gateway', mask, rec=True)
notifier.loop()


import schemas
test = schemas.TestSchema()
input = {"id": "1", "one": 234.1, "two": True, "three": 1}
input2 = {"id": "1", "one": 234.1}
test.load(input)
test.load(input2)

test2 = schemas.MySchema()
test2.dumps(input2)

