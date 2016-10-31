"""
Localization and translation for Yombo Gateway.

This is a new library and currently only supporting translations (i18n). To define states, atoms, or system messages
just create a subfolder inside your module. Then, name the file langage.po and include your translations.  Example:
en_US.po, en.po, es.po

These files will be appended to the main gateway language files. Because they are appended, do not include headers in
the PO, just the msgid and msgstr/msgstrs.

If you are supporting a language currently not supported by yombo, create an additional file to contain the language
file header. Using the same example for filenames: en_US.po.head, en.po.head, es.po.head

When the gateway starts up, if the language is unsupported, the system will use your combine your .po.head file with
 your .po file.

The formatting of the .po is the same used for any python gettext po and any PO editor should work. Just make note to
seperate the header portion from the content portion. See the Empty module files for example.

:copyright: Copyright 2016 by Yombo.
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
    def _init_(self):
        self._Database = self._Loader['localdb']
        temp = self._Configs.get('localize', 'hashes')
        self.default_lang = self._Configs.get('localize', 'default_lang', 'en')
        if temp is None:
            self.hashes = {}
        else:
            self.hashes = json.loads(temp)

        self.files = {}
        self.locale_files = abspath('.') + "/usr/locale/"

    def _load_(self):
        pass

    def _start_(self):
        pass

    def _stop_(self):
        pass

    def _unload_(self):
        pass

    def _module_init_(self, **kwargs):
        """
        Called just before modules get their _init_ called. However, all the gateway libraries are loaded.

        This combines any module .po/.po.head files with the system po files. Then creates .mo binary files.

        Uses a basic MD5 hash to validate if files have changes or not between runs. This prevents the files to be
        rebuilt on each run.
        :return:
        """
        self.parse_directory("yombo/utils/locale", has_header=True)

        for item, data in self._Modules._modulesByUUID.iteritems():
            the_directory = path.dirname(path.abspath(inspect.getfile(data.__class__))) + "/locale"
            if path.exists(the_directory):
                self.parse_directory(the_directory)

        print "localize . self.files: %s" % self.files
        languages_to_update = {}

        #always check english. If it gets updated, we need to update them all!
        hash_obj = md5(open(self.files['en'][0], 'rb').read())
        for fname in self.files['en'][1:]:
            hash_obj.update(open(fname, 'rb').read())
        checksum = hash_obj.hexdigest()
        if checksum != self.hashes['en']:
            self.hashes = {}

        for lang, files in self.files.iteritems():
            # parse the files quickly and generate a hash. Only re-render po and mo file if needed.
            hash_obj = md5(open(files[0], 'rb').read())
            for fname in files[1:]:
                hash_obj.update(open(fname, 'rb').read())
            checksum = hash_obj.hexdigest()
            print "self.hashes: %s" % self.hashes
            print "checksum: %s" % checksum
            if lang in self.hashes:
                #print "self.hashes[lang]: %s" % self.hashes[lang]
                if checksum == self.hashes[lang]:
                    continue

                languages_to_update[lang] = 'aaa'
            self.hashes[lang] = checksum

        # Lets validate the default language has actual translations. If not, we check the environment for possibilities
        if self.default_lang != 'en':
            if self.default_lang not in self.files:
                lang_parts = self.default_lang.split('_')
                if lang_parts[0] in self.files:
                    self.default_lang = lang_parts[0]
                else:
                    self.default_lang = None
                    # still can't find a good default language amongst the possible ones. Lets try checking envrionment.
                    for item in ('LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG'):
                        print "checking for possible default language in: %s" % item
                        if item in environ:
                            self.default_lang = environ.get(item).split(".")[0]
                            # self.default_lang = temp_lang[0]
                            if self.default_lang not in self.files:
                                lang_parts = self.default_lang.split('_')
                                if lang_parts[0] in self.files:
                                    self.default_lang = lang_parts[0]

        if self.default_lang is None:
            self.default_lang = 'en'

        if 'en' in languages_to_update and self.default_lang not in languages_to_update:
            languages_to_update[self.default_lang] = 'aaa'

        print "localize . languages_to_update: %s" % languages_to_update

        # we do english first, sorry. It's the base language.
        if 'en' in languages_to_update:
            self.do_update('en')
            del languages_to_update['en']

        # do system default language next.
        if self.default_lang in languages_to_update:
            self.do_update(self.default_lang)
            del languages_to_update[self.default_lang]

        self.default_lang = 'es'
        self._States['localize.default_language'] = self.default_lang

        for lang, files in languages_to_update.iteritems():
            self.do_update(lang)

        # Save the updated hash into the configuration for next time.
        # print "hashes: %s" % self.hashes
        print "setting hashes: %s" % json.dumps(self.hashes, separators=(',',':'))
        self._Configs.set('localize', 'hashes', json.dumps(self.hashes, separators=(',',':')))
        # print self._Configs.get('localize', 'hashed')

        # The below code is for both python 2 and 3.
        kwargs = {}
        if sys.version_info[0] > 3:
            # In Python 2, ensure that the _() that gets installed into built-ins
            # always returns unicodes.  This matches the default behavior under
            # Python 3, although that keyword argument is not present in the
            # Python 3 API.
            kwargs['unicode'] = True
        gettext.install('yombo', self.locale_files, **kwargs)


    def do_update(self, language):
        output_folder = 'usr/locale/' + language + '/LC_MESSAGES'
        # print "files in lang (%s): %s" % (lang, files)

        if not path.exists(output_folder):
            makedirs(output_folder)

        # merge files
        with open(output_folder + '/combined.po', 'w') as outfile:
            outfile.write("# BEGIN Combining files (%s) for locale: %s\n" % (strftime("%Y-%m-%d %H:%M:%S", gmtime()), language) )
            for fname in self.files[language]:
                outfile.write("# BEGIN File: %s\n" % fname)
                with open(fname) as infile:
                    outfile.write(infile.read())
                outfile.write("\n# END File: %s\n\n" % fname)
            outfile.write("# END Combining files for locale: %s\n" % language)

        # print "do_update: language: %s" % language
        # print "do_update: default lang: %s" % self.default_lang
        try:
            if language == 'en':
                po_en = polib.pofile('usr/locale/en/LC_MESSAGES/combined.po')
                po_en.save_as_mofile(output_folder + "/yombo.mo")
            elif language == self.default_lang:
                po_en = polib.pofile('usr/locale/en/LC_MESSAGES/combined.po')
                po_default = polib.pofile('usr/locale/%s/LC_MESSAGES/combined.po' % self.default_lang)

                self.merge(po_en, po_default)

                # for entry in po_en:
                #     print "item2: %s (%s) %s" % (entry.msgid, entry.previous_msgctxt, entry.msgstr)

                po_en.save(output_folder + "/lang_merged.po")  # this is really the merged file...
                po_en.save_as_mofile(output_folder + "/yombo.mo")
            else:
                po_default = polib.pofile('usr/locale/%s/LC_MESSAGES/combined.po' % self.default_lang)
                po_lang = polib.pofile('usr/locale/%s/LC_MESSAGES/combined.po' % language)

                self.merge(po_default, po_lang)

                po_lang.save(output_folder + "/lang_merged.po")
                po_lang.save_as_mofile(output_folder + "/yombo.mo")
        except Exception as e:
            print "Translation error: %s" % e

    def merge(self, existing, tomerge):
        """
        Merges a locale onto a default langauge base. This results in strings preferencing user locale, gateway
        define default set by gateway admin, system locale, then finally english.
        :return:
        """
        # print "existing: %s" % existing
        # print "tomerge: %s" % tomerge
        existing_entries = dict((entry.msgid, entry) for entry in existing)
        tomerge_entries = dict((entry.msgid, entry) for entry in tomerge)
#        print "existing_entries: %s" % existing_entries
        print "tomerge_entries: %s" % tomerge_entries

        for msgid, tomerge_entry in tomerge_entries.iteritems():
            if msgid not in existing_entries:
                print "adding new entry: %s" % tomerge_entry.msgstr
                existing.append(tomerge_entry)
            else:
                print "updating: %s" % tomerge_entry.msgstr
                # existing_entries.get(entry.msgid) =
                previous_msgctxt = existing_entries[msgid].msgstr
                if previous_msgctxt == '':
                    previous_msgctxt = existing_entries[msgid].msgid
                existing_entries[msgid].merge(tomerge_entries[msgid])
                existing_entries[msgid].previous_msgctxt = previous_msgctxt

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

    def get_translation(self, languages):
        """
        Returns a translator function based on a list of languages provided. If request through a webbrowser, send
        the request to :py:meth:parse_accept_language first.

        :param languages: list of locales to check, in order of list items.
        :return:
        """

        # The below code is for both python 2 and 3.
        kwargs = {}
        if sys.version_info[0] > 3:
            # In Python 2, ensure that the _() that gets installed into built-ins
            # always returns unicodes.  This matches the default behavior under
            # Python 3, although that keyword argument is not present in the
            # Python 3 API.
            kwargs['unicode'] = True
        kwargs['languages'] = languages
        trans = gettext.translation('yombo', '/home/mitch/Yombo/yombo-gateway/usr/locale', **kwargs)
        return trans.ugettext

    def parse_accept_language(self, accept_language):
        """
        From: https://siongui.github.io/2012/10/11/python-parse-accept-language-in-http-request-header/
        Modified for yombo...
        :param accept_language: The accept language header from a browser, or a string in the same format
        :return:
        """
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
        if self.default_lang not in locales:
            locales.append(self.default_lang)  # toss in the gateway default language, which may be the system lang
        if 'en' not in locales:
            locales.append('en')  # if all else fails, show english.
        return locales

