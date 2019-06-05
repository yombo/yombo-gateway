from twisted.internet.defer import inlineCallbacks

@inlineCallbacks
def global_invoke_all(hook, **kwargs):
    """
    Call all hooks in libraries and modules. Basically a shortcut for calling module_invoke_all and libraries_invoke_all
    methods.

    :param hook: The hook name to call.
    :param kwargs: kwargs to send to the function.
    :return: a dictionary of results.
    """
    lib_results = yield get_component("yombo.gateway.lib.loader").library_invoke_all(hook, True, **kwargs)
    modules_results = yield get_component("yombo.gateway.lib.modules").module_invoke_all(hook, True, **kwargs)
    # print(f"hook lib_results: {lib_results}")
    # print(f"hook modules_results: {modules_results}")
    return dict_merge(modules_results, lib_results)


@inlineCallbacks
def global_invoke_libraries(hook, **kwargs):
    """
    Call all hooks in libraries and modules. Basically a shortcut for calling module_invoke_all and libraries_invoke_all
    methods.

    :param hook: The hook name to call.
    :param kwargs: kwargs to send to the function.
    :return: a dictionary of results.
    """
    lib_results = yield get_component("yombo.gateway.lib.loader").library_invoke_all(hook, True, **kwargs)
    return lib_results


@inlineCallbacks
def global_invoke_modules(hook, **kwargs):
    """
    Call all hooks in libraries and modules. Basically a shortcut for calling module_invoke_all and libraries_invoke_all
    methods.

    :param hook: The hook name to call.
    :param kwargs: kwargs to send to the function.
    :return: a dictionary of results.
    """
    modules_results = yield get_component("yombo.gateway.lib.modules").module_invoke_all(hook, True, **kwargs)
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

def dict_merge(original, changes):
    """
    Recursively merges a dictionary with any changes. Sub-dictionaries won't be overwritten - just updated.

    *Usage**:

    .. code-block:: python

        my_information = {
            "name": "Mitch"
            "phone: {
                "mobile": "4155551212"
            }
        }

        updated_information = {
            "phone": {
                "home": "4155552121"
            }
        }

        print(dict_merge(my_information, updated_information))

    # Output:

    .. code-block:: none

        {
            "name": "Mitch"
            "phone: {
                "mobile": "4155551212",
                "home": "4155552121"
            }
        }
    """
    for key, value in original.items():
        if key not in changes:
            changes[key] = value
        elif isinstance(value, dict):
            dict_merge(value, changes[key])
    return changes
