"""
Handles rendering content to browsers or API requests. This is apart of the :ref:`WebInterface <webinterface>`
library

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019-2020 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/webinterface/mixins/render.html>`_
"""
# Import python libraries
from glob import glob
import gzip
from io import BytesIO, StringIO
import json
import msgpack
import os
import re
from typing import Any, Dict, List, Optional, Union, Type
import zlib

# Import Yombo libraries
from yombo.classes.jsonapi import JSONApi
from yombo.constants import CONTENT_TYPE_JSON, CONTENT_TYPE_MSGPACK, CONTENT_TYPE_TEXT_PLAIN, CONTENT_TYPE_TEXT_HTML
from yombo.constants.exceptions import ERROR_CODES
from yombo.core.exceptions import YomboWarning, YomboWebinterfaceError
from yombo.core.log import get_logger
from yombo.utils import unicode_to_bytes, bytes_to_unicode

logger = get_logger("library.webinterface.render")
gzipCheckRegex = re.compile(br'(:?^|[\s,])gzip(:?$|[\s,])')


class RenderMixin:
    """
    Handles responses to web clients.
    """
    @staticmethod
    def render_find_accepts(accepts):
        accepts = bytes_to_unicode(accepts)
        for accept in [CONTENT_TYPE_MSGPACK, CONTENT_TYPE_JSON, CONTENT_TYPE_TEXT_HTML, CONTENT_TYPE_TEXT_PLAIN]:
            if accept in accepts:
                return accept
        if "*/*" in accepts:
            return "text/plain"
        return None

    def render_gzip_encode(self, content):
        return

    def render_encode_output(self, request, content):
        """
        Checks the request headers for the encoding string. If it's gzip, it will be compressed.

        :param request:
        :param content:
        :return:
        """
        if content is not None and len(content) > 500:  # don't bother compressing small data
            response_content_encoding_headers = b','.join(request.responseHeaders.getRawHeaders(b'content-encoding', []))
            if bool(gzipCheckRegex.search(response_content_encoding_headers)) is False:
                request_accept_encoding_headers = b','.join(request.requestHeaders.getRawHeaders(b'accept-encoding', []))
                if gzipCheckRegex.search(request_accept_encoding_headers):
                    encoding = request.responseHeaders.getRawHeaders(b'content-encoding')
                    if encoding:
                        encoding = b','.join(encoding + [b'gzip'])
                    else:
                        encoding = b'gzip'
                    request.responseHeaders.setRawHeaders(b'content-encoding', [encoding])
                    content = gzip.compress(unicode_to_bytes(content))

        # print(f"render_encode_output: content type: {type(content)}")
        # print(f"REO: {request.responseHeaders._rawHeaders}")
        if content is None:
            request.responseHeaders.setRawHeaders(b'content-length', [str(0)])
        else:
            request.responseHeaders.setRawHeaders(b'content-length', [str(len(content))])
        # print(f"REO: {request.responseHeaders._rawHeaders}")
        return content

    # def get_idempotence(self,
    #                     request: Type["twisted.web.http.Request"],
    #                     authentication: Type["yombo.mixins.auth_mixin.AuthMixin"]
    #                     ) -> bool:
    #     """
    #     Check if idempotence is in the request and if that key has already been processed for the given user. If it
    #     has, return the same response.
    #
    #     :param self:
    #     :param request: A request instance
    #     :param authentication: An authentication instance: authkey, session, user
    #     :return:
    #     """
    #     request.setHeader("Content-Type", CONTENT_TYPE_JSON)
    #     idempotence = request.getHeader("x-idempotence")
    #     if idempotence is None:
    #         arguments = request_args(request.args)
    #         idempotence = arguments.get("_idempotence", None)
    #     if idempotence is not None:
    #         request.idempotence = idempotence
    #         idempotence = self._Hash.sha256_compact(f"{authentication.auth_id}:{idempotence}")
    #         if idempotence in self.idempotence:
    #             results = self._Tools.data_unpickle(self.idempotence[idempotence], "msgpack_zip")
    #             print(f"get_idempotence results {results}")
    #             return False
    #             request.setHeader("Idempotence", "true")
    #             request.setResponseCode(results["response_code"])
    #             return results["data"]
    #     return False

    def render_template(self,
                        request: Type["twisted.web.http.Request"],
                        template_path: str,
                        response_code: Optional[int] = None,
                        preload_nuxt: Optional[bool] = None,
                        **kwargs) -> str:
        """
        Render a page to the web browser, using a Jinja2 template. This adds common variables to the jinja2 engine.

        :param request: A request instance
        :param template_path: Path to the template file. If not fully qualified, working_dir will be prepended.
        :param response_code: Set the response code.
        :param preload_nuxt: If True, adds nuxt preload content.
        :param kwargs:
        :return:
        """
        if template_path.startswith("/") is False:
            template_path = f"{self.wi_dir}/{template_path}"
        if response_code is None:
            response_code = 200
        request.setResponseCode(response_code)
        template = self.webapp.templates.get_template(template_path)
        kwargs["authentication"] = request.auth
        kwargs["_"] = self._Localize.get_translator_from_request(request)
        if preload_nuxt is True:
            files = glob(f"{self._working_dir}/frontend/_nuxt/*.js")
            nuxtpreload = sorted((os.path.getsize(s), s.split('/')[-1]) for s in files) if files else ''
            kwargs["nuxtpreload"] = nuxtpreload[-2:]
        return template.render(**kwargs)

    def render_api(self,
                   request: Type["twisted.web.http.Request"],
                   data: Union[JSONApi, dict],
                   data_type: Optional[str],
                   response_code: Optional[int] = None) -> str:
        """
        Renders content to an API based client.

        :param request: A request instance
        :param data: Prefers a JSONApi object, but accepts a dict.
        :param data_type: The string for the JSON API type.
        :param response_code: HTTP response code to set. Default: 200
        :return:
        """
        if isinstance(data, dict):
            data = JSONApi(data)

        output = data.to_dict()
        if data_type is None:
            data_type = data.data_type(output)

        return self.render_api_raw(request, data=output, data_type=data_type, response_code=response_code)

    def render_api_raw(self,
                       request: Type["twisted.web.http.Request"],
                       data: dict,
                       data_type: Optional[str] = None,
                       response_code: Optional[int] = None) -> str:
        """
        Renders content to an API based client, however this takes the data input as a dictionary and will
        not be processed. THis shoulud be in JSON API format, but not always.

        :param request:
        :param data:
        :param data_type:
        :param response_code:
        :return:
        """
        #  These 3 functions are used to massage the data for the template when displaying the data
        #  in a browser.
        def js_list(encoder, local_data):
            pairs = []
            for v in local_data:
                pairs.append(js_val(encoder, v))
            return "[" + ", ".join(pairs) + "]"

        def js_dict(encoder, local_data):
            pairs = []
            for k, v in local_data.items():
                pairs.append(k + ": " + js_val(encoder, v))
            return "{" + ", ".join(pairs) + "}"

        def js_val(encoder, local_data):
            if isinstance(local_data, dict):
                val = js_dict(encoder, local_data)
            elif isinstance(local_data, list):
                val = js_list(encoder, local_data)
            else:
                val = encoder.encode(local_data)
            return val

        if response_code is None or isinstance(response_code, int) is False:
            response_code = 200
        request.setResponseCode(response_code)

        accepts = request.getHeader("accept")
        if isinstance(accepts, str):
            accepts = accepts.lower()
        else:
            accepts = ""

        accepted_type = self.render_find_accepts(accepts)
        if accepted_type is None:
            raise YomboWebinterfaceError(response_code=415)

        # idempotence = request.getHeader("x-idempotence")
        # if idempotence is None:
        #     arguments = request_args(request.args)
        #     idempotence = arguments.get("_idempotence", None)
        # if idempotence is not None:
        #     if data_type is None:
        #         data_type = ""
        #     idempotence = self._Hash.sha256_compact(f"{request.auth.auth_id}:{data_type}:{idempotence}")
        #
        #     self.idempotence[idempotence] = self._Tools.data_pickle({
        #             "data": data,
        #             "response_code": response_code,
        #             # "response_headers": request.re
        #         },
        #         "msgpack_zip"
        #     )

        request.setHeader("Content-Type", accepted_type)
        if accepted_type == CONTENT_TYPE_JSON:
            # print(f"dumping json data: {data}")
            return json.dumps(data)
        elif accepted_type == CONTENT_TYPE_MSGPACK:
            return msgpack.packb(data)
        elif accepted_type == CONTENT_TYPE_TEXT_HTML or CONTENT_TYPE_TEXT_PLAIN:
            encoder = json.JSONEncoder(ensure_ascii=False)
            if data_type is None:
                data_type = "Unknown"
            template_path = "pages/misc/json_api.html"

            return self.render_template(request,
                                        template_path,
                                        response_code=response_code,
                                        data_type=data_type,
                                        data=js_val(encoder, data),
                                        )
        else:
            return "Browser friendly version coming soon:\n" + json.dumps(data)

    def render_error(self, request, title: Optional[str] = None, messages: Optional[Union[str, list]] = None,
                     response_code: Optional[int] = None, error_code: Optional[Union[str, int]] = None):
        """
        Displays an error page to the user. This also sets the response code to response_code.

        :param request:
        :param title:
        :param messages:
        :param response_code:
        :param error_code:
        :param api:
        :return:
        """
        if response_code is None or isinstance(response_code, int) is False or response_code not in ERROR_CODES:
            response_code = 400

        if response_code not in ERROR_CODES:
            response_code = 400

        if messages == None:
            message = [{}]
        if isinstance(messages, str):
            messages = [{"detail": messages}]

        for message in messages:
            if "response_code" not in message:
                message["status"] = response_code

            if message["status"] not in ERROR_CODES:
                message["status"] = 400

            missing_items = ERROR_CODES[message["status"]]

            if "title" not in message:
                message["title"] = missing_items["title"]
            if "detail" not in message:
                message["detail"] = missing_items["details"]
            if "code" not in message:
                if error_code is not None:
                    message["code"] = error_code
                else:
                    message["code"] = missing_items["error_code"]

        accepts = request.getHeader("accept")
        if isinstance(accepts, str):
            accepts = accepts.lower()
        else:
            accepts = "text/html"

        accepted_type = self.render_find_accepts(accepts)
        if accepted_type in (CONTENT_TYPE_JSON, CONTENT_TYPE_MSGPACK):
            return self.render_api_errors(request,
                                          messages=messages,
                                          response_code=response_code)

        if accepted_type in (CONTENT_TYPE_TEXT_PLAIN, CONTENT_TYPE_TEXT_HTML):
            return self.render_template(request,
                                        "pages/errors/error.html",
                                        title=title,
                                        messages=messages,
                                        response_code=response_code,
                                        error_code=error_code)
        raise YomboWebinterfaceError(response_code=415)

    def render_api_error(self,
                         request: Type["twisted.web.http.Request"],
                         error_code: Optional[Union[str, int]] = None,
                         title: Optional[str] = None,
                         messages: Optional[str] = None,
                         meta: Optional[Dict[str, Any]] = None,
                         about_link: Optional[str] = None,
                         response_code: Optional[int] = None):
        """
        Render a single error to an API client.

        :param request: A request instance
        :param error_code: A string or in to pass as the error code to lookup.
        :param title: Title for the error.
        :param messages: Details about the error.
        :param meta: Any additional information about the error.
        :param about_link: A link to get more details about the error.
        :param response_code: HTTP response code to set.
        :return:
        """
        error = {}
        if error_code is not None:
            error["code"] = str(error_code)
        if title is not None:
            error["title"] = title
        if messages is not None:
            error["detail"] = messages
        elif isinstance(about_link, str):
            error["links"] = {"about": about_link}

        return self.render_api_errors(request, [error, ], meta, response_code)

    def render_api_errors(self,
                          request: Type["twisted.web.http.Request"],
                          messages: List[Union[str, Dict[str, Union[str, int, float, None]]]],
                          meta: Optional[Dict[str, Any]] = None,
                          response_code: Optional[int] = None) -> str:
        """
        Render multiple API errors.

        :param request: A request instance
        :param messages: A dictionary of errors to return to client.
        :param meta: Any additional information about the error.
        :param response_code: HTTP response code to set.
        :return:
        """
        response = {
            "jsonapi": {"version": "1.0"},
            "errors": messages,
        }

        if meta is not None:
            response["meta"] = meta

        return self.render_api_raw(request, data=response, response_code=response_code)

    def still_building_frontend(self, request):
        """ Called from various places. Returns a simple page that says frontend still building. """
        return self.render_template(request,
                                    "pages/misc/still_building_frontend.html",
                                    )

    def still_loading(self, request, message=None):
        """ Called from various places. Returns a simple page that says frontend still building. """
        return self.render_template(request,
                                    "pages/misc/still_loading.html",
                                    message=message
                                    )
