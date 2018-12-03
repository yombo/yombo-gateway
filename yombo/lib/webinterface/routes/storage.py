from twisted.internet.defer import inlineCallbacks

from yombo.core.exceptions import YomboNoAccess
from yombo.lib.webinterface.auth import require_auth

def route_storage(webapp):
    with webapp.subroute("/storage") as webapp:
        @webapp.route("/")
        @require_auth()
        def page_storage(webinterface, request, session):
            return webinterface.redirect(request, "/storage/index")

        @webapp.route("/index")
        @require_auth()
        def page_lib_storage_index(webinterface, request, session):
            # session.has_access("atom", "*", "view")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/storage/index.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/info", "Info")
            webinterface.add_breadcrumb(request, "/storage/index", "Storage")
            return page.render(alerts=webinterface.get_alerts(),
                               )

        @webapp.route("/<string:file_id>/details")
        @require_auth()
        @inlineCallbacks
        def page_lib_storage_details(webinterface, request, session, file_id):
            # session.has_access("atom", atom_name, "view")
            try:
                file_data = yield webinterface._Storage.get(file_id)
            except Exception as e:
                webinterface.add_alert(f"Storage file id.  {file_id}", "warning")
                redirect = webinterface.redirect(request, "/storage/index")
                return redirect
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/storage/details.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/info", "Info")
            webinterface.add_breadcrumb(request, "/storage/index", "Storage")
            webinterface.add_breadcrumb(request, f"/storage/{file_id}/details", "Details")
            page = page.render(alerts=webinterface.get_alerts(),
                               file_data=file_data,
                               )
            return page

        @webapp.route("/<string:file_id>/delete")
        @require_auth()
        @inlineCallbacks
        def page_lib_storage_delete(webinterface, request, session, file_id):
            # session.has_access("atom", atom_name, "view")
            if file_id.isalnum() is False:
                webinterface.add_alert(f"Storage file id is invalid.", "warning")
                redirect = webinterface.redirect(request, "/storage/index")
                return redirect

            try:
                print("delete: 1")
                yield webinterface._Storage.delete(file_id)
                print("delete: 2")
            except KeyError as e:
                print("delete: 3")
                webinterface.add_alert(f"Storage file id not found: {file_id}", "warning")
                redirect = webinterface.redirect(request, "/storage/index")
                return redirect

            print("delete: 8")
            webinterface.add_alert("Storage file deleted")

            return webinterface.redirect(request, "/storage/index")
