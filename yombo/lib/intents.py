# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Tasks @ Library Documentation <https://yombo.net/docs/libraries/intents>`_

Handles converstation intents.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.23.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/intents.html>`_
"""
from collections import deque
import re
from time import time
import voluptuous as vol

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, maybeDeferred

# Import Yombo libraries
from yombo.constants.platforms import PLATFORM_LIGHT, PLATFORM_SWITCH
from yombo.constants.devicetypes.light import ATR_RGB_COLOR
from yombo.constants.features import FEATURE_SUPPORT_COLOR, FEATURE_BRIGHTNESS
from yombo.constants.intents import *
from yombo.core.exceptions import YomboWarning, IntentHandleError
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.mixins.yombobasemixin import YomboBaseMixin
from yombo.utils import generate_source_string, sha224_compact
import yombo.utils.validators as val
import yombo.utils.color as color_util

logger = get_logger('library.intents')

SLOT_SCHEMA = vol.Schema({
}, extra=vol.ALLOW_EXTRA)

class Intents(YomboLibrary):
    """
    Accepts intents and tries to match them.  More details to come.
    """
    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo intents library"

    def _init_(self, **kwargs):
        self.intents = {}
        self.history = deque([], 100)
        self.off_locations = None
        self.on_locations = None

    def _load_(self, **kwargs):
        """
        Setup basic intents to control devices, scenes, and automation rules.

        :param kwargs:
        :return:
        """
        item_type_slot_schema = {
            vol.Required('item_type'): val.string,
        }

        light_slot_schema = {
            vol.Required('name'): val.string,
            vol.Optional('color'): color_util.color_name_to_rgb,
            vol.Optional('brightness'): vol.All(vol.Coerce(int), vol.Range(0, 100))
        }
        switch_slot_schema = {
            vol.Required('name'): val.string,
        }

        # By location
        statements = self.generate_location_statements('on')
        self.on_locations = self.add(
            statements,
            callback=self.handle_yombo_intents_location,
            slot_schema=item_type_slot_schema,
            intent_type=INTENT_TURN_ON,
            description="Control devices by location - on",
        )
        statements = self.generate_location_statements('off')
        self.off_locations = self.add(
            statements,
            callback=self.handle_yombo_intents_location,
            slot_schema=item_type_slot_schema,
            intent_type=INTENT_TURN_OFF,
            description="Control devices by location - off",
        )

        # Specific items
        self.add([
            'Turn [the] [a] {name}[s] on',
            'Turn on [the] [a] [an] {name}[s]',
            ],
            callback=self.handle_yombo_intents,
            slot_schema=light_slot_schema,
            intent_type=INTENT_TURN_ON,
            description="Turn on a device or activate a scene.",
        )
        self.add([
            'Turn [the] [a] {name}[s] off',
            'Turn off [the] [a] [an] {name}[s]',
            ],
            callback=self.handle_yombo_intents,
            slot_schema=light_slot_schema,
            intent_type=INTENT_TURN_OFF,
            description="Turn off a device or stop a scene.",
        )
        self.add([
            'Toggle [the] [a] [an] {name}[s]',
            '[the] [a] [an] {name}[s] toggle',
            ],
            callback=self.handle_yombo_intents,
            slot_schema=switch_slot_schema,
            intent_type=INTENT_TOGGLE,
            description="Toggle a device",
        )
        self.add([
            'Enable [the] [a] [an] {name}[s]',
            ],
            callback=self.handle_yombo_intents,
            slot_schema=switch_slot_schema,
            intent_type=INTENT_ENABLE,
            description="Enable a device or scene.",
        )
        self.add([
            'Disable [the] [a] [an] {name}[s]',
            ],
            callback=self.handle_yombo_intents,
            slot_schema=switch_slot_schema,
            intent_type=INTENT_DISABLE,
            description="Disable a device or scene.",
        )
        self.add([
            'Open [the] [a] [an] {name}[s]',
            ],
            callback=self.handle_yombo_intents,
            slot_schema=switch_slot_schema,
            intent_type=INTENT_OPEN_COVER,
            description="Open a cover",
        )
        self.add([
            'Close [the] [a] [an] {name}[s]',
            ],
            callback=self.handle_yombo_intents,
            slot_schema=switch_slot_schema,
            intent_type=INTENT_CLOSE_COVER,
            description="Close a cover",
        )

    @inlineCallbacks
    def _started_(self, **kwargs):
        """
        Testing for now...
        :param kwargs:
        :return:
        """
        try:
            yield self.match("Turn off all house kitchen lights")
        except YomboWarning as e:
            print("(intents) ERROR: %s" % e)

        try:
            yield self.match("Turn off all house bedroom lights")
        except YomboWarning as e:
            print("(intents) ERROR: %s" % e)


        try:
            yield self.match("Turn off all kitchen lights")
        except YomboWarning as e:
            print("(intents) ERROR: %s" % e)

        try:
            yield self.match("Turn off kitchen lights")
        except YomboWarning as e:
            print("(intents) ERROR: %s" % e)

        try:
            yield self.match("Turn kitchen lights off")
        except YomboWarning as e:
            print("(intents) ERROR: %s" % e)

        try:
            yield self.match("Turn all lights off")
        except YomboWarning as e:
            print("(intents) ERROR: %s" % e)

        try:
            yield self.match("Turn lights off")
        except YomboWarning as e:
            print("(intents) ERROR: %s" % e)

    def generate_location_statements(self, action):
        statements = []
        for location_id, location in self._Locations.locations.items():
            if location.location_type != 'location' or location.machine_label == 'none':
                continue
            location_label = location.label.lower()
            for area_id, area in self._Locations.locations.items():
                if area.location_type != 'area' or area.machine_label == 'none':
                    continue
                area_label = area.label.lower()
                statements.append({
                    'statement': 'Turn [all] [the] %s %s {item_type}[s] %s' % (location_label, area_label, action),
                    'meta': {'location_id': location_id, 'area_id': area_id},
                    }
                )
                statements.append({
                    'statement': 'Turn %s [all] [the] %s %s {item_type}[s]' % (action, location_label, area_label),
                    'meta': {'location_id': location_id, 'area_id': area_id},
                    }
                )

                statements.append({
                    'statement': 'Turn [all] [the] %s {item_type}[s] %s' % (area_label, action),
                    'meta': {'area_id': area_id},
                    }
                )
                statements.append({
                    'statement': 'Turn %s [all] [the] %s {item_type}[s]' % (action, area_label),
                    'meta': {'area_id': area_id},
                    }
                )
        return statements

    def _locations_deleted_(self, **kwargs):
        self.update_locations()

    def _locations_imported_(self, **kwargs):
        self.update_locations()

    def _locations_updated_(self, **kwargs):
        self.update_locations()

    def _locations_deleted_(self, **kwargs):
        self.update_locations()

    def update_locations(self, **kwargs):
        self.on_locations.statements = self.generate_location_statements('on')
        self.off_locations.statements = self.generate_location_statements('off')

    @inlineCallbacks
    def handle_yombo_intents(self, intent_request):
        print("(intents) handle_yombo_intents was called")
        slots = intent_request.slots
        intent_type = intent_request.intent_type
        print("(intents) Slots: %s" % slots)
        print("(intents) intent_type: %s == %s" % (intent_type, INTENT_TURN_ON))

        # look thru devices
        # look thru scenes
        # look thru automation items
        slot_name = slots['name']['value']

        # print("(intents) intent_type: %s == %s" % (intent_type, INTENT_TURN_ON))

        try:
            request_item = self._Devices.get(slot_name, limiter=.85)
            request_type = 'device'

            print("(intents) GOOD: Found Device: %s" % request_item.full_label)
        except KeyError:
            print("(intents) BAD: Device %s was not found..." % slot_name)
            return

        speech_parts = []
        if request_type == "device":
            command_inputs = {}
            if 'color' in slots:
                request_item.has_feature(FEATURE_SUPPORT_COLOR)
                command_inputs[ATR_RGB_COLOR] = slots['color']['value']
                speech_parts.append('the color {}'.format(slots['color']['value']))

            if 'brightness' in slots:
                request_item.has_feature(FEATURE_BRIGHTNESS)
                command_inputs[ATR_RGB_COLOR] = slots['brightness']['value']
                speech_parts.append('{}% brightness'.format(slots['brightness']['value']))

            if intent_type == INTENT_TURN_ON:
                request_id = request_item.turn_on()
                yield self._Devices.wait_for_command_to_finish(request_id, timeout=3)
            elif intent_type == INTENT_TURN_OFF:
                request_id = request_item.turn_off()
                yield self._Devices.wait_for_command_to_finish(request_id, timeout=3)
            elif intent_type == INTENT_TOGGLE:
                request_id = request_item.toggle()
                yield self._Devices.wait_for_command_to_finish(request_id, timeout=3)
            else:
                raise IntentHandleError("Unknown intent type: %s" % intent_type)

            response = intent_request.response()

            if not speech_parts:  # No attributes changed
                speech = 'Turned {status} {label}'.format(
                    status=request_item.human_status.lower(),
                    label=request_item.full_label.lower())
            else:
                parts = ['Changed {} to'.format(request_item.human_status)]
                for index, part in enumerate(speech_parts):
                    if index == 0:
                        parts.append(' {}'.format(part))
                    elif index != len(speech_parts) - 1:
                        parts.append(', {}'.format(part))
                    else:
                        parts.append(' and {}'.format(part))
                speech = ''.join(parts)

            print("(intents) speech: %s" % speech)
            response.set_speech(speech)
            return response

    # @inlineCallbacks
    def handle_yombo_intents_location(self, intent_request):
        print("(intents) handle_yombo_intents_location was called")
        slots = intent_request.slots
        intent_type = intent_request.intent_type
        statement_meta = intent_request.statement_meta

        print("(intents) Slots: %s" % slots)
        print("(intents) statement_meta: %s" % intent_request.statement_meta)
        print("(intents) intent_type: %s == %s" % (intent_type, INTENT_TURN_ON))

        item_type = slots['item_type']['value']

        location_id = statement_meta.get('location_id', self._Locations.location_id)
        area_id = statement_meta.get('area_id', self._Locations.area_id)

        if item_type not in ('light', 'device'):
            return

        for device_id, device in self._Devices.devices.items():
            if device.location_id != location_id:
                print("device is not in the right location: %s" % location_id)
                continue
            if device.area_id != area_id:
                print("device is not in the right area: %s" % area_id)
                continue

            if item_type == 'light':
                if device.PLATFORM_BASE != PLATFORM_LIGHT:
                    continue
            if item_type == 'device':
                if device.PLATFORM_BASE not in (PLATFORM_LIGHT, PLATFORM_SWITCH):
                    continue

            if intent_type == INTENT_TURN_ON:
                print("turning on: %s" % device.full_label)
                # request_id = device.turn_on()
                # yield self._Devices.wait_for_command_to_finish(request_id, timeout=3)
            elif intent_type == INTENT_TURN_OFF:
                print("turning off: %s" % device.full_label)
                # request_id = device.turn_off()
                # yield self._Devices.wait_for_command_to_finish(request_id, timeout=3)

    def add(self, in_statements, callback, slot_schema=None, intent_type=None,
            description=None, meta=None, intent_id=None):
        """
        Add a new intent.

        :param in_statements: The string to parse.
        :param callback: The callback to call if an intent matches.
        :param meta: Any content set here will be included with an intent match.
        :param intent_id: Optional ID to be to used.
        :return: The intent instance.
        """
        if isinstance(in_statements, str):
            statements = [in_statements]
        statements = []
        for statement in in_statements:
            if isinstance(statement, str):
                statements.append({
                    'statement': statement,
                    'meta': {}
                    }
                )
            else:
                statements.append(statement)

        source = generate_source_string()
        if intent_id is None:
            hash_string = ""
            for statement in statements:
                hash_string += ":%s" % statement['statement']
            if isinstance(description, str):
                hash_string += description
            intent_id = sha224_compact(hash_string)[:15]

        self.intents[intent_id] = Intent(self,
                                         statements=statements,
                                         intent_id=intent_id,
                                         callback=callback,
                                         meta=meta,
                                         description=description,
                                         source=source,
                                         intent_type=intent_type,
                                         slot_schema=slot_schema,
                                         )

        return self.intents[intent_id]

    @inlineCallbacks
    def match(self, statement, source=None):
        """
        Attempts to search through all intents.

        :param statement:
        :return:
        """
        print("(intents) * Starting match on statement: %s" % statement)
        history = {
            'statement': statement,
            'source': source,
            'handler_matched': False,
            'time': time(),
            'slots': {},
        }
        for intent_id, intent in self.intents.items():
            try:
                intent_request = intent.match(statement, source)
            except YomboWarning:
                continue

            # print("(intents) Found a matchin: %s" % intent_request)
            # print("(intents) Found a callback: %s" % intent.callback)
            # intent_response = intent.callback(intent_request)
            try:
                intent_response = yield maybeDeferred(intent.callback, intent_request)
            except Exception as e:
                history['handler_matched'] = False
                self.history.append(history)
                raise YomboWarning("No intents matched request statement: %s" % e)

            # print("(intents) intent_response : %s" % intent_response)
            history['handler_matched'] = True
            history['slots'] = intent_request.slots
            self.history.append(history)
            return intent_response

        self.history.append(history)
        raise YomboWarning("No intents matched request statement.")

    def get(self, intent_id):
        if intent_id in self.intents:
            return self.intents[intent_id]
        raise KeyError('Invalid intent id')


class Intent(YomboBaseMixin):
    @property
    def statements(self):
        return self._statements

    @statements.setter
    def statements(self, value):
        self.matchers = self.create_matcher(value)
        self._statements = value

    def __init__(self, parent, statements, intent_id, callback, meta, description, source, slot_schema,
                 intent_type):
        super().__init__(parent)
        self.matchers = []
        self._statements = statements
        self.intent_id = intent_id
        self.callback = callback
        self.meta = meta
        self.description = description
        self.match_count = 0
        self.source = source
        self.intent_type = intent_type
        self.slot_schema = slot_schema
        self._slot_schema = None  # Compiled schema
        self.create_matchers()

    def match(self, statement, source=None):
        """
        Simply try to match the sent in intent with ours.

        :param statement:
        :return:
        """
        print("(intents)   * intent::match - intent=%s" % statement)
        for match_info in self.matchers:
            matcher = match_info['matcher']
            match = matcher.match(statement)
            if not match:
                continue

            print("(intents)     * intent::match - matcher=%s" % matcher)
            # we have a matching intent, now lets check if it has the required slots.
            slots = {key: {'value': value} for key, value in match.groupdict().items()}

            self.validate_slots(slots)
            self.match_count += 1
            return IntentRequest(intent=self,
                                 slots=slots,
                                 source=source,
                                 statement=statement,
                                 statement_meta=match_info['meta'])
        raise YomboWarning("Intent not matched.")

    def validate_slots(self, slots):
        """
        Validate slot information.
        """
        # print("(intents) about to validate slots: %s" % slots)
        # print("(intents) slot_schema: %s" % self.slot_schema)
        if self.slot_schema is None or len(self.slot_schema) == 0:
            return slots

        if self._slot_schema is None:
            self._slot_schema = vol.Schema({
                key: SLOT_SCHEMA.extend({'value': validator})
                for key, validator in self.slot_schema.items()},
                                           extra=vol.ALLOW_EXTRA)

        # print("(intents) _slot_schema : %s" % self._slot_schema)
        # print("(intents)")
        return self._slot_schema(slots)

    def create_matchers(self):
        """
        Create a regex that matches the intent (voice command / speech).
        """
        for temp_statement in self._statements:
            statement = temp_statement['statement']
            meta = temp_statement['meta']
            # Pattern matches : Change light to [the color] {name}
            parts = re.split(r'({\w+}|\[[\w\s]+\] *)', statement)

            # GROUP, Matches {name}
            group_matcher = re.compile(r'{(\w+)}')
            # OPTIONAL, Matches [the color]
            optional_matcher = re.compile(r'\[([\w ]+)\] *')

            pattern = ['^']
            for part in parts:
                group_match = group_matcher.match(part)
                optional_match = optional_matcher.match(part)

                # Normal part
                if group_match is None and optional_match is None:
                    pattern.append(part)
                    continue

                # Group part
                if group_match is not None:
                    pattern.append(
                        r'(?P<{}>[\w ]+?)\s*'.format(group_match.groups()[0]))

                # Optional part
                elif optional_match is not None:
                    pattern.append(r'(?:{} *)?'.format(optional_match.groups()[0]))

            pattern.append('$')
            self.matchers.append({
                'matcher': re.compile(''.join(pattern), re.I),
                'meta': meta,
                }
            )


class IntentRequest(object):
    @property
    def intent_type(self):
        return self.intent.intent_type

    @property
    def meta(self):
        return self.intent.meta

    def __str__(self):
        return "Yombo intent response: %s" % self.statement

    """
    Send intent requests to intent handlers.
    """
    def __init__(self, intent=None, slots=None, source=None, statement=None, statement_meta=None):
        self.intent = intent
        self.slots = slots or {}
        self.source = source
        self.statement = statement
        self.statement_meta = statement_meta or {}
        self._response = None

    def response(self):
        if self._response is None:
            self._response = IntentResponse(self)
        return self._response


class IntentResponse(object):
    """
    Sent in response to an intent request.
    """
    def __str__(self):
        return "Yombo intent response: %s" % self.intent_request.intent

    def __init__(self, intent_request=None):
        self.intent_request = intent_request
        self.speech = {}
        self.card = {}

    def set_speech(self, speech, speech_type="plain", extra_data=None):
        self.speech[speech_type] = {
            'speech': speech,
            'extra_data': extra_data,
        }

    def set_card(self, title, content, card_type='simple'):
        self.card[card_type] = {
            'title': title,
            'content': content,
        }

