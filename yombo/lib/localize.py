# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Internationalization @ Module Development <https://yombo.net/docs/modules/internationalization/>`_

Localization and translation for Yombo Gateway.

This is a new library and currently only supporting translations (i18n). See
`Internationalization @ Module Development <https://yombo.net/docs/modules/internationalization/>`_ for details on
usage.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.12.0

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
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
from hashlib import md5
from time import gmtime, strftime
from os.path import abspath
import __builtin__
import sys
import traceback

# Import 3rd-party libs
import yombo.ext.polib as polib

# Import Yombo libraries
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

logger = get_logger("library.localize")

class Localize(YomboLibrary):
    """
    Provides internaltionalization and localization where possible.  Default language is 'en' (English). System and
    debug messages are never translated.
    """
    MSGCTXT_GLUE = "\004"

    def _init_(self):
        self.default_lang = self._Configs.get2('localize', 'default_lang', 'en', False)

        try:
            hashes = self._Configs.get('localize', 'hashes')
        except:
            self.hashes = {'en': None}
        else:
            self.hashes = json.loads(hashes)

        if 'en' not in self.hashes:
            self.hashes['en'] = ''

        self.files = {}
        self.locale_files = abspath('.') + "/usr/locale/"
        self.translator = self.get_translator()
        __builtin__.__dict__['_'] = self.handle_translate

    def _modules_created_(self, **kwargs):
        """
        Called just before modules get their _init_ called. However, all the gateway libraries are loaded.

        This combines any module .po/.po.head files with the system po files. Then creates .mo binary files.

        Uses a basic MD5 hash to validate if files have changes or not between runs. This prevents the files to be
        rebuilt on each run.
        :return:
        """
        try:
            languages_to_update = {}
            self.parse_directory("yombo/utils/locale", has_header=True)

            try:
                for item, data in self._Modules.modules.iteritems():
                    the_directory = path.dirname(path.abspath(inspect.getfile(data.__class__))) + "/locale"
                    if path.exists(the_directory):
                        self.parse_directory(the_directory)
            except Exception as e:
                logger.warn("Unable list module local files: %s" % e)

            # print "localize . self.files: %s" % self.files

            #always check english. If it gets updated, we need to update them all!
            hash_obj = md5(open(self.files['en'][0], 'rb').read())

            for fname in self.files['en'][1:]:
                hash_obj.update(open(fname, 'rb').read())
            checksum = hash_obj.hexdigest()

            if checksum != self.hashes['en']:
                self.hashes = {}

            # Generate/update locale file hashes. If anything changed, add to languages_to_update
            for lang, files in self.files.iteritems():
                hash_obj = md5(open(files[0], 'rb').read())
                for fname in files[1:]:
                    hash_obj.update(open(fname, 'rb').read())
                checksum = hash_obj.hexdigest()
                # print "self.hashes: %s" % self.hashes
                # print "checksum (%s): %s" % (lang, checksum)
                if lang in self.hashes:
                    # print "self.hashes[lang]: %s" % self.hashes[lang]
                    if checksum == self.hashes[lang]:
                        # print "skipping lang due to checksum match: %s" % lang
                        self.hashes[lang] = checksum
                        continue

                self.hashes[lang] = checksum
                # print "not skipping lang due to checksum mismatch: %s" % lang
                languages_to_update[lang] = 'aaa'

            # print "languages_to_update: %s" % languages_to_update
            # print "self.default_lang 11: %s" % self.default_lang()
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
                languages_to_update[self.default_lang()] = 'a'

            # print "localize . languages_to_update: %s" % languages_to_update

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

            for lang, files in languages_to_update.iteritems():
                self.do_update(lang)

            # Save the updated hash into the configuration for next time.
            self._Configs.set('localize', 'hashes', json.dumps(self.hashes, separators=(',',':')))

            self.translator = self.get_translator()
            __builtin__.__dict__['_'] = self.handle_translate
        except Exception as e: # if problem with translation, at least return msgid...
            logger.error("Unable to load translations. Gettng null one. Reason: %s" % e)
            logger.error("--------------------------------------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")
            self.translator = self.get_translator(get_null=True)
            __builtin__.__dict__['_'] = self.handle_translate

    def get_system_language(self):
        """
        Returns the system language.
        :return:
        """
        for item in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
            # print "checking for possible default language in: %s" % item
            if item in environ:
                try:
                    return environ.get(item).split(".")[0]
                except:
                    return None

    def get_translator(self, languages=None, get_null=False):
        if get_null is False:
            try:
                # The below code is for both python 2 and 3.
                kwargs = {}
                if sys.version_info[0] > 3:
                    # In Python 2, ensure that the _() that gets installed into built-ins
                    # always returns unicodes.  This matches the default behavior under
                    # Python 3, although that keyword argument is not present in the
                    # Python 3 API.
                    kwargs['unicode'] = True

                if languages is None:
                    languages = []
                    if self.default_lang() not in languages:
                        languages.append(self.default_lang())  # toss in the gateway default language, which may be the system lang
                    if 'en' not in languages:
                        languages.append('en')  # if all else fails, show english.
                kwargs['languages'] = languages
                return gettext.translation('yombo', self.locale_files, **kwargs)
                # print _('', "Current locale: None")
                # print _('webinterface', "There is {num} device turned on.", "There are {num} devices turned on.", 2)
            except Exception as e: # if problem with translation, at least return msgid...
                logger.error("Unable to load translations: %s" % e)
                # we will still install _() so our system doesn't break!
        return gettext.NullTranslations()

    def handle_translate(self, msgctxt, msgid1=None, msgid2=None, num=None, translator=None):
        # fix args...
        # print "msgctxt: %s" % msgctxt
        if msgid1 is None:
            msgid1 = msgctxt
            msgctxt = None

        if translator is None:
            translator = self.translator

        # print "msgctxt= %s, msgid1 =%s, msgid2=%s, num=%s" % (msgctxt, msgid1, msgid2, num)

        msgkey1 = None
        if msgctxt is not None and msgctxt is not "":
            msgkey1 = msgctxt + self.MSGCTXT_GLUE + msgid1
        else:
            msgkey1 = msgid1

        if msgid2 != None and num != None:
            if msgctxt is not None and msgctxt is not "":
                msgkey2 = msgctxt + self.MSGCTXT_GLUE + msgid2
            else:
                msgkey2 = msgid2
            translation = translator.ungettext(msgkey1, msgkey2, num)
            if translation == msgctxt + self.MSGCTXT_GLUE + msgid1:
                return msgid1.format(num=num)
            elif translation == msgctxt + self.MSGCTXT_GLUE + msgid2:
                return msgid2.format(num=num)
            else:
                return translation
        else:
            if msgctxt is None:
                translation = translator.ugettext(msgkey1)
                if translation == msgid1:
                    return msgid1
                else:
                    return translation
            else:
                translation = translator.ugettext(msgkey1)
                if translation == msgctxt + self.MSGCTXT_GLUE + msgid1:
                    return msgid1
                else:
                    return translation

    def do_update(self, language):
        """
        Merges all the files togther and then generates a compiled langauges file (mo)
        :param language:
        :return:
        """
        output_folder = 'usr/locale/' + language + '/LC_MESSAGES'
        # print "files in lang (%s): %s" % (lang, files)

        if not path.exists(output_folder):
            makedirs(output_folder)

        # merge files
        with open(output_folder + '/combined.po', 'w') as outfile:
            # outfile.write("# BEGIN Combining files (%s) for locale: %s\n" % (strftime("%Y-%m-%d %H:%M:%S", gmtime()), language) )
            for fname in self.files[language]:
                # outfile.write("# BEGIN File: %s\n" % fname)
                with open(fname) as infile:
                    outfile.write(infile.read())
                # outfile.write("\n# END File: %s\n\n" % fname)
            # outfile.write("# END Combining files for locale: %s\n" % language)
        po_lang = polib.pofile(output_folder + '/combined.po')
        # po_lang = polib.pofile('yombo/utils/locale/es-yombo.po')
        # print "saving po for labng: %s" % language
        po_lang.save_as_mofile(output_folder + "/yombo.mo")

    def parse_directory(self, directory, has_header=False):
        """
        Checks a directory for any .po or .po.head files to combine them. This allows modules to have translation
        files.
        :param directory: The directory to check.
        :return:
        """
        # print "Checking folder: %s" % directory
        for file in listdir(directory):
            if file.endswith(".po"):
                filename = file.split('.')
                filename = filename[0]
                # print "Checking filename: %s" % file
                name = filename.split('-')
                locale = name[0].split('_')
                if len(locale) == 0 or len(locale) > 2:
                    logger.warn("Bad language_country code split. Must be <ISO 639 lang code>_<ISO 3166 REGION CODE (optional)>: {file}", file=file)

                if len(locale) >= 1:
                    if locale[0].islower() is False:
                        logger.warn("Invalid file, ISO 639 lang code must be lower case: %s", file=file)
                        continue
                    elif len(locale[0]) != 2:
                        logger.warn("Invalid file, ISO 639 lang code must be 2 letters: %s", file=file)
                        continue

                if len(locale) == 2:
                    if locale[0].isupper() is False:
                        logger.warn("Invalid file, ISO 6166 region code must be upper case: %s", file=file)
                        continue
                    elif len(locale[0]) != 2:
                        logger.warn("Invalid file, ISO 6166 region code must be 2 letters: %s", file=file)
                        continue

                logger.debug("Adding file: {file}  to locale: {lang}", file=file, lang=name[0])
                if name[0] not in self.files:
                    if path.exists(directory + "/" + file + ".head"):
                        self.files[name[0]] = []
                        self.files[name[0]].append(directory + "/" + file + ".head")
                        self.files[name[0]].append(directory + "/" + file)
                    else:
                        if has_header == True:
                            self.files[name[0]] = []
                            self.files[name[0]].append(directory + "/" + file)
                        else:
                            logger.warn("Yombo core doesn't have a locale for: {lang}  Cannot merge file. Additionally, no '.head' file exists. (Help link soon.)",
                                lang=name[0])
                else:
                    self.files[name[0]].append(directory + "/" + file)

    def get_ugettext(self, languages):
        """
        Returns a translator function based on a list of languages provided. If request through a webbrowser, send
        the request to :py:meth:parse_accept_language first.

        :param languages: list of locales to check, in order of list items.
        :return:
        """
        # print "requested languages: %s" % languages

        translator = self.get_translator(languages)
        return translator.ugettext

    def get_ungettext(self, languages):
        """
        Returns a translator function based on a list of languages provided. If request through a webbrowser, send
        the request to :py:meth:parse_accept_language first.

        :param languages: list of locales to check, in order of list items.
        :return:
        """
        # print "requested languages: %s" % languages

        translator = self.get_translator(languages)
        return translator.ungettext

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

