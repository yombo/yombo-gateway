"""
Gets the user's session (either websession or authkey) for web requests. Typically used as a method decorator
just after the Klein (webapp) route call: @get_session(auth_required=True, api=True)

If auth_required is True, will redirect the user to the login page if they are not authenticated.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/webinterface/auth.html>`_
"""
from functools import wraps
from inspect import signature
import json
import msgpack
from ratelimit import RateLimitException
import traceback
from typing import Optional, Union

from twisted.internet.defer import inlineCallbacks

from yombo.constants import CONTENT_TYPE_JSON, CONTENT_TYPE_MSGPACK
from yombo.constants.webinterface import IGNORED_EXTENSIONS
from yombo.constants.exceptions import ERROR_CODES
from yombo.core.exceptions import (YomboWarning, YomboNoAccess, YomboInvalidValidation, YomboWebinterfaceError,
                                   YomboMarshmallowValidationError)
from yombo.core.log import get_logger
from yombo.lib.webinterface.response_tools import common_headers
from yombo.utils import bytes_to_unicode, random_string
from yombo.utils.datatypes import coerce_value

logger = get_logger("library.webinterface.auth")
webinterface = None  # Set by setup_yombo_reference()


def setup_webinterface_reference(incoming_webinterface):
    """
    Setup a reference to the webinterface, called by webinterface itself during _init_().

    :param incoming_webinterface: Pointer to the webinterace library.
    :return:
    """
    global webinterface
    webinterface = incoming_webinterface


def update_request(request, api):
    """
    Modifies the request to add "received_cookies in unicode. Also, adds a "args"
    attribute that contains the incoming arguments, but in unicode. Also adds "_" to the
    templates, but it for the current user's language.

    Finally, it adds cache-control and expires items to ensure the content isn't cached.

    :param request:
    :return:
    """
    request.auth = None
    if api in ("true", True, 1, "yes"):
        request.api = True
    else:
        request.api = False

    request.received_cookies = bytes_to_unicode(request.received_cookies)
    request.args = bytes_to_unicode(request.args)
    request.request_id = random_string(length=25)
    request.setHeader("Cache-Control", "no-cache, no-store, must-revalidate")  # don't cache!
    request.setHeader("Expires", "-1")  # don't cache!

    # Make uniform arguments available as 'processed_arguments'. First, if the request is type
    # POST, PATCH, or PUT, then first try to decode the body request. If not, then use the query string args.

    request.processed_body = None
    request.processed_body_encoding = None

    if bytes_to_unicode(request.method).lower() in ("post", "patch", "put"):
        content_type = bytes_to_unicode(request.getHeader("content-type"))
        if isinstance(content_type, str):
            content_type = content_type.lower()
        else:
            content_type = ""

        if content_type == CONTENT_TYPE_JSON:
            try:
                request.processed_body = bytes_to_unicode(json.loads(request.content.read()))
                request.processed_body_encoding = "json"
            except Exception as e:
                logger.info("Error decoding web request 'json' data: {e}", e=e)
        elif content_type == CONTENT_TYPE_MSGPACK:
            try:
                request.processed_body = bytes_to_unicode(msgpack.unpackb(request.content.read()))
                request.processed_body_encoding = "msgpack"
            except Exception as e:
                logger.info("Error decoding web request 'msgpack' data: {e}", e=e)
    common_headers(request)


def get_session(auth_required: Optional[bool] = None,
                create_session: Optional[bool] = None,
                login_redirect: Optional[str] = None,
                api: Optional[bool] = None,
                access_platform: Optional[str] = None, access_item: Optional[str] = None,
                access_action: Optional[str] = None, *args, **kwargs):
    """
    Web interface decorator that gets the user's session, either websession or authkey.

    If checking for access, must supply all access* items.

    :param auth_required: If true, user must be authenticated to access the resource..
    :param create_session: If true, an empty session is created for tracking.
    :param login_redirect: If set, and user is required to login, redirect here after login.
    :param api: If true, treat the request as an API request and output errors in JSON/MSGPack form.
    :param access_platform: The platform to ensure the user has access to.
    :param access_item: The item ID or '*' fo any/all.
    :param access_action: Action being performed, such as: modify, delete, view, control...
    :param args:
    :param kwargs:
    :return:
    """
    def deco(f):
        @wraps(f)
        @inlineCallbacks
        def wrapped_f(request, *a, **kw):
            """Request is sent in by the webapp.route() wrapper."""
            global webinterface
            nonlocal f, auth_required, create_session, login_redirect, api, access_platform, access_item, access_action

            update_request(request, api)  # Add extra items to the request.
            host = request.getHeader("host")
            if host is None:
                logger.info("Discarding request, appears to be malformed host header")
                return webinterface.render_error(request,
                                                 title="Malformed request headers.",
                                                 messages="The request was invalid, malformed request.",
                                                 response_code=400,
                                                 error_core="mfh-1932")
            host_info = host.split(":")
            request.requestHeaders.setRawHeaders("host_name", [host_info[0]])

            if len(host_info) > 1:
                request.requestHeaders.setRawHeaders("host_port", [host_info[1]])

            # For API requests, system must be fully started.
            # if api is True:
            if webinterface.web_interface_fully_started is False:
                return webinterface.render_template(request,
                                                    "pages/misc/still_loading.html",
                                                    )

            # If the path is /api/*, and the method is OPTIONS, send just the CORS response.
            if request.method.decode().upper() == "OPTIONS" and request.path.decode().strip().startswith("/api/"):
                return

            # Look for a session in either authkeys or websessions.
            try:
                request.auth = webinterface._AuthKeys.get_session_from_request(request)
            except YomboWarning as e:
                logger.debug("Login not found by authkey. {e}", e=e)
                try:
                    request.auth = yield webinterface._WebSessions.get_session_from_request(request)
                except YomboWarning as e:
                    logger.info("Login not found by cookie. {e}", e=e)
                    request.auth = None

            # Create session if login_redirect is set or create_session is True.
            if login_redirect is not None:
                create_session = True

            # 'Touch' any auth items for last_updated_at, if it's a happy URL.
            if request.auth is not None:
                url_path = request.path.decode().strip()
                if any(ext in url_path for ext in IGNORED_EXTENSIONS) is False:
                    request.auth.touch()

            try:
                if create_session is True and request.auth is None:
                    # print(f"run_first: before session created: {session}")
                    request.auth = yield webinterface._WebSessions.create_from_web_request(request)
                    # print(f"run_first: created new session: {session.asdict()}")
            except RateLimitException as e:
                logger.warn("Too many sessions being created, stopping this one!")
                return webinterface.render_api_error(request,
                                                     error_code="toofast-dj923h",
                                                     title="Too many requests",
                                                     messages="Client is making too many requests, slow down.",
                                                     response_code=429)

            if request.auth is not None:
                request.auth.touch()

            # Now validate if the session is any good.
            if auth_required is True and (request.auth is None or request.auth.is_valid() is False):
                if request.auth is not None:
                    setup_login_redirect(request, login_redirect)
                return return_need_login(webinterface, request, **kwargs)

            # if api is True:
                # results = webinterface.check_idempotence(request, session)
                # if isinstance(results, bool) is False:
                #     return results

            if access_platform is not None and access_item is not None and access_action is not None:
                try:
                    request.auth.is_allowed(access_platform, access_action, access_item)
                except YomboNoAccess as e:
                    return return_no_access(webinterface, request, e)

            results = yield auth_run_wrapped_function(f, webinterface, request, *a, **kw)
            return webinterface.render_encode_output(request, results)
        return wrapped_f
    return deco


@inlineCallbacks
def auth_run_wrapped_function(function_to_call, webinterface, request, *args, **kwargs):
    """
    Wraps the callback in a try/except to list the exception details. This allows more detailed handling
    of errors. Displays either JSON or HTML, based on the incoming request.

    :param function_to_call: Callable to call.
    :param webinterface: Reference to the webinterface library.
    :param request: The request.
    :param args: Args to pass to function.
    :param kwargs: Additional kwargs to pass to function.
    :return:
    """
    def call(function_to_call, *args, **kwargs):
        return function_to_call(*args, **kwargs)

    arguments = signature(function_to_call)
    request.request_context = f"{function_to_call.__module__}.{function_to_call.__name__}"
    if "session" in arguments.parameters:
        args = (request.auth,) + args

    try:
        results = yield call(function_to_call, webinterface, request, *args, **kwargs)
        return results
    except (YomboWarning, YomboInvalidValidation, YomboMarshmallowValidationError) as e:
        return webinterface.render_error(request,
                                         title=e.title,
                                         messages=e.errors,
                                         response_code=e.response_code,
                                         error_code=e.error_code,
                                         )
    except YomboWebinterfaceError as e:
        return webinterface.render_error(request,
                                         title=e.title,
                                         messages=e.errors,
                                         response_code=e.response_code,
                                         error_code=e.error_code,
                                         )
    # except KeyError as e:
        # missing = ERROR_CODES[404]
        # message = str(e)
        # if (message[0] == message[-1]) and message.startswith(("'", '"')):
        #     message = message[1:-1]
        # return webinterface.render_error(request,
        #                                  title=missing["title"],
        #                                  messages=message,
        #                                  response_code=404,
        #                                  error_code=missing["error_code"],
        #                                  )
    except YomboNoAccess as e:
        return return_no_access(webinterface, request, e)
    except Exception as e:  # catch anything here...so can display details.
        logger.error("---------------==(Traceback)==--------------------------")
        logger.error("Exception: {e}", e=e)
        logger.error("Function: {function_to_call}", function_to_call=function_to_call)
        logger.error("Request: {request}", request=request)
        logger.error("{trace}", trace=traceback.format_exc())
        logger.error("--------------------------------------------------------")

        log_level = webinterface._Configs.get("logging.library.webinterface", "info", False)
        if log_level != "debug":
            return webinterface.render_error(
                request,
                title="Server error",
                messages=f"The server encountered an error while processing this request: '{type(e).__name__}': {e}",
                response_code=500,
                error_code="server-error",
                )
        else:
            accepts = request.getHeader("accept")
            if isinstance(accepts, str):
                accepts = accepts.lower()
            else:
                content_type = ""

            if "json" in accepts or "msgpack" in accepts or request.api is True:
                return webinterface.render_api_error(request,
                                                     title="Server Error",
                                                     messages="The server encountered an error while processing this request.",
                                                     response_code=500,
                                                     error_code="server_error",
                                                     )
            return webinterface.render_template(request,
                                                webinterface.wi_dir + "/pages/errors/traceback.html",
                                                traceback=traceback.format_exc()
                                                )


def setup_login_redirect(request, login_redirect):
    """
    If login_redirect is not none, return a session. Either create a new session or
    update the existing session.

    :param request:
    :param login_redirect:
    :return:
    """
    session = request.auth
    if login_redirect is None:  # only create a new session if we need too
        login_redirect = request.uri.decode('utf-8')

    try:
        session["auto_login_redirect"] = coerce_value(request.args.get('autologinredirect', [0])[0], 'int')
    except:
        session["auto_login_redirect"] = 0

    session.created_by = "setup_login_redirect"
    # request.received_cookies[webinterface._WebSessions.config.cookie_session_name] = session.auth.auth_id

    # If login redirect end with something silly, ignore it
    if login_redirect.endswith(('.js', '.jpg', '.png', '.css')):
        login_redirect = "/"

    # If we already have a login redirect url and a new one ends with something silly, ignore it
    if "login_redirect" not in session:
        session["login_redirect"] = login_redirect
    else:  # Just display a warning...
        logger.debug("Already have login redirect: {login_redirect}", login_redirect=session['login_redirect'])


def return_need_login(webinterface, request, auth_message=None, **kwargs):
    """
    Returns login page if a normal user, or a json 401 error if an API request.

    :param webinterface:
    :param session:
    :param auth_message:
    :param kwargs:
    :return:
    """
    content_type = request.getHeader("content-type")
    if isinstance(content_type, str):
        content_type = content_type.lower()
    else:
        content_type = ""
    if request.api is True or "json" in content_type:
        if auth_message is None:
            auth_message = "The request requires authorization, none was provided."
        return webinterface.render_api_error(request,
                                             error_code="unauthorized",
                                             title="Unauthorized",
                                             messages=auth_message,
                                             response_code=401)
    return webinterface.redirect(request, "/user/login")


def return_no_access(webinterface, request, error):
    """
    Returns the 403 page to user.

    :param webinterface:
    :param request:
    :param error: YomboNoAccess exception.
    :param kwargs:
    :return:
    """
    return webinterface.render_error(request,
                                     title="Forbidden",
                                     messages="No access to the protected resource.",
                                     response_code=403,
                                     error_code=error.error_code,
                                     )
