"""
Various error handlers that extend the web_interface library class.
"""

ERROR_RESPONSES = {
    400: {"title": "Bad Request",
          "message": "The request could not be understood by the server due to malformed syntax."},
    401: {"title": "Unauthorized",
          "message": "The request requires user authentication."},
    403: {"title": "BadRequest",
          "message": "The server understood the request, but is refusing to fulfill it. "
                     "Authorization will not help, repeating the request will accomplish nothing."},
    404: {"title": "Not Found",
          "message": "The server has not found anything matching the requested URI."},
    429: {"title": "Too Many Requests",
          "message": "The browser (or client) has sent too many requests to fast. Slow down on the coffee."},
}


class ErrorHandler(object):
    """
    Handles error pages.
    """
    def error_page(webinterface, request, session, response_code=400, title=None, messages=None, api=None):
        """
        Displays an error page to the user. This also sets the response code to response_code.

        :param response_code:
        :param request:
        :param title:
        :param message:
        :param api:
        :return:
        """
        request.setResponseCode(response_code)
        if response_code not in ERROR_RESPONSES:
            response_code = 400
        if title is None:
            title = ERROR_RESPONSES[400]['title']
        if messages is None:
            messages = [ERROR_RESPONSES[400]['message'], ]
        elif isinstance(messages, str):
            messages = [messages, ]

        page = webinterface.get_template(request, webinterface.wi_dir + "/pages/errors/error.html")
        return page.render(alerts=session.get_alerts(),
                           response_code=response_code,
                           title=title,
                           messages=messages)
