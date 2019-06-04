from functools import wraps
from ratelimit import RateLimitException
import traceback
from urllib.parse import urlparse

from twisted.internet.defer import inlineCallbacks

from yombo.core.exceptions import YomboWarning, YomboNoAccess, YomboInvalidValidation
from yombo.core.log import get_logger
from yombo.lib.webinterface.routes.api_v1 import return_error, args_to_dict
from yombo.utils import bytes_to_unicode
from yombo.utils.datatypes import coerce_value

logger = get_logger("library.webinterface.auth")


def update_request(webinterface, request):
    """
    Modifies the request to add "received_cookies in unicode. Also, adds a "args"
    attribute that contains the incoming arguments, but in unicode. Also adds "_" to the
    templates, but it for the current user's language.

    Finally, it adds cache-control and expires items to ensure the content isnt" cached.

    :param request: 
    :return: 
    """
    request.auth = None
    request.received_cookies = bytes_to_unicode(request.received_cookies)
    request.args = bytes_to_unicode(request.args)
    request.setHeader("server", "Apache/2.4.38 (Unix)")
    request.setHeader("X-Powered-By", "YGW")
    request.setHeader("Cache-Control", "no-cache, no-store, must-revalidate")  # don't cache!
    origin_final = "*"
    if request.requestHeaders.hasHeader("origin"):
        origin = request.requestHeaders.getRawHeaders("origin")[0]
        if origin is not None:
            origin = urlparse(origin)
            if origin.scheme in ("http", "https") and len(origin.hostname) < 150 \
                    and origin.port > 60 and origin.port < 65535:
                origin_final = f"{origin.scheme}://{origin.hostname}:{origin.port}"  # For the API

    request.setHeader("Access-Control-Allow-Origin", origin_final)  # For the API, TODO: Make this more restrictive.
    request.setHeader("Access-Control-Allow-Credentials", "true")  # For the API, TODO: Make this more restrictive.

    request.setHeader("Expires", "-1")  # don't cache!
    request.setHeader("X-Frame-Options", "SAMEORIGIN")  # Prevent nesting frames
    request.setHeader("X-Content-Type-Options", "nosniff");  # We"ll do our best to be accurate!
    request.webinterface = webinterface


def run_first(create_session=None, *args, **kwargs):
    """
    Decorator that attempts to get the user's session and appends the webinterface reference
    and session reference to the function call.

    :param create_session: If true, will create a new session. Used during login.
    :param args:
    :param kwargs:
    :return:
    """
    def deco(f):
        @wraps(f)
        @inlineCallbacks
        def wrapped_f(webinterface, request, *a, **kw):
            # print(f"run_first: f: {f}")

            if "api" in kwargs and kwargs["api"] is True:
                if webinterface.web_interface_fully_started is False:
                    # print("auth get session: api request")
                    return webinterface.render_api_error(request, None,
                                                         code="booting-2",
                                                         title="Still loading",
                                                         detail="Gateway is not ready to process API requests.",
                                                         response_code=503)

            session = None
            update_request(webinterface, request)
            host = request.getHeader("host")
            hostname = request.getRequestHostname().decode('utf-8')

            if host is None:
                logger.info("Discarding request, appears to be malformed host header")
                return return_need_login(webinterface, request, None,
                                         api_message="Malformed request headers.",
                                         **kwargs)
            host_info = host.split(":")
            request.requestHeaders.setRawHeaders("host_name", [hostname])

            if len(host_info) > 1:
                request.requestHeaders.setRawHeaders("host_port", [host_info[1]])
            # else:
            #     request.requestHeaders.setRawHeaders("host_port", [None])

            try:
                session = webinterface._AuthKeys.get_session_from_request(request)
                session.touch()
            except YomboWarning as e:
                try:
                    session = yield webinterface._WebSessions.get_session_from_request(request)
                    session.touch()
                except YomboWarning as e:
                    logger.warn("Error in run_first: {e}", e=e)
                    pass

            if session is not None:
                if session.is_valid():
                    request.auth = session

            try:
                if create_session is True and request.auth is None:
                    # print(f"run_first: before session created: {session}")
                    session = webinterface._WebSessions.create_from_web_request(request)
                    # print(f"run_first: created new session: {session.asdict()}")
                    request.auth = session
            except RateLimitException as e:
                logger.warn("Too many sessions being created, stopping this one!")
                return _("ui::messages::rate_limit_exceeded", "Too many attempts, try again later.")

            results = yield auth_run_wrapped_function(f, webinterface, request, session, *a, **kw)
            return results
        return wrapped_f
    return deco


def require_auth(roles=None, login_redirect=None, access_platform=None, access_item=None, access_action=None,
                 *args, **kwargs):
    """
    Decorator that gets the user's session. If user isn't logged in, will redirect to the user login page.

    :param roles:
    :param login_redirect:
    :param access_platform:
    :param access_item:
    :param access_action:
    :param args:
    :param kwargs:
    :return:
    """
    def deco(f):
        @wraps(f)
        @inlineCallbacks
        def wrapped_f(webinterface, request, *a, **kw):
            update_request(webinterface, request)

            host = request.getHeader("host")
            if host is None:
                logger.info("Discarding request, appears to be malformed host header")
                return return_need_login(webinterface, request, None,
                                         api_message="Malformed request headers.",
                                         **kwargs)
            host_info = host.split(":")
            request.requestHeaders.setRawHeaders("host_name", [host_info[0]])

            if len(host_info) > 1:
                request.requestHeaders.setRawHeaders("host_port", [host_info[1]])
            # else:
            #     request.requestHeaders.setRawHeaders("host_port", [None])

            if hasattr(request, "breadcrumb") is False:
                request.breadcrumb = []
                webinterface.misc_wi_data["breadcrumb"] = request.breadcrumb

            # Try to find a session id from the client.
            if "api" in kwargs and kwargs["api"] is True:
                if webinterface.web_interface_fully_started is False:
                    return webinterface.render_api_error(request, None,
                                                         code="booting-1",
                                                         title="Still loading",
                                                         detail="Gateway is not ready to process API requests.",
                                                         response_code=503)

                try:
                    session = webinterface._AuthKeys.get_session_from_request(request)
                    session.touch()
                except YomboWarning as e:
                    logger.debug("API key not found, trying web session (cookie): {e}", e=e)
                    try:
                        session = yield webinterface._WebSessions.get_session_from_request(request)
                    except YomboWarning as e:
                        logger.info("API request doesn't have a valid auth key or session. Bye bye: {e}", e=e)
                        return return_need_login(webinterface, request, None,
                                                 api_message="API request doesn't have a valid auth key or session.",
                                                 **kwargs)
                    # results = webinterface.check_idempotence(request, session)
                    # if isinstance(results, bool) is False:
                    #     return results
            else:
                try:
                    session = yield webinterface._WebSessions.get_session_from_request(request)
                except YomboWarning as e:
                    session = webinterface._WebSessions.create_from_web_request(request)
                    # print(f"require_auth: created new session: {session.asdict()}")
                    setup_login_redirect(webinterface, request, session, login_redirect)
                    logger.info("Discarding request, api requests not accepted: {e}", e=e)
                    logger.info("Request: {request}", request=request)
                    return return_need_login(webinterface, request, None,
                                             api_message=f"Discarding request, api requests not accepted: {e}",
                                             **kwargs)

            # Now validate if the session is any good.
            if session.enabled is False or session.is_valid() is False or session.has_user is False:
                setup_login_redirect(webinterface, request, session, login_redirect)
                return return_need_login(webinterface, request, session,
                                         api_message="API Key is not valid.",
                                         **kwargs)

            session.touch()
            request.auth = session

            if access_platform is not None and access_item is not None and access_action is not None:
                if session.has_access(access_platform, access_item, access_action, raise_error=False) is False:
                    return return_no_access(webinterface, request, session, "No access", **kwargs)
                    pass

            results = yield auth_run_wrapped_function(f, webinterface, request, session, *a, **kw)
            return results
        return wrapped_f
    return deco


@inlineCallbacks
def auth_run_wrapped_function(f, webinterface, request, session, *a, **kw):
    """
    Wraps the callback in a try/except to list the exception details.

    :param f:
    :param webinterface:
    :param request:
    :param session:
    :param a:
    :param kw:
    :return:
    """
    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    try:
        results = yield call(f, webinterface, request, session, *a, **kw)
        return results
    except YomboInvalidValidation as e:
        return return_not_valid_input(webinterface, request, session, **kw)
    except YomboNoAccess as e:
        return return_no_access(webinterface, request, session, "No access", **kw)
    except Exception as e:  # catch anything here...so can display details.
        logger.error("---------------==(Traceback)==--------------------------")
        logger.error("Exception: {e}", e=e)
        logger.error("Function: {f}", f=f)
        logger.error("Request: {request}", request=request)
        logger.error("{trace}", trace=traceback.format_exc())
        logger.error("--------------------------------------------------------")
        content_type = request.getHeader("content-type")
        if isinstance(content_type, str):
            content_type = content_type.lower()
        else:
            content_type = ""
        if "json" in content_type:
            return webinterface.render_api_error(request, None,
                                                 code="server_error",
                                                 title="Server Error",
                                                 detail="The server encountered an error while processing this request.",
                                                 response_code=500)
        return webinterface.render(request, session,
                                   webinterface.wi_dir + "/pages/errors/traceback.html",
                                   traceback=traceback.format_exc()
                                   )


def setup_login_redirect(webinterface, request, session, login_redirect):
    """
    If login_redirect is not none, return a session. Either create a new session or
    update the existing session.

    :param webinterface:
    :param request:
    :param login_redirect:
    :return:
    """
    if login_redirect is None:  # only create a new session if we need too
        login_redirect = request.uri.decode('utf-8')

    if session is None:
        try:
            session = webinterface._WebSessions.create_from_web_request(request)
            # print(f"setup_login_redirect: created new session: {session.asdict()}")
        except YomboWarning as e:
            logger.warn("Discarding request, appears to be malformed request. Unable to create session.")
            return return_need_login(webinterface, request, None,
                                     api_message="Malformed request headers.",
                                     )
        except RateLimitException as e:
            logger.warn("Too many sessions being created!")
            return _("ui::messages::rate_limit_exceeded", "Too many attempts, try again later.")

    try:
        auto_login_redirect = coerce_value(request.args.get('autologinredirect', [0])[0], 'int')
    except:
        auto_login_redirect = 0

    session.created_by = "login_redirect"
    request.received_cookies[webinterface._WebSessions.config.cookie_session_name] = session.auth_id

    # If login redirect end with something silly, ignore it
    if login_redirect.endswith(('.js', '.jpg', '.png', '.css')):
        login_redirect = "/"

    # If we already have a login redirect url and a new one ends with something silly, ignore it
    if "login_redirect" not in session:
        session["login_redirect"] = login_redirect
    else:  # Just display a warning...
        logger.debug("Already have login redirect: {login_redirect}", login_redirect=session['login_redirect'])

    session["auto_login_redirect"] = auto_login_redirect
    return session


def return_need_login(webinterface, request, session, api_message=None, **kwargs):
    """
    Returns login page if a normal user, or a json 401 error if an API request.

    :param webinterface:
    :param request:
    :param session:
    :param api_message:
    :param kwargs:
    :return:
    """
    content_type = request.getHeader("content-type")
    if isinstance(content_type, str):
        content_type = content_type.lower()
    else:
        content_type = ""
    if ("api" in kwargs and kwargs["api"] is True) or "json" in content_type:
        if api_message is None:
            api_message = "The request requires authorization, none was provided."
        return webinterface.render_api_error(request, None,
                                             code="unauthorized",
                                             title="Unauthorized",
                                             detail=api_message,
                                             response_code=401)
    return webinterface.redirect(request, "/user/login")


def return_not_valid_input(webinterface, request, session, **kwargs):
    """
    The system caught a YomboInvalidValidation exception and redirected here. Typically when a user
    submits bogus arguments.

    Returns a 400 error page to users and a json 400 message to API request.

    :param webinterface:
    :param request:
    :param kwargs:
    :return:
    """
    content_type = request.getHeader("content-type")
    if isinstance(content_type, str):
        content_type = content_type.lower()
    else:
        content_type = ""
    if ("api" in kwargs and kwargs["api"] is True) or "json" in content_type:
        return webinterface.render_api_error(request, None,
                                             code="invalid_request",
                                             title="Invalid request",
                                             detail="The request was invalid.",
                                             response_code=400)
    return webinterface.render(request, session,
                               webinterface.wi_dir + "/pages/errors/400.html",
                               title="Invalid request",
                               message="The request being made is invalid.",
                               )


def return_no_access(webinterface, request, session, error, **kwargs):
    """
    Returns the 403 page to user.

    :param webinterface:
    :param request:
    :param error:
    :param kwargs:
    :return:
    """
    content_type = request.getHeader("content-type")
    if isinstance(content_type, str):
        content_type = content_type.lower()
    else:
        content_type = ""
    if ("api" in kwargs and kwargs["api"] is True) or "json" in content_type:
        return webinterface.render_api_error(request, None,
                                             code="forbidden",
                                             title="Forbidden",
                                             detail="No access to the protected resource.",
                                             response_code=403)
    return webinterface.render(request, session, webinterface.wi_dir + "/pages/errors/403.html", error=error)
