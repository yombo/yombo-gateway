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
    def _init_(self, loader):
        pass

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
        i18n_strings = global_invoke_all('i18n')
        compiled_i18n = {}

        for component, msgids in i18n_strings.iteritems():
            for msgid, languages in msgids.iteritems():
                for lang, msgstr in languages.iteritems():
                    if lang not in compiled_i18n:
                        compiled_i18n[lang] = []
                    compiled_i18n[lang].append({'msgid': msgid, 'msgstr': msgstr})

        # Now do something with it! Use polib

