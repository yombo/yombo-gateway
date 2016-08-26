"""
Localization for Yombo Gateway. The goal is to support translations and localization.

To just get started: translation first!

*Usage**:

.. code-block:: python

   if self._Atom['os'] != None:
       logger.debug("Running on operating system: {operatingsystem}", operatingsystem=self._Atom['os'])

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from time import time

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboHookStopProcessing
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import global_invoke_all

logger = get_logger("library.localize")


class Localize(YomboLibrary):
    """
    Provides the Atom information for modules and libraries to get more
    information about the underlying system.
    """
    def _init_(self):
        self.atoms = {}  # All atom translations
        self.configuration = {}  # All configuration translations
        self.system_messages = {}  # Various system messages.
        self.states = {}  # All state translations

        import sys, gettext
        kwargs = {}
        if sys.version_info[0] > 3:
            # In Python 2, ensure that the _() that gets installed into built-ins
            # always returns unicodes.  This matches the default behavior under
            # Python 3, although that keyword argument is not present in the
            # Python 3 API.
            kwargs['unicode'] = True
        gettext.install('yombo', 'locale', **kwargs)

    def _load_(self):
        pass

    def _start_(self):
        pass

    def _stop_(self):
        pass

    def _unload_(self):
        pass

    def _module_load_(self, **kwargs):
        """
        Called after _preload_ is called for all the modules. Gets a list of all possible translations.

        **Usage**:

        .. code-block:: python

           def ModuleName_i18n(self, **kwargs):
               return [{'mymodule.section.hello': {
                           'en': 'hello',
                           'es': 'hola',
                           },
                       },
               }]
        """
#         temp_strings = global_invoke_all('i18n_states')
#         for component, strings in temp_strings.iteritems():
#             for string in strings:
#                 print "string: %s" % string
#                 for label, languages in string.iteritems():
#                     print "label: %s" % label
#                     for language, the_string in languages.iteritems():
#                         print "language: %s, data: %s" % (language, the_string)
#                         if language not in self.states:
#                             self.states[language] = []
#                         self.states[language].append({'msgid': label, 'msgstr': the_string})

        temp_strings = global_invoke_all('i18n_states')
        for component, strings in temp_strings.iteritems():
#            print "component: %s, msgids: %s" % (component, msgids)
            for string in strings:
#                print "string: %s" % string
                for msgid, languages in string.iteritems():
#                    print "label: %s" % msgid
                    for language, the_string in languages.iteritems():
#                        print "language: %s, the_string: %s" % (language, the_string)
                        if msgid not in self.states:
                            self.states[msgid] = {}
                        if language not in self.states[msgid]:
                            self.states[msgid][language] = {}
                        self.states[msgid][language] = the_string

        temp_strings = global_invoke_all('i18n_atoms')
        for component, strings in temp_strings.iteritems():
#            print "component: %s, msgids: %s" % (component, msgids)
            for string in strings:
#                print "string: %s" % string
                for msgid, languages in string.iteritems():
#                    print "label: %s" % msgid
                    for language, the_string in languages.iteritems():
#                        print "language: %s, the_string: %s" % (language, the_string)
                        if msgid not in self.states:
                            self.atoms[msgid] = {}
                        if language not in self.atoms[msgid]:
                            self.atoms[msgid][language] = {}
                        self.atoms[msgid][language] = the_string

        temp_strings = global_invoke_all('i18n_configurations1')
        for component, strings in temp_strings.iteritems():
#            print "component: %s, msgids: %s" % (component, msgids)
            for string in strings:
#                print "string: %s" % string
                for msgid, languages in string.iteritems():
#                    print "label: %s" % msgid
                    for language, the_string in languages.iteritems():
#                        print "language: %s, the_string: %s" % (language, the_string)
                        if msgid not in self.configuration:
                            self.configuration[msgid] = {}
                        if language not in self.configuration[msgid]:
                            self.configuration[msgid][language] = {}
                        self.configuration[msgid][language] = the_string


    def get_strings(self, accept_language, type):
        accept_languages = self.parse_accept_language(accept_language)

        strings = getattr(self, type)

#        print accept_languages
#        print strings

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
