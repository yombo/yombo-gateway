# Import python libraries
import re

from twisted.internet.defer import inlineCallbacks

from yombo.constants.permissions import AUTH_PLATFORM_STORAGE
from yombo.lib.webinterface.auth import get_session
from yombo.lib.webinterface.routes.api_v1.__init__ import return_json


def route_api_v1_storage(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route("/storage/index", methods=["GET"])
        @get_session(auth_required=True, api=True)
        @inlineCallbacks
        def apiv1_storage_get(webinterface, request, session):
            session.is_allowed(AUTH_PLATFORM_STORAGE, "view")
            args = request.args

            try:
                draw = int(args["draw"][0])
                start = int(args["start"][0])
                length = int(args["length"][0])
                order_column_number = int(args["order[0][column]"][0])
                search_string = str(args["search[value]"][0])
                col_name = f"columns[{order_column_number}][data]"
                order_column_name = str(args[col_name][0])
            except:
                return return_json(request, {}, 500)

            order_direction = args["order[0][dir]"][0]
            if order_direction.lower() not in ("asc", "desc"):
                return return_json(request, {}, 500)

            if re.match("^[ \w-]+$", search_string) is None:
                search_string = ""

            data, total_count, filtered_count = yield webinterface._LocalDB.search_storage_for_datatables(
                order_column_name, order_direction, start,
                length, search_string)

            response = {
                "draw": draw,
                "recordsTotal": total_count,
                "recordsFiltered": filtered_count,
                "data": data,
            }

            return return_json(request, response)
