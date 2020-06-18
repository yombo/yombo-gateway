ERROR_CODES = {
    400: {"title": "Bad Request",
          "details": "The request could not be understood by the server due to malformed syntax. "
                     "Re-sending the request will not help.",
          "error_code": "bad-request-400",
          "links": {
              "about": "https://yombo.net/GWAPI:Overview"
            }
          },
    401: {"title": "Unauthorized",
          "details": "The request requires user authentication, typically requires an Auth Key",
          "error_code": "unauthorized-401",
          "links": {
              "about": "https://yombo.net/GWAPI:Overview"
            }
          },
    403: {"title": "Forbidden",
          "details": "The server understood the request, but is refusing to fulfill it. Authorization will not help "
                     "and resending the request will not help.",
          "error_code": "forbidden-403",
          "links": {
              "about": "https://yombo.net/GWAPI:Overview"
            }
          },
    404: {"title": "Not Found",
          "details": "The server has not found anything at the requested URI.",
          "error_code": "not-found-404",
          "links": {
              "about": "https://yombo.net/GWAPI:Overview"
            }
          },
    405: {"title": "Method Not Allowed",
          "details": "The requested method cannot be performed against the requested resource.",
          "error_code": "method-not-allowed-405",
          "links": {
              "about": "https://yombo.net/GWAPI:Overview"
            }
          },
    415: {"title": "Unsupported Media Type",
          "details": "The requested output formatting is not supported. Try application/json, text/html, etc.",
          "error_code": "unsupported-media-type-415",
          "links": {
              "about": "https://yombo.net/GWAPI:Overview"
            }
          },
    429: {"title": "Too Many Requests",
          "message": [
              "The browser (or client) has sent too many requests to fast. Slow down on the coffee.",
              "Typically, this means that a GET was requested but allow, or POST was requested by now allowed."
          ],
          "error_code": "too-many-requests-429",
          "links": {
              "about": "https://yombo.net/GWAPI:Overview"
            }
          },
    500: {"title": "Internal Server Error",
          "details": "The requested item could not be returned due to an error.",
          "error_code": "internal-server-error-500",
          "links": {
              "about": "https://yombo.net/GWAPI:Overview"
            }
          }
    }
