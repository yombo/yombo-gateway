#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""

.. note::

  For more information see: `Entity Core @ Module Development <https://yombo.net/docs/core/entity>`_

Used by all classes to add various magic features.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/core/entity.html>`_
"""
from os import getcwd
import sys
import traceback
from typing import Any, ClassVar
from yombo.core.log import get_logger

logger = get_logger("core.entity")


class Entity:
    """All classes should inherit this class first. This setups basic attributes that are helpfull to all classes."""
    _Root: ClassVar["yombo.core.library.Library"] = None
    _Entity_type: ClassVar[str] = "unknown"
    _Entity_label_attribute: ClassVar[str] = "unknown"
    _Name: str
    _ClassPath: str
    _FullName: str
    _Parent: Any
    _working_dir: str = None
    _app_dir: str = None

    @classmethod
    def _Configure_Entity_Class_Library_References_INTERNAL_ONLY_(cls, magic_library_attributes) -> None:
        for current_library_name, current_library_reference in magic_library_attributes.items():
            setattr(cls, current_library_name, current_library_reference)

    @classmethod
    def _Configure_Entity_Class_BASIC_REFERENCES_INTERNAL_ONLY_(cls, app_dir: str = None,
            working_dir: str = None) -> None:
        cls._app_dir = app_dir
        cls._working_dir = working_dir

    @property
    def _gateway_id(self) -> str:
        return self._Root.gateway_id

    @_gateway_id.setter
    def _gateway_id(self, val: str) -> None:
        """ Does nothing. """
        return

    @property
    def _is_master(self) -> bool:
        return self._Root.is_master

    @property
    def _is_current_master(self) -> bool:
        return self._Root.is_current_master

    @_is_master.setter
    def _is_master(self, val: bool) -> None:
        """ Does nothing. """
        return

    @property
    def _master_gateway_id(self) -> str:
        """ Does nothing. """
        return self._Root.master_gateway_id

    def __init__(self, parent, *args, **kwargs) -> None:
        if hasattr(self, "_Entity_type") in (False, "unknown"):
            self._Entity_type: str = f"unknown-{self.__class__.__name__}"

        if hasattr(self, "_Entity_label_attribute") in (False, "unknown"):
            self._Entity_label_attribute: str = "machine_label"

        self._Parent = parent

        try:  # Some exceptions not being caught & displayed. So, catch, display and release.
            self._Name = self.__class__.__name__
            file = sys.modules[self.__class__.__module__].__file__
            self._ClassPath = file[len(getcwd())+1:].split(".")[0].replace("/", ".")
            self._FullName = f"{self._ClassPath}:{self._Name}"
            super().__init__(*args, **kwargs)
        except Exception as e:
            logger.error("---==(Entity caught init in '{name}': {e})==--", name=self._Name, e=e)
            logger.error("--------------------------------------------------------")
            logger.error("{error}", error=sys.exc_info())
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.print_exc(file=sys.stdout))
            logger.error("--------------------------------------------------------")
            raise e
