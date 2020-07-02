# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * For library documentation, see: `Internationalization @ Library Documentation <https://yombo.net/docs/libraries/localize>`_

Localization and translation for Yombo Gateway.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/localize.html>`_
"""
# Import python libraries
import builtins
from functools import partial
import json
from os import environ
from string import Formatter
import sys
from time import time
import traceback
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.utils.converters import unit_convert
from yombo.utils.dictionaries import recursive_dict_merge, access_dict
from yombo.core.log import get_logger

logger = get_logger("library.localize")


class YomboFormatter(Formatter):
    """ Converts a localize string, applying arguments to it. """
    def get_value(self, key, args, keywords):
        if isinstance(key, str):
            try:
                return keywords[key]
            except KeyError:
                return key
        else:
            return Formatter.get_value(key, args, keywords)


class Localize(YomboLibrary):
    """
    Provides internationalization and localization where possible. Default language is "en" (English).

    Localization provides translations for both the system messages, including yombo.toml file.
    """
    @inlineCallbacks
    def _init_(self, **kwargs):
        self.yombo_formatter = YomboFormatter()

        self.localization_degrees = self._Configs.get("localization.degrees", "f", instance=True)
        self.locale_save_folder = f"{self._working_dir}/locale"
        self.available_translations = []
        self.backend_translations = {}

        # Temp load english translation for bootup.
        data = yield self._Files.read(f"{self._app_dir}/yombo/locale/backend/en.json")
        self.backend_translations["en"] = json.loads(data)
        self.default_lang = self._Configs.get("localize.default_lang", self.get_system_language(), instance=True)
        # print(f"########################: default lang: {self.default_lang}")
        # print(f"localize module: a: {self.default_lang}")
        # print(f"localize module: a: {type(self.default_lang)}")
        builtins.__dict__["_"] = self.handle_translate

    @inlineCallbacks
    def _modules_pre_init_(self, **kwargs):
        """
        Called just before modules get their _init_ called. However, all the gateway libraries are loaded.

        This gets all the frontend/backend translation files (.json) to be merged into individual language files.
        :return:
        """
        yield self.update_language_files()

    @inlineCallbacks
    def update_language_files(self):
        """
        This gets all the frontend/backend translation files (.json) to be merged into individual language files.

        :param language:
        :return:
        """
        backend_files = {}
        frontend_files = {}
        try:
            backend_files = yield self._Files.search_path_for_files(
                f"yombo/locale/backend/*",
                recursive=True, merge_dict=backend_files)
        except Exception as e:
            logger.warn("Unable list module backend locale files: {e}", e=e)
        # print(f"localize module: 22: {self.default_lang}")
        # print(f"localize module: 22: {type(self.default_lang)}")
        try:
            frontend_files = yield self._Files.search_path_for_files(
                f"yombo/locale/frontend/*",
                recursive=True, merge_dict=frontend_files)
        except Exception as e:
            logger.warn("Unable list module frontend locale files: {e}", e=e)

        # print(f"localize module: 55")

        for item, module in self._Modules.modules.items():
            # print(f"localize module: {module._machine_label}")
            if module._status != 1:
                continue
            try:
                backend_files = yield self._Files.search_path_for_files(
                    f"yombo/modules/{module._machine_label.lower()}/backend_locale/*",
                    recursive=True, merge_dict=backend_files)
            except Exception as e:
                logger.warn("Unable list module backend locale files: {e}", e=e)
            try:
                frontend_files = yield self._Files.search_path_for_files(
                    f"yombo/modules/{module._machine_label.lower()}/frontend_locale/*",
                    recursive=True, merge_dict=frontend_files)
            except Exception as e:
                logger.warn("Unable list module frontend locale files: {e}", e=e)

        @inlineCallbacks
        def process_locales(files, locale_type):
            """
            Load each locale, merge, and then output to new json file.

            :param files: Dictionary of files, as output from search_path_for_files
            :param locale_type: frontend/backend
            :return:
            """
            locales = {}
            output = {}
            meta = {}
            for file, data in files.items():
                locale = data["filename"].split(".")[0]
                if locale not in locales:
                    locales[locale] = []
                    output[locale] = {}
                    meta[locale] = {"files": [], "time": int(time())}
                meta[locale]["files"].append(file)
                locales[locale].append(file)

            for locale, files in locales.items():
                for file in files:
                    try:
                        data = yield self._Files.read(file)
                        data = json.loads(data)
                    except Exception as e:
                        logger.warn("Unable to read json local file: {e}", e=e)
                    # print(f"local data: {locale}, {file} = {data}")
                    recursive_dict_merge(output[locale], data)
                if locale_type == "backend":
                    if locale not in self.available_translations:
                        self.available_translations.append(locale)
                    # print(f"localize module: 22: {self.default_lang}")
                    # print(f"localize module: 22: {type(self.default_lang)}")
                    # if locale in self.requested_locales \
                    #         or locale in self.backend_translations \
                    #         or locale == self.default_lang.value:
                    self.backend_translations[locale] = data
                try:
                    yield self._Files.save(f"{self.locale_save_folder}/{locale_type}/{locale}.json",
                                    json.dumps(output[locale], separators=(',', ':')))
                    yield self._Files.save(f"{self.locale_save_folder}/{locale_type}/{locale}_meta.json",
                                    json.dumps(meta[locale], indent=4))
                except Exception as e:
                    logger.warn("Unable to write json local file: {e}", e=e)

            if self.default_lang.value not in self.available_translations:
                self._Configs.set("localize.default_lang", "en", ref_source=self)
                self.default_lang = self._Configs.get("localize.default_lang", "en", instance=True)

        yield process_locales(backend_files, "backend")
        yield process_locales(frontend_files, "frontend")
        try:
            pass
        except Exception as e:  # if problem with translation, at least return msgid...
            logger.error("Unable to load translations. Getting null one. Reason: {e}", e=e)
            logger.error("--------------------------------------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")
            self.translator = self.get_translator()
            builtins.__dict__["_"] = self.handle_translate

    def display_temperature(self, in_temp, in_type=None, out_type=None, out_decimals=None):
        """
        Simply converts a one temperature from another. Assumes incoming is the system standard of
        "c" for celcius and defaults to convert the output to the gateway defined system
        default of either "c" or "f".

        :param in_temp: input temperature to consider
        :type in_temp: int, float
        :param in_type: Output temp type. C or F. Default is "c".
        :type out_type: str
        :param out_type: Output temp type. C or F. Default is the system defined value.
        :type in_type: str
        :param out_decimals: If an int, will return the value as a string with the specified decimals.
        :type out_decimals: int, None
        :return:
        """
        if in_type is None:
            in_type = "c"
        else:
            in_type = in_type[0].lower()

        if out_type is None:
            out_type = self.localization_degrees.value[0].lower()
        else:
            out_type = out_type[0].lower()

        if out_type == in_type:
            return in_temp

        converter = f"{in_type}_{out_type}"
        out_temp = unit_convert(converter, in_temp)

        if out_decimals is None:
            return {"value": out_temp, "type": out_type}
        return {
            "value": "{0:.{1}f}".format(out_temp, out_decimals),
            "type": out_type,
           }

    def bytes2human(self, size, precision=2):
        """
        Converts bytes to a human friendly version.

        Source: https://stackoverflow.com/questions/5194057/better-way-to-convert-file-sizes-in-python

        :param precision:
        :return:
        """
        suffixes = ["B", "KB", "MB", "GB", "TB"]
        suffixIndex = 0
        while size > 1024 and suffixIndex < 4:
            suffixIndex += 1  # increment the index of the suffix
            size = size / 1024.0  # apply the division
        return "%.*f%s" % (precision, size, suffixes[suffixIndex])

    def get_system_language(self):
        """
        Returns the system language.
        :return:
        """
        lang = "en"
        for item in ('LANG', 'LC_ALL', 'LC_MESSAGES', 'LANGUAGE'):
            if item in environ:
                try:
                    temp_lang = environ.get(item).split(".")[0]
                    if temp_lang is not None and temp_lang != "":
                        lang = temp_lang
                        break
                except:
                    return None

        if lang not in self.available_translations and "_" in lang:
            lang = lang.split("_")[0]
        if lang not in self.available_translations:
            lang = "en"
        return lang

    def get_translator(self, languages=None):
        """
        Returns a partial to handle_translate with a predetermined language set.

        :param languages: A list or string of possible languages to use.
        :return:
        """
        return partial(self.handle_translate, _set_language=self.validate_language(languages))

    def handle_translate_by_language(self, language, msgid, default_text=None, **kwargs):
        return self.handle_translate(msgid, default_text, _set_language=language, **kwargs)

    def handle_translate(self, msgid, default_text=None, _set_language=None, **kwargs):
        set_language = _set_language or self.default_lang.value
        # if set_language not in self.backend_translations:
        #     set_language = "en"
        if set_language not in self.backend_translations:
            set_language = self.validate_language(set_language)
            if set_language not in self.backend_translations:
                return msgid

        message = None
        try:
            message = access_dict(msgid, self.backend_translations[set_language])
        except KeyError as e:
            logger.debug(f"handle_translate: Key not found: {msgid}")
            if default_text is not None:
                return default_text
            return msgid
        except TypeError as e:
            logger.debug(f"handle_translate: Key not found: {msgid}")
            if default_text is not None:
                return default_text
            return msgid

        if message is None:
            return msgid
        return self.yombo_formatter.format(message, **kwargs)

    def validate_language(self, languages):
        """
        Validates the the requested language is available. Accepts a list or string. If the requested
        language is not found, the default language is returned.

        :param languages:
        :return:
        """
        if languages is None:
            languages = []
        elif isinstance(languages, str):
            languages = [item.strip() for item in languages.split(',')]
        if self.default_lang.value not in languages:
            languages.append(self.default_lang.value)
        if "en" not in languages:
            languages.append("en")  # if all else fails, show english.
        for lang in languages:
            if lang in self.available_translations:
                return lang
        return self.default_lang.value

    def get_translator_from_request(self, request):
        """
        Gets
        :param accept_language: The accept language header from a browser, or a string in the same format
        :return:
        """
        accept_language = request.getHeader("accept-language")
        if accept_language is None or accept_language == "":
            accept_language = "en"
        languages = accept_language.split(",")
        locales = []

        for language in languages:
            lang = language.split(";")
            lang = lang[0].strip()
            lang_parts = lang.split("-")
            if lang not in locales:
                locales.append(lang.replace("-", "_"))
            if lang_parts[0] not in locales:
                locales.append(lang_parts[0])
        locale = self.validate_language(languages)
        return partial(self.handle_translate_by_language, locale)
