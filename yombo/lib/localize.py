# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Internationalization @ Module Development <https://yombo.net/docs/libraries/localize>`_

Localization and translation for Yombo Gateway.


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/localize.html>`_
"""
# Import python libraries
from time import time
from os import path, listdir, makedirs, environ
import inspect
import sys, gettext
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json
try:
    from hashlib import sha3_224 as sha224
except ImportError:
    from hashlib import sha224
import builtins
from string import Formatter
import sys
import traceback

# Import 3rd-party libs
import yombo.ext.polib as polib

# Import Yombo libraries
from yombo.core.library import YomboLibrary
import yombo.core.settings as settings
from yombo.utils.converters import unit_convert
from yombo.core.log import get_logger

logger = get_logger("library.localize")

class YomboFormatter(Formatter):
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
    Provides internaltionalization and localization where possible.  Default language is 'en' (English). System and
    debug messages are never translated.
    """
    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo localization and translation library"

    def _init_(self, **kwargs):
        self.working_dir = settings.arguments['working_dir']
        self.default_lang = self._Configs.get2('localize', 'default_lang', 'en', False)

        try:
            hashes = self._Configs.get('localize', 'hashes')
        except:
            self.hashes = {'en': None}
        else:
            self.hashes = json.loads(hashes)

        if 'en' not in self.hashes:
            self.hashes['en'] = None

        self.localization_degrees = self._Configs.get2("localization", "degrees", "f")

        self.files = {}

        self.locale_save_folder = "%s/locale/po/" % self.working_dir
        self.translator = self.get_translator()
        builtins.__dict__['_'] = self.handle_translate

    def display_temperature(self, in_temp, in_type=None, out_type=None, out_decimals=None):
        """
        Simply converts a one temperature from another. Assumes incoming is the system standard of
        'c' for celcius and defaults to convert the output to the gateway defined system
        default of either 'c' or 'f'.

        :param in_temp: input temperature to consider
        :type in_temp: int, float
        :param in_type: Output temp type. C or F. Default is 'c'.
        :type out_type: str
        :param out_type: Output temp type. C or F. Default is the system defined value.
        :type in_type: str
        :param out_decimals: If an int, will return the value as a string with the specified decimals.
        :type out_decimals: int, None
        :return:
        """
        if in_type is None:
            in_type = 'c'
        else:
            in_type = in_type[0].lower()

        if out_type is None:
            out_type = self.localization_degrees()[0].lower()
        else:
            out_type = out_type[0].lower()

        if out_type == in_type:
            return in_temp

        converter = '%s_%s' % (in_type, out_type)
        out_temp = unit_convert(converter, in_temp)

        if out_decimals is None:
            return {'value': out_temp, 'type': out_type}
        return {
            'value': "{0:.{1}f}".format(out_temp, out_decimals),
            'type': out_type,
           }

    def bytes2human(self, size, precision=2):
        """
        Converts bytes to a human friendly version.

        Source: https://stackoverflow.com/questions/5194057/better-way-to-convert-file-sizes-in-python

        :param precision:
        :return:
        """
        suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
        suffixIndex = 0
        while size > 1024 and suffixIndex < 4:
            suffixIndex += 1  # increment the index of the suffix
            size = size / 1024.0  # apply the division
        return "%.*f%s" % (precision, size, suffixes[suffixIndex])

    def _modules_pre_init_(self, **kwargs):
        """
        Called just before modules get their _init_ called. However, all the gateway libraries are loaded.

        This combines any module .po/.po.head files with the system po files. Then creates .mo binary files.

        Uses a basic sha224 hash to validate if files have changes or not between runs. This prevents the files to be
        rebuilt on each run.
        :return:
        """
        try:
            languages_to_update = {}
            self.parse_directory("yombo/utils/locale", has_header=True)

            try:
                for item, data in self._Modules.modules.items():
                    the_directory = path.dirname(path.abspath(inspect.getfile(data.__class__))) + "/locale"
                    if path.exists(the_directory):
                        self.parse_directory(the_directory)
            except Exception as e:
                logger.warn("Unable list module local files: %s" % e)

            # always check english. If it gets updated, we need to update them all!
            hash_obj = sha224(open(self.files['en'][0], 'rb').read())

            for fname in self.files['en'][1:]:
                hash_obj.update(open(fname, 'rb').read())
            checksum = hash_obj.hexdigest()

            if checksum != self.hashes['en']:
                self.hashes = {}

            # Generate/update locale file hashes. If anything changed, add to languages_to_update
            for lang, files in self.files.items():
                hash_obj = sha224(open(files[0], 'rb').read())
                for fname in files[1:]:
                    hash_obj.update(open(fname, 'rb').read())
                checksum = hash_obj.hexdigest()
                if lang in self.hashes:
                    if path.exists(self.working_dir + '/locale/po/' + lang + '/LC_MESSAGES/yombo.mo') is False:
                        languages_to_update[lang] = True
                        continue
                    if checksum == self.hashes[lang]:
                        # self.hashes[lang] = checksum
                        continue

                self.hashes[lang] = checksum
                languages_to_update[lang] = True

            # If we have a default language, lets make sure we have language files for it.
            if self.default_lang() is not None:
                if self.default_lang() not in self.files:
                    self.default_lang(set=None)
                    language = self.default_lang().split('_')[0]
                    if language in self.files:
                        self.default_lang(set=language)
            # If no default lang, try the system language.
            if self.default_lang() is None:
                language = self.get_system_language()
                if language in self.files:
                    self.default_lang(set=language)
                else:
                    language = language.split('_')[0]
                    if language in self.files:
                        self.default_lang(set=language)

            # If still no language, we will use english.
            if self.default_lang() is None:
                self.default_lang(set='en')

            # English is the base of all language files. If English needs updating, we update the default too.
            if 'en' in languages_to_update and self.default_lang() not in languages_to_update:
                languages_to_update[self.default_lang()] = True

            # Always do english language updates first, it's the base of all.
            if 'en' in languages_to_update:
                self.do_update('en')
                del languages_to_update['en']

            # Add the default language to the stack.
            if self.default_lang() in languages_to_update:
                self.do_update(self.default_lang())
                del languages_to_update[self.default_lang()]

            # self.default_lang() = 'es' # some testing...
            self._States['localize.default_language'] = self.default_lang()

            for lang, files in languages_to_update.items():
                self.do_update(lang)

            # Save the updated hash into the configuration for next time.
            self._Configs.set('localize', 'hashes', json.dumps(self.hashes, separators=(',',':')))

            gettext._translations.clear()
            self.translator = self.get_translator()
            builtins.__dict__['_'] = self.handle_translate

        except Exception as e: # if problem with translation, at least return msgid...
            logger.error("Unable to load translations. Getting null one. Reason: %s" % e)
            logger.error("--------------------------------------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")
            self.translator = self.get_translator(get_null=True)
            builtins.__dict__['_'] = self.handle_translate

    def get_system_language(self):
        """
        Returns the system language.
        :return:
        """
        for item in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
            if item in environ:
                try:
                    return environ.get(item).split(".")[0]
                except:
                    return None

    def get_translator(self, languages=None, get_null=None):
        if get_null is True:
            return gettext.NullTranslations()
        if languages is None:
            languages = []
            if self.default_lang() not in languages:
                languages.append(
                    self.default_lang())  # toss in the gateway default language, which may be the system lang
            if 'en' not in languages:
                languages.append('en')  # if all else fails, show english.
        logger.debug("locale_files path: {path}", path=self.locale_save_folder)
        try:
            return gettext.translation('yombo', self.locale_save_folder, languages)
        except Exception as e: # if problem with translation, at least return msgid...
            logger.warn("Ignore this if first running Yombo. Unable to load translations: %s" % e)
        return gettext.NullTranslations()

    def handle_translate(self, msgid, default_text=None, translator=None, **kwargs):

        if translator is None:
            translator = self.translator
        yfmt = YomboFormatter()
        translation = translator.gettext(msgid)
        if translation == msgid and default_text is not None:
            return yfmt.format(default_text, **kwargs)
        return yfmt.format(translation, **kwargs)

    def do_update(self, language):
        """
        Merges all the files togther and then generates a compiled langauges file (mo)
        :param language:
        :return:
        """
        logger.debug("Localize combining files for language: {language}", language=language)
        output_folder = self.working_dir + '/locale/po/' + language + '/LC_MESSAGES'

        if not path.exists(output_folder):
            makedirs(output_folder)

        # merge files
        with open(output_folder + '/yombo.po', 'w') as outfile:
            # outfile.write("# BEGIN Combining files (%s) for locale: %s\n" % (strftime("%Y-%m-%d %H:%M:%S", gmtime()), language) )
            for fname in self.files[language]:
                # outfile.write("# BEGIN File: %s\n" % fname)
                with open(fname) as infile:
                    outfile.write(infile.read())
                # outfile.write("\n# END File: %s\n\n" % fname)
            # outfile.write("# END Combining files for locale: %s\n" % language)
        po_lang = polib.pofile(output_folder + '/yombo.po')
        po_lang.save_as_mofile(output_folder + "/yombo.mo")

    def parse_directory(self, directory, has_header=False):
        """
        Checks a directory for any .po or .po.head files to combine them. This allows modules to have translation
        files.
        :param directory: The directory to check.
        :return:
        """
        for filename in listdir(directory):
            if filename.endswith(".po") is False:
                continue
            filepart = filename.split('.')
            filepart = filepart[0]
            locale = filepart.split('_')
            if len(locale) == 0 or len(locale) > 2:
                logger.warn("Bad language_country code split. Must be <ISO 639 lang code>_<ISO 3166 REGION CODE (optional)>: {{locale}}, file: {filename}",
                            locale=locale[0], filename=filename)

            if locale[0].islower() is False:
                logger.warn("Invalid file, ISO 639 lang code must be lower case: {locale}, file: {filename}",
                            locale=locale[0], filename=filename)
                continue
            elif len(locale[0]) not in (2, 3):
                logger.warn("Invalid file, ISO 639 lang code must be 2 (preferred) or 3 letters: {locale}, file: {filename}",
                            locale=locale[0], filename=filename)
                continue

            if len(locale) == 2:
                if locale[1].isupper() is False and locale[1].isalpha() is True:
                    logger.warn("Invalid file, ISO 6166 region code must be upper case: {locale}, file: {filename}",
                                locale=locale[0], filename=filename)
                    continue
                elif len(locale[1]) not in (2, 3):
                    logger.warn("Invalid file, ISO 6166 region code must be 2 letters: {locale}, file: {filename}",
                                locale=locale[0], filename=filename)
                    continue

            if filepart not in self.files:
                if path.exists(directory + "/" + filename + ".head"):
                    self.files[filepart] = []
                    self.files[filepart].append(directory + "/" + filename + ".head")
                    self.files[filepart].append(directory + "/" + filename)
                else:
                    if has_header == True:
                        self.files[filepart] = []
                        self.files[filepart].append(directory + "/" + filename)
                    else:
                        logger.warn("Yombo core doesn't have a locale for: {lang}  Cannot merge file. Additionally, no '.head' file exists. (Help link soon.)",
                            lang=filepart)
            else:
                self.files[filepart].append(directory + "/" + filename)

    def get_ugettext(self, languages):
        """
        Returns a translator function based on a list of languages provided. If request through a webbrowser, send
        the request to :py:meth:parse_accept_language first.

        :param languages: list of locales to check, in order of list items.
        :return:
        """
        translator = self.get_translator(languages)
        return translator.gettext

    def get_ungettext(self, languages):
        """
        Returns a translator function based on a list of languages provided. If request through a webbrowser, send
        the request to :py:meth:parse_accept_language first.

        :param languages: list of locales to check, in order of list items.
        :return:
        """
        translator = self.get_translator(languages)
        return translator.ngettext

    def parse_accept_language(self, accept_language):
        """
        From: https://siongui.github.io/2012/10/11/python-parse-accept-language-in-http-request-header/
        Modified for yombo...
        :param accept_language: The accept language header from a browser, or a string in the same format
        :return:
        """
        if accept_language is None or accept_language == "":
            accept_language = "en"
        languages = accept_language.split(",")
        locales = []

        for language in languages:
            lang = language.split(";")
            lang = lang[0].strip()
            lang_parts = lang.split('-')
            if lang not in locales:
                locales.append(lang.replace("-", "_"))
            if lang_parts[0] not in locales:
                locales.append(lang_parts[0])
        if self.default_lang() not in locales:
            locales.append(self.default_lang())  # toss in the gateway default language, which may be the system lang
        if 'en' not in locales:
            locales.append('en')  # if all else fails, show english.
        return locales

