<!DOCTYPE html>
<html>
   <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="">
    <meta name="author" content="">

    <title>{{ misc_wi_data.gateway_label() }} - Yombo</title>
	{% block head_top %}{% endblock %}

    <!-- Bootstrap Core CSS ad metisMenu -->
    <link href="/static/css/bootstrap-metisMenu.min.css" rel="stylesheet">
    <!-- SB Admin 2 -->
    <link href="/static/css/admin2.min.css" rel="stylesheet">
    {% block head_css %}{% endblock %}
    <script defer src="/static/js/fontawesome-all.min.js"></script>

	{% block head_bottom %}{% endblock %}
   </head>
   <body>
	<div id="pageLoading"></div>
    <div id="wrapper">

        <!-- Page Content -->
            <div class="container-fluid">
                {%- if alerts|length != 0 %}
                <div class="row">
                    <div class="col-lg-12">
                        <div>&nbsp</div>
                          {% for key, alert in alerts.items() %}{% if alert.dismissable %}
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
                          {% for key, notification in misc_wi_data.notifications.notifications.items() if notification.always_show -%}
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
                {% block content %}{% endblock %}
           </div>
            <!-- /.container-fluid -->

    </div>
    <!-- /#wrapper -->

    <!-- jQuery, js.cookie, bootstrap, metisMenu -->
    <script src="/static/js/jquery-cookie-bootstrap-metismenu.min.js"></script>

    {% block body_bottom_js %}{% endblock %}

    <!-- Custom Theme JavaScript -->
    <script src="/static/js/sb-admin2.min.js"></script>
    {% if misc_wi_data.display_captcha %}<div class="g-recaptcha" data-sitekey="6Lf-ECYTAAAAADt-HAksVV_OsiFEziODndQe-xnq"></div>{% endif %}

   {% block body_bottom %}{% endblock %}
   </body>
</html>

