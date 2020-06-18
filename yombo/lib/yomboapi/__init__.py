"""

.. note::

  * For library documentation, see: `YomboAPI @ Library Documentation <https://yombo.net/docs/libraries/yomboapi>`_


Manages interactions with api.yombo.net

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.11.0
.. versionadded:: 0.24.0 Standardized to use the requests library.

:copyright: Copyright 2016-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/docs/gateway/html/current/_modules/yombo/lib/yomboapi/__init__.html>`_
"""
# Import python libraries
import traceback
from typing import Any, Optional, Union

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import VERSION
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

from .interactions_mixin import InteractionsMixin
logger = get_logger("library.yomboapi")


class YomboAPI(YomboLibrary, InteractionsMixin):
    """
    Handles interactions with YomboAPI. Can be used by both libraries and modules to interact with with
    API.Yombo.Net.
    """
    @inlineCallbacks
    def _init_(self, **kwargs):
        """ Validate the gateway's credentials (ID & Hash). """
        self.gateway_hash = self._Configs.get("core.gwhash", None, False, instance=True)

        # Please don't use this API key for other uses. To get you're own API key, please email
        # support@yombo.net
        # TODO: Create portal or use the gateway itself to get an API key.
        self.api_app_key = self._Configs.get("yomboapi.api_app_key",
                                             "4Pz5CwKQCsexQaeUvhJnWAFO6TRa9SafnpAQfAApqy9fsdHTLXZ762yCZOct",
                                             False)
        self.base_url = self._Configs.get("yomboapi.baseurl", "https://api.yombo.net/api", False)
        self.gateway_credentials_is_valid = False
        yield self._check_gateway_credentials()

    @inlineCallbacks
    def _check_gateway_credentials(self):
        """
        Talks to the Yombo API and validates the current gateway ID / Gateway Hash (password) and
        the API Auth Key is valid. Sometimes a new API auth key is returned during this check, it
        should be saved for future calls.

        :return:
        """
        logger.debug(f"About to validate gateway credentials")
        gateway_id = self._gateway_id
        gateway_hash = self.gateway_hash.value

        if gateway_id == "local" or gateway_hash is None:
            logger.warn("Unable to validate gateway, gateway_id: {gateway_id}", gateway_id=gateway_id)
            logger.warn("Unable to validate gateway, gateway_hash: {gateway_hash}", gateway_hash=gateway_hash)
            self.gateway_credentials_is_valid = False
            return

        try:
            logger.debug(f"Now doing credential check....")
            response = yield self.request("POST",
                                          f"/v1/gateways/{gateway_id}/check_authentication",
                                          {"hash": gateway_hash},
                                          authorization_header="none",
                                          )
        except YomboWarning as e:
            logger.warn("Unable to validate gateway credentials: {message}", message=e.message)
            if e.error_code in (400, 404):
                self._Configs.set("core.gwid", "local")

            self.gateway_credentials_is_valid = False
            return

        except Exception as e:
            logger.info("check_gateway_credentials API Error: {error}", error=e)
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.format_exc())
            logger.error("--------------------------------------------------------")
            logger.warn("An exception of type {etype} occurred in yombo.lib.yomboapi:import_component. Message: {msg}",
                        etype=type(e), msg=e)
            logger.error("--------------------------------------------------------")
            self.gateway_credentials_is_valid = False
        else:
            data = response.content["data"]
            self.gateway_credentials_is_valid = data["attributes"]["hash_valid"]
            # print(f"api_auth_valid 222: gateway credentals: {self.gateway_credentials_is_valid}")

    @inlineCallbacks
    def request(self, method: str, url: str, body: Optional[Any] = None, query_params: Optional[list] = None,
                headers: Optional[dict] = None, authorization_header=None):
        """
        Make a request to the the Yombo API.

        :param method: GET, POST, PATCH, DELETE, etc.
        :param url: The part after /api. Typically starts with '/v1/'.
        :param body: Body of the request.
        :param query_params: A list of strings to create a query string with. ["key=value"]
        :param headers: A dictionary to add to the HTTP headers request.
        :param authorization_header:
        :return: WebResponse from the Requests library.
        """
        if headers is None:
            headers = {}

        if query_params is not None:
            url += f"?{'&'.join(query_params)}"

        logger.debug("yomboapi request: {url}", url=url)
        request = ApiRequest(self, method, url, body, headers, authorization_header)
        logger.debug("headers: {headers}", headers=request.headers)
        logger.debug("yombo api request body: {body}", body=body)
        response = yield request.request()
        logger.debug("yombo api request response: {response}", response=response)

        self._check_results(response, method, url, body)
        return response

    def _check_results(self, response, method, url, body):
        """ Checks the results for errors and displays them if possible. """
        if response.content_type == "string":
            logger.warn("-----==( Error: API received an invalid response, got a string back )==----")
            logger.warn("Request: {request}", request=response.request.__dict__)
            logger.warn("URL: {method} {uri}", method=response.request.method, uri=response.request.uri)
            logger.warn("Header: {request_headers}", request_headers=response.request.headers)
            logger.warn("Request Data: {body}", body=body)
            logger.warn("Response Headers: {headers}", headers=response.headers)
            logger.warn("Content: {content}", content=response.content)
            logger.warn("--------------------------------------------------------")
        elif response.response_code >= 300:
            logger.warn("-----==( Error: API received an invalid response )==----")
            logger.warn("Request: {request}", request=response.request.__dict__)
            logger.warn("Code: {code}", code=response.response_code)
            logger.warn("URL: {method} {uri}", method=response.request.method, uri=response.request.uri)
            logger.warn("Header: {request_headers}", request_headers=response.request.headers)
            logger.warn("Request Data: {body}", body=body)
            logger.warn("Response Headers: {headers}", headers=response.headers)
            logger.warn("Content: {content}", content=response.content)
            logger.warn("--------------------------------------------------------")
            message = ""
            logger.warn("Error with API request: {method} {url}", method=method, url=url)
            if "errors" in response.content:
                errors = response.content["errors"]
                for error in errors:
                    if len(message) == 0:
                        message += ", "
                    message += f"{message}  {error['title']} - {error['detail']}"
                    raise YomboWarning(response.content["errors"], response.response_code, "_check_results1",
                                       "yomboapi", meta=response)
            else:
                message = f"{response.response_code} - {response.response_phrase}"
            raise YomboWarning(message, response.response_code, "_check_results2", "yomboapi", meta=response)


class ApiRequest:
    """
    Used to create requests from the API.
    """
    def __init__(self, parent, method="GET", url="", body=None, headers={}, authorization_header=None):
        self._Parent = parent
        self.api_app_key = self._Parent.api_app_key
        self.base_url = self._Parent.base_url
        self.user_agent = f"yombo-gateway-{VERSION}"

        self.method = method
        if url.startswith("/"):
            self.url = self.base_url + url
        else:
            self.url = url
        self.body = body
        self.timeout = 30
        self.extra_headers = headers

        self._my_headers = {
            "Accept": "application/json",
            "X-Api-Key": self.api_app_key,
            "Content-Type": "application/json",
        }

        self._authorization_header = self.check_authorization_header(authorization_header)
        self.requested_headers = None

    @property
    def headers(self):
        """ Merge my headers with requested headers"""
        if self._authorization_header is not None:
            return {**self.extra_headers, **self._my_headers, **self._authorization_header}
        else:
            return {**self.extra_headers, **self._my_headers}

    def check_authorization_header(self, incoming):
        if incoming is None or incoming == "":
            if self._Parent.gateway_credentials_is_valid is False:
                return None
            return {"Authorization": f"YomboGateway {self._Parent._gateway_id} {self._Parent.gateway_hash}"}
        else:
            return {"Authorization": incoming}

    @inlineCallbacks
    def request(self):
        self.requested_headers = self.headers
        response = yield self._Parent._Requests.request(self.method, self.url, headers=self.requested_headers,
                                                        json=self.body, timeout=self.timeout)
        return response
