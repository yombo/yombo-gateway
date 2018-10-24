# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/crontabs" sub-route of the web interface.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.18.0

:copyright: Copyright 2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/routes/crontabs.py>`_
"""
# from collections import OrderedDict
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.routes.crontabs")


def route_crontabs(webapp):
    with webapp.subroute("/crontab") as webapp:
        def root_breadcrumb(webinterface, request):
            webinterface.add_breadcrumb(request, "/?", "Home")
            webinterface.add_breadcrumb(request, "/crontab/index", "CronTabs")

        @webapp.route('/')
        @require_auth()
        def page_crontabs(webinterface, request, session):
            session.has_access('crontab', '*', 'view', raise_error=True)
            return webinterface.redirect(request, '/crontab/index')

        @webapp.route('/index')
        @require_auth()
        def page_crontabs_index(webinterface, request, session):
            session.has_access('crontab', '*', 'view', raise_error=True)
            item_keys, permissions = webinterface._Users.get_access(session, 'crontab', 'view')
            root_breadcrumb(webinterface, request)
            page = webinterface.get_template(request, webinterface.wi_dir + '/pages/crontab/index.html')
            return page.render(
                alerts=webinterface.get_alerts(),
                )

        @webapp.route('/<string:crontab_id>/details', methods=['GET'])
        @require_auth()
        def page_crontabs_details_get(webinterface, request, session, crontab_id):
            try:
                session.has_access('crontab', crontab_id, 'view', raise_error=True)
                crontab = webinterface._CronTab.get(crontab_id)
            except KeyError as e:
                webinterface.add_alert(e, 'warning')
                return webinterface.redirect(request, '/crontab/index')

            page = webinterface.get_template(
                request,
                webinterface.wi_dir + '/pages/crontab/details.html')
            root_breadcrumb(webinterface, request)
            webinterface.add_breadcrumb(request, "/crontab/%s/details" % crontab.cron_id, crontab.label)
            return page.render(alerts=webinterface.get_alerts(),
                               crontab=crontab,
                               )

        # @webapp.route('/add', methods=['GET'])
        # @require_auth()
        # def page_crontabs_add_get(webinterface, request, session):
        #     session.has_access('crontab', '*', 'add', raise_error=True)
        #     data = {
        #         'label': webinterface.request_get_default(request, 'label', ""),
        #         'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
        #         'description': webinterface.request_get_default(request, 'description', ""),
        #         'status': int(webinterface.request_get_default(request, 'status', 1)),
        #     }
        #     root_breadcrumb(webinterface, request)
        #     webinterface.add_breadcrumb(request, "/crontab/add", "Add")
        #     return page_crontabs_form(webinterface, request, session, 'add', data, "Add CronTab")
        #
        # @webapp.route('/add', methods=['POST'])
        # @require_auth()
        # @inlineCallbacks
        # def page_crontabs_add_post(webinterface, request, session):
        #     session.has_access('crontab', '*', 'add', raise_error=True)
        #     data = {
        #         'label': webinterface.request_get_default(request, 'label', ""),
        #         'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
        #         'description': webinterface.request_get_default(request, 'description', ""),
        #         'status': int(webinterface.request_get_default(request, 'status', 1)),
        #     }
        #
        #     try:
        #         crontab = yield webinterface._CronTab.add(data['label'], data['machine_label'],
        #                                                data['description'], data['status'])
        #     except YomboWarning as e:
        #         webinterface.add_alert("Cannot add crontab. %s" % e.message, 'warning')
        #         return page_crontabs_form(webinterface, request, session, 'add', data, "Add CronTab",)
        #
        #     webinterface.add_alert("New crontab '%s' added." % crontab.label)
        #     return webinterface.redirect(request, "/crontab/%s/details" % crontab.crontab_id)
        #
        # @webapp.route('/<string:crontab_id>/edit', methods=['GET'])
        # @require_auth()
        # def page_crontabs_edit_get(webinterface, request, session, crontab_id):
        #     session.has_access('crontab', crontab_id, 'edit', raise_error=True)
        #     try:
        #         crontab = webinterface._CronTab.get(crontab_id)
        #     except KeyError as e:
        #         webinterface.add_alert(e.message, 'warning')
        #         return webinterface.redirect(request, '/crontab/index')
        #
        #     root_breadcrumb(webinterface, request)
        #     webinterface.add_breadcrumb(request, "/crontab/%s/details" % crontab.crontab_id, crontab.label)
        #     webinterface.add_breadcrumb(request, "/crontab/%s/edit" % crontab.crontab_id, "Edit")
        #     data = {
        #         'label': crontab.label,
        #         'machine_label': crontab.machine_label,
        #         'description':  crontab.description(),
        #         'status': crontab.effective_status(),
        #         'crontab_id': crontab_id,
        #         'allow_intents': crontab.data['config']['allow_intents'],
        #     }
        #     return page_crontabs_form(webinterface,
        #                             request,
        #                             session,
        #                             'edit',
        #                             data,
        #                             "Edit CronTab: %s" % crontab.label)
        #
        # @webapp.route('/<string:crontab_id>/edit', methods=['POST'])
        # @require_auth()
        # def page_crontabs_edit_post(webinterface, request, session, crontab_id):
        #     session.has_access('crontab', crontab_id, 'edit', raise_error=True)
        #     try:
        #         crontab = webinterface._CronTab.get(crontab_id)
        #     except KeyError as e:
        #         webinterface.add_alert(e.message, 'warning')
        #         return webinterface.redirect(request, '/crontab/index')
        #
        #     data = {
        #         'label': webinterface.request_get_default(request, 'label', ""),
        #         'machine_label': webinterface.request_get_default(request, 'machine_label', ""),
        #         'description': webinterface.request_get_default(request, 'description', ""),
        #         'status': int(webinterface.request_get_default(request, 'status', 1)),
        #         'crontab_id': crontab_id,
        #         'allow_intents': int(webinterface.request_get_default(request, 'allow_intents', 1)),
        #     }
        #     print("crontab save: %s" % data)
        #
        #     try:
        #         crontab = webinterface._CronTab.edit(crontab_id,
        #                                           data['label'], data['machine_label'],
        #                                           data['description'], data['status'],
        #                                           data['allow_intents'])
        #     except YomboWarning as e:
        #         webinterface.add_alert("Cannot edit crontab. %s" % e.message, 'warning')
        #         root_breadcrumb(webinterface, request)
        #         webinterface.add_breadcrumb(request, "/crontab/%s/details" % crontab.crontab_id, crontab.label)
        #         webinterface.add_breadcrumb(request, "/crontab/%s/edit", "Edit")
        #
        #         return page_crontabs_form(webinterface, request, session, 'edit', data,
        #                                                 "Edit CronTab: %s" % crontab.label)
        #
        #     webinterface.add_alert("CronTab '%s' edited." % crontab.label)
        #     return webinterface.redirect(request, "/crontab/%s/details" % crontab.crontab_id)
        #
        # def page_crontabs_form(webinterface, request, session, action_type, crontab, header_label):
        #     page = webinterface.get_template(
        #         request,
        #         webinterface.wi_dir + '/pages/crontab/form.html')
        #     return page.render(alerts=webinterface.get_alerts(),
        #                        header_label=header_label,
        #                        crontab=crontab,
        #                        action_type=action_type,
        #                        )
        #
        # @webapp.route('/<string:crontab_id>/delete', methods=['GET'])
        # @require_auth()
        # def page_crontabs_details_post(webinterface, request, session, crontab_id):
        #     session.has_access('crontab', crontab_id, 'delete', raise_error=True)
        #     try:
        #         crontab = webinterface._CronTab.get(crontab_id)
        #     except KeyError as e:
        #         webinterface.add_alert(e.message, 'warning')
        #         return webinterface.redirect(request, '/crontab/index')
        #
        #     page = webinterface.get_template(
        #         request,
        #         webinterface.wi_dir + '/pages/crontab/delete.html'
        #     )
        #     root_breadcrumb(webinterface, request)
        #     webinterface.add_breadcrumb(request, "/crontab/%s/details" % crontab_id, crontab.label)
        #     webinterface.add_breadcrumb(request, "/crontab/%s/delete" % crontab_id, "Delete")
        #     return page.render(alerts=webinterface.get_alerts(),
        #                        crontab=crontab,
        #                        )
        #
        # @webapp.route('/<string:crontab_id>/delete', methods=['POST'])
        # @require_auth()
        # @inlineCallbacks
        # def page_crontabs_delete_post(webinterface, request, session, crontab_id):
        #     session.has_access('crontab', crontab_id, 'delete', raise_error=True)
        #     try:
        #         crontab = webinterface._CronTab.get(crontab_id)
        #     except KeyError as e:
        #         webinterface.add_alert(e.message, 'warning')
        #         return webinterface.redirect(request, '/crontab/index')
        #
        #     try:
        #         confirm = request.args.get('confirm')[0]
        #     except:
        #         webinterface.add_alert('Must enter "delete" in the confirmation box to delete the crontab.', 'warning')
        #         return webinterface.redirect(request, '/crontab/%s/details' % crontab_id)
        #
        #     if confirm != "delete":
        #         webinterface.add_alert('Must enter "delete" in the confirmation box to delete the crontab.', 'warning')
        #         return webinterface.redirect(request,
        #                                      '/crontab/%s/details' % crontab_id)
        #
        #     try:
        #         yield crontab.delete(session=session['yomboapi_session'])
        #     except YomboWarning as e:
        #         webinterface.add_alert("Cannot delete crontab. %s" % e.message, 'warning')
        #         return webinterface.redirect(request, '/crontab/%s/details' % crontab_id)
        #
        #     webinterface.add_alert('CronTab deleted. Will be fully removed from system on next restart.')
        #     return webinterface.redirect(request, '/crontab/index')
        #
        # @webapp.route('/<string:crontab_id>/disable', methods=['GET'])
        # @require_auth()
        # def page_crontabs_disable_get(webinterface, request, session, crontab_id):
        #     session.has_access('crontab', crontab_id, 'disable', raise_error=True)
        #     try:
        #         crontab = webinterface._CronTab.get(crontab_id)
        #     except KeyError as e:
        #         webinterface.add_alert(e.message, 'warning')
        #         return webinterface.redirect(request, '/crontab/index')
        #
        #     page = webinterface.get_template(request, webinterface.wi_dir + '/pages/crontab/disable.html')
        #     root_breadcrumb(webinterface, request)
        #     webinterface.add_breadcrumb(request, "/crontab/%s/details" % crontab.crontab_id, crontab.label)
        #     webinterface.add_breadcrumb(request, "/crontab/%s/disable" % crontab.crontab_id, "Disable")
        #     return page.render(alerts=webinterface.get_alerts(),
        #                        crontab=crontab,
        #                        )
        #
        # @webapp.route('/<string:crontab_id>/disable', methods=['POST'])
        # @require_auth()
        # def page_crontabs_disable_post(webinterface, request, session, crontab_id):
        #     session.has_access('crontab', crontab_id, 'disable', raise_error=True)
        #     try:
        #         crontab = webinterface._CronTab.get(crontab_id)
        #     except KeyError as e:
        #         webinterface.add_alert(e.message, 'warning')
        #         return webinterface.redirect(request, '/crontab/index')
        #
        #     try:
        #         confirm = request.args.get('confirm')[0]
        #     except:
        #         webinterface.add_alert('Must enter "disable" in the confirmation box to disable the crontab.',
        #                                'warning')
        #         return webinterface.redirect(request, '/crontab/%s/details' % crontab_id)
        #
        #     if confirm != "disable":
        #         webinterface.add_alert('Must enter "disable" in the confirmation box to disable the crontab.',
        #                                'warning')
        #         return webinterface.redirect(request, '/crontab/%s/details' % crontab_id)
        #
        #     try:
        #         crontab.disable(session=session['yomboapi_session'])
        #     except YomboWarning as e:
        #         webinterface.add_alert("Cannot disable crontab. %s" % e.message, 'warning')
        #         return webinterface.redirect(request, '/crontab/%s/details' % crontab_id)
        #
        #     msg = {
        #         'header': 'CronTab Disabled',
        #         'label': 'CronTab disabled successfully',
        #         'description': '<p>The crontab has been disabled.'
        #                        '<p>Continue to:</p><ul>'
        #                        ' <li><strong><a href="/crontab/index">CronTab index</a></strong></li>'
        #                        ' <li><a href="/crontab/%s/details">View the disabled crontab</a></li>'
        #                        '<ul>' %
        #                        crontab.crontab_id,
        #     }
        #
        #     page = webinterface.get_template(request, webinterface.wi_dir + '/pages/display_notice.html')
        #     root_breadcrumb(webinterface, request)
        #     webinterface.add_breadcrumb(request, "/crontab/%s/details" % crontab.crontab_id, crontab.label)
        #     webinterface.add_breadcrumb(request, "/crontab/%s/disable" % crontab.crontab_id, "Disable")
        #     return page.render(alerts=webinterface.get_alerts(),
        #                        msg=msg,
        #                        )
        #
        # @webapp.route('/<string:crontab_id>/enable', methods=['GET'])
        # @require_auth()
        # def page_crontabs_enable_get(webinterface, request, session, crontab_id):
        #     session.has_access('crontab', crontab_id, 'enable', raise_error=True)
        #     try:
        #         crontab = webinterface._CronTab.get(crontab_id)
        #     except KeyError as e:
        #         webinterface.add_alert(e.message, 'warning')
        #         return webinterface.redirect(request, '/crontab/index')
        #
        #     page = webinterface.get_template(request, webinterface.wi_dir + '/pages/crontab/enable.html')
        #     root_breadcrumb(webinterface, request)
        #     webinterface.add_breadcrumb(request, "/crontab/%s/details" % crontab.crontab_id, crontab.label)
        #     webinterface.add_breadcrumb(request, "/crontab/%s/enable" % crontab.crontab_id, "Enable")
        #     return page.render(alerts=webinterface.get_alerts(),
        #                        crontab=crontab,
        #                        )
        #
        # @webapp.route('/<string:crontab_id>/enable', methods=['POST'])
        # @require_auth()
        # def page_crontabs_enable_post(webinterface, request, session, crontab_id):
        #     session.has_access('crontab', crontab_id, 'enable', raise_error=True)
        #     try:
        #         crontab = webinterface._CronTab.get(crontab_id)
        #     except KeyError as e:
        #         webinterface.add_alert(e.message, 'warning')
        #         return webinterface.redirect(request, '/crontab/index')
        #     try:
        #         confirm = request.args.get('confirm')[0]
        #     except:
        #         webinterface.add_alert('Must enter "enable" in the confirmation box to enable the crontab.', 'warning')
        #         return webinterface.redirect(request, '/crontab/%s/details' % crontab_id)
        #
        #     if confirm != "enable":
        #         webinterface.add_alert('Must enter "enable" in the confirmation box to enable the crontab.', 'warning')
        #         return webinterface.redirect(request, '/crontab/%s/details' % crontab_id)
        #
        #     try:
        #         crontab.enable(session=session['yomboapi_session'])
        #     except YomboWarning as e:
        #         webinterface.add_alert("Cannot enable crontab. %s" % e.message, 'warning')
        #         return webinterface.redirect(request, '/crontab/%s/details' % crontab_id)
        #
        #     webinterface.add_alert("CronTab '%s' enabled." % crontab.label)
        #     return webinterface.redirect(request, "/crontab/%s/details" % crontab.crontab_id)
        #
        # @webapp.route('/<string:crontab_id>/duplicate_crontab', methods=['GET'])
        # @require_auth()
        # @inlineCallbacks
        # def page_crontabs_duplicate_crontab_get(webinterface, request, session, crontab_id):
        #     session.has_access('crontab', crontab_id, 'view', raise_error=True)
        #     session.has_access('crontab', '*', 'add', raise_error=True)
        #     try:
        #         crontab = webinterface._CronTab.get(crontab_id)
        #     except KeyError as e:
        #         webinterface.add_alert(e.message, 'warning')
        #         return webinterface.redirect(request, '/crontab/index')
        #
        #     try:
        #         yield webinterface._CronTab.duplicate_crontab(crontab_id)
        #     except KeyError as e:
        #         webinterface.add_alert("Cannot duplicate crontab. %s" % e.message, 'warning')
        #         return webinterface.redirect(request, '/crontab/index')
        #
        #     webinterface.add_alert("CronTab dupllicated.")
        #     return webinterface.redirect(request, '/crontab/index')
