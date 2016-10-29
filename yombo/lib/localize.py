"""
Localization and translation for Yombo Gateway.

This is a new library and currently only supporting translations (i18n). To define states, atoms, or system messages
just create a subfolder inside your module. Then, name the file langage.po and include your translations.  Example:
en_US.po, en.po, es.po

These files will be appended to the main gateway language files. Because they are appended, do not include headers in
the PO, just the msgid and msgstr/msgstrs.

If you are supporting a language currently not supported by yombo, create an additional file to contain the language
file header. Using the same example for filenames: en_US.po.base, en.po.base, es.po.base

When the gateway starts up, if the language is unsupported, the system will use your combine your .po.base file with
 your .po file.

The formatting of the .po is the same used for any python gettext po and any PO editor should work. Just make note to
seperate the header portion from the content portion. See the Empty module files for example.

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from time import time
from os import path, listdir, makedirs
import inspect
import sys, gettext
import json
from hashlib import md5
from time import gmtime, strftime

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
        if temp is None:
            self.hashes = {}
        else:
            self.hashes = json.loads(temp)

        self.files = {}

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

        This combines any module .po/.po.base files with the system po files. Then creates .mo binary files.

        # Todo: Create a hash system so we don't have to keep rebuilding everything.
        :return:
        """
        self.parse_directory("yombo/utils/locale", True)

        for item, data in self._Modules._modulesByUUID.iteritems():
            the_directory = path.dirname(path.abspath(inspect.getfile(data.__class__))) + "/locale"
            if path.exists(the_directory):
                self.parse_directory(the_directory)

        print "all files: %s" % self.files
        for lang, files in self.files.iteritems():

            # parse the files quickly and generate a hash. Only re-render po and mo file if needed.
            hash_obj = md5(open(files[0], 'rb').read())
            for fname in files[1:]:
                hash_obj.update(open(fname, 'rb').read())
            checksum = hash_obj.hexdigest()
            print "checksum: %s" % checksum
            if lang in self.hashes:
                if checksum == self.hashes[lang]:
                    continue
            else:
                self.hashes[lang] = checksum

            po = None
            output_folder = 'usr/locale/' + lang + '/LC_MESSAGES'
            print "files in lang (%s): %s" % (lang, files)

            if not path.exists(output_folder):
                makedirs(output_folder)

            # merge files
            with open(output_folder + '/yombo.po', 'w') as outfile:
                outfile.write("# BEGIN Combining files (%s) for locale: %s\n" % (strftime("%Y-%m-%d %H:%M:%S", gmtime()), lang) )
                for fname in files:
                    outfile.write("# BEGIN File: %s\n" % fname)
                    with open(fname) as infile:
                        outfile.write(infile.read())
                    outfile.write("\n# END File: %s\n\n" % fname)
                outfile.write("# END Combining files for locale: %s\n" % lang)

            # save binary file
            po = polib.pofile(output_folder + "/yombo.po")
            print po.save_as_mofile(output_folder + "/yombo.mo")
            del po

        # Save the updated hash into the configuration for next time.
        print "hashes: %s" % self.hashes
        self._Configs.set('localize', 'hashed', json.dumps(self.hashes, separators=(',',':')))
        print self._Configs.get('localize', 'hashed')

        # The below code is for both python 2 and 3.
        kwargs = {}
        if sys.version_info[0] > 3:
            # In Python 2, ensure that the _() that gets installed into built-ins
            # always returns unicodes.  This matches the default behavior under
            # Python 3, although that keyword argument is not present in the
            # Python 3 API.
            kwargs['unicode'] = True
        gettext.install('yombo', 'usr/locale', **kwargs)


    def parse_directory(self, directory, primary=False):
        print "Checking folder: %s" % directory
        for file in listdir(directory):
            if file.endswith(".po"):
                filename = file.split('.')
                filename = filename[0]
                print "Checking filename: %s" % file
                name = filename.split('-')
                locale = name[0].split('_')
                if len(locale) == 0 or len(locale) > 2:
                    print "Bad language_country code split. Must be <ISO 639 lang code>_<ISO 3166 REGION CODE (optional)>: %s" % file

                if len(locale) >= 1:
                    if locale[0].islower() is False:
                        print "Invalid file, ISO 639 lang code must be lower case: %s" % file
                        continue
                    elif len(locale[0]) != 2:
                        print "Invalid file, ISO 639 lang code must be 2 letters: %s" % file
                        continue

                if len(locale) == 2:
                    if locale[0].isupper() is False:
                        print "Invalid file, ISO 6166 region code must be upper case: %s" % file
                        continue
                    elif len(locale[0]) != 2:
                        print "Invalid file, ISO 6166 region code must be 2 letters: %s" % file
                        continue

                print "adding file: %s  to locale: %s" % (file, name[0])
                if primary:
                    if name[0] not in self.files:
                        self.files[name[0]] = []
                    self.files[name[0]].append(directory + "/" + file)
                else:
                    if name[0] not in self.files:
                        if path.exists(directory + "/" + file + ".base"):
                            self.files[name[0]] = []
                            self.files[name[0]].append(directory + "/" + file)
                        else:
                            print "Yombo core doesn't have a locale for: %s   Cannot merge file. Additionally, no '.base' file exists. (Help link soon.)"
                    else:
                        self.files[name[0]].append(directory + "/" + file)

    def get_strings(self, accept_language, type):
        accept_languages = self.parse_accept_language(accept_language)

        strings = getattr(self, type)

        results = {}
        for msgid, languages in strings.iteritems():

            for accept_lang, number in accept_languages:
                if accept_lang in languages:
                    results[msgid] = languages[accept_lang]
                else:
                    results[msgid] = ""
        return results

    def parse_accept_language(self, accept_language):
        """
        From: https://siongui.github.io/2012/10/11/python-parse-accept-language-in-http-request-header/
        Modified for yombo...
        :param accept_language: The accept language header from a browser, or a string in the same format
        :return:
        """
        languages = accept_language.split(",")
        locale_q_pairs = []

        for language in languages:
            if language.split(";")[0] == language:
                # no q => q = 1
                language = language.strip()
                lang_parts = language.split('-')
                locale_q_pairs.append((lang_parts[0], "1"))
            else:
                locale = language.split(";")[0].strip()
                q = language.split(";")[1].split("=")[1]
                lang_parts = locale.split('-')
                locale_q_pairs.append((lang_parts[0], q))

        return locale_q_pairs
