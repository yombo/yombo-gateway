"""
Determine who called a function.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: See LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/utils.html>`_
"""
# Import python libraries
import inspect
import sys


def caller_string(offset=None, prefix=None):
    """
    Gets the python file, class, and method that was called. For example, if this was
    called from yombo.lib.amqp within the class "AMQP" in the function new, the results
    would look like: "F:yombo.lib.amqp C:AMQP Md:new"

    If this wasn't called from within a class, it would look like:
    "F:yombo.core.soemthing M:washere"

    If gateway_id is supplied, it will now look like:
    "G:zbc1230 F:yombo.lib.amqp C:AMQP M:new"

    The offset is used to determine how far back in the call stack it should look. For example,
    if this function was called within yombo.lib.module.somemodule and want to get the method
    that directly called it, use offset "1".  If the previous caller is desired, use 2, etc.

    :param offset: How far back to go in the stack. Default is 1, use 0 for current function.
    :param prefix: What to prefix the string with: Ex,"g=<gw_id>"
    :return:
    """
    return caller(offset=offset, prefix=prefix)["string"]


def caller(offset=None, prefix=None):
    """
    Gets details about the caller. Returns a dictionary with the following items:

    * file - The python module that is calling this.
    * class - The class the call came from.
    * method - Which method the call came from.
    * string - A string represention of the above: f=<module.name>,c=<class name>,m=<method name>
      * If any of the above items is None, than the value is ommited.

    The offset is used to determine how far back in the call stack it should look. For example,
    if this function was called within yombo.lib.module.somemodule and want to get the method
    that directly called it, use offset "1".  If the previous caller is desired, use 2, etc.

    :param offset: How far back to go in the stack. Default is 1, use 0 for current function.
    :param prefix: What to prefix the string with: Ex,"g=<gw_id>"
    :return:
    """
    offset = offset if isinstance(offset, int) else 1
    offset = offset + 1
    calling_frame = sys._getframe(offset)
    mod = inspect.getmodule(calling_frame)
    results = {
        "file": mod.__name__,
        "method": calling_frame.f_code.co_name,
    }
    if "self" in calling_frame.f_locals:
        results["class"] = calling_frame.f_locals['self'].__class__.__name__
        results["string"] = f"f={mod.__name__},c={calling_frame.f_locals['self'].__class__.__name__}" \
                            f",m={calling_frame.f_code.co_name}"
    else:
        results["string"] = f"f={mod.__name__},m={calling_frame.f_code.co_name}"
    if prefix is not None:
        results["string"] = f"{prefix},{results['string']}"
        results["prefix"] = prefix
    return results
