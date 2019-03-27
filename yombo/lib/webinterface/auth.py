from functools import wraps
from ratelimit import RateLimitException
from time import time
import traceback

from twisted.internet.defer import inlineCallbacks

from yombo.core.exceptions import YomboWarning, YomboNoAccess, YomboInvalidValidation
from yombo.core.log import get_logger
from yombo.lib.webinterface.routes.api_v1.__init__ import return_error, args_to_dict
from yombo.utils import bytes_to_unicode, sha256_compact

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
    request.setHeader("Cache-Control", "no-cache, no-store, must-revalidate")  # don't cache!
    request.setHeader("Expires", "-1")  # don't cache!
    request.setHeader("X-Frame-Options", "SAMEORIGIN")  # Prevent nesting frames
    request.setHeader("X-Content-Type-Options", "nosniff");  # We"ll do our best to be accurate!
    request.webinterface = webinterface


def check_idempotence(webinterface, request, session):
    """
    Check if idempotence is in the request and if that key has already been processed for the given user.
    If the key has already been used, will return a 409 code, otherwise, lets the request continue.

    :param webinterface:
    :param request:
    :param session:
    :return:
    """
    idempotence = request.getHeader("x-idempotence")
    if idempotence is None:
        arguments = args_to_dict(request.args)
        idempotence = arguments.get("_idempotence", None)
    request.idempotence = idempotence
    if idempotence is not None:
        idempotence = sha256_compact(f"{session.auth_id}:{idempotence}")
        if idempotence in webinterface.idempotence:
            return return_error(request, "idempotence error", 409,
                                "This idempotence key has already be processed.")
        webinterface.idempotence[idempotence] = int(time())
        return True
    return False


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
            print("run_first....")
            session = None
            update_request(webinterface, request)
            host = request.getHeader("host")
            if host is None:
                logger.info("Discarding request, appears to be malformed host header")
                return return_need_login(webinterface, request, None, **kwargs)
            host_info = host.split(":")
            request.requestHeaders.setRawHeaders("host_name", [host_info[0]])

            if len(host_info) > 1:
                request.requestHeaders.setRawHeaders("host_port", [host_info[1]])
            else:
                request.requestHeaders.setRawHeaders("host_port", [None])

            # if hasattr(request, "breadcrumb") is False:
            #     request.breadcrumb = []
            #     webinterface.misc_wi_data["breadcrumb"] = request.breadcrumb

            try:
                session = webinterface._AuthKeys.get_session_from_request(request)
                session.touch()
            except YomboWarning as e:
                try:
                    session = yield webinterface._WebSessions.get_session_from_request(request)
                    session.touch()
                except YomboWarning as e:
                    pass

            if session is not None:
                print("check is valid.. 1")
                if session.is_valid():
                    request.auth = session

            try:
                if create_session is True and request.auth is None:
                    session = webinterface._WebSessions.create_from_web_request(request)
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
    def call(f, *args, **kwargs):
        return f(*args, **kwargs)

    def deco(f):
        @wraps(f)
        @inlineCallbacks
        def wrapped_f(webinterface, request, *a, **kw):
            update_request(webinterface, request)

            host = request.getHeader("host")
            if host is None:
                logger.info("Discarding request, appears to be malformed host header")
                return return_need_login(webinterface, request, None, **kwargs)
            host_info = host.split(":")
            request.requestHeaders.setRawHeaders("host_name", [host_info[0]])

            if len(host_info) > 1:
                request.requestHeaders.setRawHeaders("host_port", [host_info[1]])
            else:
                request.requestHeaders.setRawHeaders("host_port", [None])

            if hasattr(request, "breadcrumb") is False:
                request.breadcrumb = []
                webinterface.misc_wi_data["breadcrumb"] = request.breadcrumb

            # Try to find a session id from the client.
            if "api" in kwargs and kwargs["api"] is True:
                print("auth get session: api request")
                try:
                    session = webinterface._AuthKeys.get_session_from_request(request)
                    session.touch()
                except YomboWarning as e:
                    logger.debug("API key not found, trying web session (cookie): {e}", e=e)
                    try:
                        session = yield webinterface._WebSessions.get_session_from_request(request)
                    except YomboWarning as e:
                        logger.info("API request doesn't have a valid auth key or session. Bye bye: {e}", e=e)
                        return return_need_login(webinterface, request, None, **kwargs)
                    results = check_idempotence(webinterface, request, session)
                    if isinstance(results, bool) is False:
                        return results
            else:
                print("auth get session: web request")
                try:
                    session = yield webinterface._WebSessions.get_session_from_request(request)
                except YomboWarning as e:
                    session = setup_login_redirect(webinterface, request, None, login_redirect)
                    logger.debug("Discarding request, api requests not accepted: {e}", e=e)
                    logger.debug("Request: {request}", request=request)
                    return return_need_login(webinterface, request, None, **kwargs)

            # print(f"auth hh. session: {session}")
            # Now validate if the session is any good.
            # print(f"auth session.enabled: {session.enabled}")
            # print(f"auth session.is_valid: {session.is_valid()}")
            print("check is valid.. 3")

            if session.enabled is False or session.is_valid() is False or session.has_user is False:
                # print("auth: require_auth: session is not enable or is not valid!")
                return return_need_login(webinterface,
                                         request,
                                         session,
                                         api_message="API Key is not valid.",
                                         **kwargs)

            session.touch()
            request.auth = session

            if access_platform is not None and access_item is not None and access_action is not None:
                if session.has_access(access_platform, access_item, access_action, raise_error=False) is False:
                    return return_no_access(webinterface, request, "No access", **kwargs)
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
        return return_not_valid_input(webinterface, request, **kw)
    except YomboNoAccess as e:
        return return_no_access(webinterface, request, "No access", **kw)
    except Exception as e:  # catch anything here...so can display details.
        logger.error("---------------==(Traceback)==--------------------------")
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
            return return_error(request, "Server Error", 500, traceback.format_exc())
        page = webinterface.get_template(request, webinterface.wi_dir + "/pages/misc/traceback.html")
        return page.render(traceback=traceback.format_exc())


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
        return

    if session is None:
        try:
            session = webinterface._WebSessions.create_from_web_request(request)
        except YomboWarning as e:
            logger.warn("Discarding request, appears to be malformed request. Unable to create session.")
            return return_need_login(webinterface, request, None)
        except RateLimitException as e:
            logger.warn("Too sessions being created!")
            return _("ui::messages::rate_limit_exceeded", "Too many attempts, try again later.")

    session.created_by = "login_redirect"
    request.received_cookies[webinterface._WebSessions.config.cookie_session_name] = session.auth_id
    session["login_redirect"] = login_redirect
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
        return return_error(request, "Unauthorized", 401, api_message)
    return webinterface.redirect(request, "/user/login")


def return_not_valid_input(webinterface, request, **kwargs):
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
        return return_error(request, "Forbidden - No access to protected resource", 400)
    page = webinterface.get_template(request, webinterface.wi_dir + "/pages/errors/400.html")
    return page.render(
        alerts=webinterface.get_alerts(),
        title="Invalid request",
        message="The request being made is invalid.",
    )


def return_no_access(webinterface, request, error, **kwargs):
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
        return return_error(request, "Forbidden - No access to protected resource", 403)
    page = webinterface.get_template(request, webinterface.wi_dir + "/pages/errors/403.html")
    return page.render(alerts=webinterface.get_alerts(), error=error)
