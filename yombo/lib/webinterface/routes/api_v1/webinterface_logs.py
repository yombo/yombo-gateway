# Import python libraries
import re

from twisted.internet.defer import inlineCallbacks

from yombo.constants.permissions import ACTIONS_SYSTEM_OPTION
from yombo.lib.webinterface.auth import get_session
from yombo.lib.webinterface.routes.api_v1.__init__ import return_json


def route_api_v1_web_logs(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route("/web_logs", methods=["GET"])
        @get_session(auth_required=True, api=True)
        @inlineCallbacks
        def apiv1_web_logs_get(webinterface, request, session):
            session.is_allowed(ACTIONS_SYSTEM_OPTION, "weblogs")
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

            data, total_count, filtered_count = yield webinterface._LocalDB.search_web_logs_for_datatables(
                order_column_name, order_direction, start, length, search_string)

            response = {
                "draw": draw,
                "recordsTotal": total_count,
                "recordsFiltered": filtered_count,
                "data": data,
            }

            return return_json(request, response)
