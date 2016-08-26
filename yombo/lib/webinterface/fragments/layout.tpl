<!DOCTYPE html>
<html lang="en">
   <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="">
    <meta name="author" content="">

    <title>Yombo - {{ data.gateway_label }}</title>
	{% block head_top %}{% endblock %}

    <!-- Bootstrap Core CSS ad metisMenu -->
    <link href="/static/css/bootsrap-metisMenu.min.css" rel="stylesheet">
    {% block head_css %}{% endblock %}
    {% block echarts %}{% endblock %}
    <!-- SB Admin 2 and Font Awesome CSS -->
    <link href="/static/css/admin2-font_awesome.min.css" rel="stylesheet">

	{% block head_bottom %}{% endblock %}
   </head>
   <body>
	<div id="pageLoading"></div>
	<header>
		<!-- Top Navigation -->
		{% if data.gateway_configured %}{% include 'lib/webinterface/fragments/full_top_nav.tpl' %}
		{% else %}{% include 'lib/webinterface/fragments/config_top_nav.tpl' %}
        {% endif %}
	</header>
    <div id="wrapper">
        <!-- Side Navigation -->
		{%- include 'lib/webinterface/fragments/side_nav.tpl' -%}
        <!-- Page Content -->
        <div id="page-wrapper">
            <div class="container-fluid">
                {% if alerts|length != 0 %}
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
                {% endif %}
                {% block content %}{% endblock %}
           </div>
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
   </body>
</html>

