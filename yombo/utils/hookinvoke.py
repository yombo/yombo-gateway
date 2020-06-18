"""
A couple of shortcut functions to call hooks. Used by libraries and modules to call hooks in other libraries
and modules.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2016-2020 by Yombo.
:license: See LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/hookinvoke.html>`_
"""
from twisted.internet.defer import inlineCallbacks

from yombo.utils.dictionaries import recursive_dict_merge


@inlineCallbacks
def global_invoke_all(hook, called_by, **kwargs):
    """
    Call all hooks in libraries and modules. Basically a shortcut for calling module_invoke_all and libraries_invoke_all
    methods.

    :param hook: The hook name to call.
    :param called_by: Reference of the caller.
    :param kwargs: kwargs to send to the function.
    :return: a dictionary of results.
    """
    # print(f"global_invoke_all: {hook}, {called_by}, {kwargs}")
    lib_results = yield get_component("yombo.lib.loader").invoke_all("library",
                                                                     hook,
                                                                     called_by=called_by,
                                                                     **kwargs)
    modules_results = yield get_component("yombo.lib.loader").invoke_all("module",
                                                                         hook,
                                                                         called_by=called_by,
                                                                         **kwargs)
    return recursive_dict_merge(modules_results, lib_results)


@inlineCallbacks
def global_invoke_libraries(hook, called_by, **kwargs):
    """
    Call all hooks in libraries and modules. Basically a shortcut for calling module_invoke_all and libraries_invoke_all
    methods.

    :param hook: The hook name to call.
    :param called_by: Reference of the caller.
    :param kwargs: kwargs to send to the function.
    :return: a dictionary of results.
    """
    lib_results = yield get_component("yombo.lib.loader").invoke_all("library",
                                                                     hook,
                                                                     called_by=called_by,
                                                                     # stop_on_error=True,
                                                                     **kwargs)
    return lib_results


@inlineCallbacks
def global_invoke_modules(hook, called_by, **kwargs):
    """
    Call all hooks in libraries and modules. Basically a shortcut for calling module_invoke_all and libraries_invoke_all
    methods.

    :param hook: The hook name to call.
    :param called_by: Reference of the caller.
    :param kwargs: kwargs to send to the function.
    :return: a dictionary of results.
    """
    modules_results = yield get_component("yombo.lib.loader").invoke_all("module",
                                                                         hook,
                                                                         called_by=called_by,
                                                                         # stop_on_error=True,
                                                                         **kwargs)
    return modules_results


def get_component(name):
    """
    Return loaded component (module or library). This can be used to find
    other modules or libraries. The getComponent uses the :ref:`FuzzySearch <fuzzysearch>`
    class to make searching easier, but can only be off one or two letters
    due to importance of selecting the correct library or module.

    :raises KeyError: When the requested component cannot be found.
    :param name: The name of the component (library or module) to find.  Returns a
        pointer to the object so it's functions and attributes can be accessed.
    :type name: string
    :return: Pointer to requested library or module.
    :rtype: Object reference
    """
    if not hasattr(get_component, "components"):
        from yombo.lib.loader import get_the_loaded_components
        get_component.components = get_the_loaded_components()
    try:
        return get_component.components[name.lower()]
    except KeyError:
        raise KeyError("No such loaded component:" + str(name))
