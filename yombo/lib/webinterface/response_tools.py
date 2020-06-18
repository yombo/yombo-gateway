"""
Various tools for web request responses.
"""
from urllib.parse import urlparse


def common_headers(request):
    """
    Adds common headers to the request:
    server - Fake a server response version
    x-powered-by - "YGW"
    access-control-allow-origin - Use the request info to a proper response
    access-control-allow-credentials - "true"
    x-frame-options - "SAMEORIGIN"
    x-control-type-options - "nosniff"

    :param request:
    :return:
    """
    request.setHeader("server", "Apache/2.4.41 (Unix)")
    request.setHeader("X-Powered-By", "YGW")

    origin_final = "*"
    if request.requestHeaders.hasHeader("origin"):
        origin = request.requestHeaders.getRawHeaders("origin")[0]
        if origin is not None:
            origin = urlparse(origin)
            origin_port = origin.port
            if origin_port is None:
                origin_final = f"{origin.scheme}://{origin.hostname}"  # For the API
            else:
                if origin.scheme in ("http", "https") and len(origin.hostname) < 150 and 60 < origin_port < 65535:
                    origin_final = f"{origin.scheme}://{origin.hostname}:{origin_port}"  # For the API

    request.setHeader("Access-Control-Allow-Origin", origin_final)  # For the API, TODO: Make this more restrictive.
    request.setHeader("Access-Control-Allow-Headers", "Content-Type")
    request.setHeader("Access-Control-Allow-Credentials", "true")  # For the API, TODO: Make this more restrictive.
    request.setHeader("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, PUT, OPTIONS")  # Allow common actions.
    request.setHeader("X-Frame-Options", "SAMEORIGIN")  # Prevent nesting frames
    request.setHeader("X-Content-Type-Options", "nosniff")  # We"ll do our best to be accurate!
