<!DOCTYPE html>
<html lang="en">
   <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="">
    <meta name="author" content="">

    <title>Yombo - {{ misc_wi_data.gateway_label }}</title>
	{% block head_top %}{% endblock %}

    <!-- Bootstrap Core CSS ad metisMenu -->
    <link href="/static/css/bootsrap-metisMenu.min.css" rel="stylesheet">
    {% block head_css %}{% endblock %}
    {% block echarts %}{% endblock %}
    <!-- SB Admin 2 and Font Awesome CSS -->
    <link href="/static/css/admin2.min.css" rel="stylesheet">
    <link href="/static/css/font_awesome.min.css" rel="stylesheet">

	{% block head_bottom %}{% endblock %}
   </head>
   <body>
	<div id="pageLoading"></div>
	<header>
		<!-- Top Navigation -->
		{% if misc_wi_data.gateway_configured %}{% include 'lib/webinterface/fragments/full_top_nav.tpl' %}
		{% else %}{% include 'lib/webinterface/fragments/config_top_nav.tpl' %}
        {% endif %}
	</header>

    <div class="modal fade" id="logoutModal" tabindex="-1" role="dialog" aria-labelledby="logoutModalLabel">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
            <h4 class="modal-title" id="myModalLabel">Confirm Logout</h4>
          </div>
          <div class="modal-body">
              <p>Ready to logout?</p>
          </div>
          <div class="modal-footer">
              <a href="#" id="logoutBtnYes" class="btn btn-danger">Yes</a>
              <a href="#" data-dismiss="modal" aria-hidden="true" class="btn btn-primary">No</a>
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" id="restartModal" tabindex="-1" role="dialog" aria-labelledby="restartModalLabel">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
            <h4 class="modal-title" id="myModalLabel">Confirm Restart</h4>
          </div>
          <div class="modal-body">
              <p>Restart the Yombo Automation Gateway?</p>
          </div>
          <div class="modal-footer">
              <a href="#" id="restartBtnYes" class="btn btn-danger">Yes</a>
              <a href="#" data-dismiss="modal" aria-hidden="true" class="btn btn-primary">No</a>
          </div>
        </div>
      </div>
    </div>

    <div class="modal fade" id="shutdownModal" tabindex="-1" role="dialog" aria-labelledby="shutdownModalLabel">
      <div class="modal-dialog" role="document">
        <div class="modal-content">
          <div class="modal-header">
            <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
            <h4 class="modal-title" id="myModalLabel">Confirm Shutdown</h4>
          </div>
          <div class="modal-body">
              <p>Are you sure you want to shutdown the gateway?</p>
              <div class="bs-callout bs-callout-danger" id=callout-images-ie-rounded-corners>
                  <h4>Warning</h4>
                  <p>
                      By shutting down the gateway softawre, this web interface will no longer function. The gateway
                      software will need to be manually started.
                  </p>
              </div>
          </div>
          <div class="modal-footer">
              <a href="#" id="shutdownBtnYes" class="btn btn-danger">Yes</a>
              <a href="#" data-dismiss="modal" aria-hidden="true" class="btn btn-primary">No</a>
          </div>
        </div>
      </div>
    </div>

    <div id="wrapper">
        <!-- Side Navigation -->
		{%- include 'lib/webinterface/fragments/side_nav.tpl' -%}
        <!-- Page Content -->
        <div id="page-wrapper">
                {%- if alerts|length != 0 %}
                <div class="row">
                    <div class="col-lg-12">
                        <div>&nbsp</div>
                          {% for key, alert in alerts.iteritems() %}{% if alert.dismissable %}
                          <div class="alert alert-{{ alert.level }} alert-dismissable" data-the_alert_id="{{ key }}">
                            <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>
                            {{ alert.message }}
                          </div>{% else %}
                          <div class="alert alert-{{ alert.level }}">
                            {{ alert.message }}.
                          </div>{% endif %}{% endfor %}
                    </div>
                    <!-- /.col-lg-12 -->
                </div>
                <!-- /.row -->
                {%- endif -%}
                {%- if misc_wi_data.notifications.always_show_count != 0 %}
                <div class="row">
                    <div class="col-lg-12">
                        <div>&nbsp</div>
                          {% for key, notification in misc_wi_data.notifications.iteritems() if notification.always_show -%}
                          {%- if notification.always_show_allow_clear -%}
                          <div class="alert alert-{{ misc_wi_data.notification_priority_map_css[notification.priority] }} alert-dismissable" data-the_alert_id="{{ key }}">
                            <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>
                            <strong><a href="/notifications/details/{{notification.notification_id}}" title="Show notification">{{ notification.title }}</a>:</strong> {{ notification.message }}
                          </div>
                          {%- else -%}
                          <div class="alert alert-{{ misc_wi_data.notification_priority_map_css[notification.priority]}}">
                              <strong><a href="/notifications/details/{{notification.notification_id}}" title="Show notification">{{ notification.title }}</a>:</strong> {{ notification.message }}
                          </div>
                          {%- endif -%}
                        {%- endfor -%}
                    </div>
                    <!-- /.col-lg-12 -->
                </div>
                <!-- /.row -->
                {%- endif -%}
                {%- if misc_wi_data.breadcrumb|length > 0 -%}
                <div class="row">
                    <div class="col-lg-12">
                        <div class="breadcrumbs">
                        {%- for breadcrumb in misc_wi_data.breadcrumb -%}
                            {% if loop.last or breadcrumb.show == false %}
                                {{ breadcrumb.text }}
                            {% else %}
                                <a href="{{ breadcrumb.url }}">{{ breadcrumb.text }}</a>
                            {% endif %}

                        {{ ' <i class="fa fa-angle-double-right" aria-hidden="true"></i> ' if not loop.last }}
                        {%- endfor -%}
                        </div>
                    <!-- /.col-lg-12 -->
                    </div>
                <!-- /.row -->
                </div>
                {%- endif -%}
                {% block content %}{% endblock %}
            <!-- /.container-fluid -->
        </div>
        <!-- /#page-wrapper -->

    </div>
    <!-- /#wrapper -->

    <!-- jQuery, js.cookie, bootstrap, metisMenu -->
    <script src="/static/js/jquery-cookie-bootstrap-metismenu.min.js"></script>

    {% block body_bottom_js %}{% endblock %}

    <!-- Custom Theme JavaScript -->
    <script src="/static/js/sb-admin2.min.js"></script>

   {% block body_bottom %}{% endblock %}
    <script>


    $('.confirm-logout').on('click', function(e) {
        e.preventDefault();
        var id = $(this).data('id');
        $('#logoutModal').data('id', id).modal('show');
    });
    $('#logoutBtnYes').click(function() {
        $('#logoutModal').modal('hide');
        window.location.href = "/logout";
    });

    $('.confirm-restart').on('click', function(e) {
        e.preventDefault();
        var id = $(this).data('id');
        $('#restartModal').data('id', id).modal('show');
    });
    $('#restartBtnYes').click(function() {
        $('#restartModal').modal('hide');
        window.location.href = "/system/control/restart";
    });

    $('.confirm-shutdown').on('click', function(e) {
        e.preventDefault();
        var id = $(this).data('id');
        $('#shutdownModal').data('id', id).modal('show');
    });
    $('#shutdownBtnYes').click(function() {
        $('#shutdownModal').modal('hide');
        window.location.href = "/system/control/shutdown";
    });

</script>
   </body>
</html>

