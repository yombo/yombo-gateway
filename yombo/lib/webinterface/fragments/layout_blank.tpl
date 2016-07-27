<!DOCTYPE html>
<html lang="en">
<html>
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
    <!-- SB Admin 2 and Font Awesome CSS -->
    <link href="/static/css/admin2-font_awesome.min.css" rel="stylesheet">

	{% block head_bottom %}{% endblock %}
   </head>
   <body>
	<div id="pageLoading"></div>
    <div id="wrapper">

        <!-- Page Content -->
            <div class="container-fluid">
                {% if alerts|length != 0 %}
                <div class="row">
                    <div class="col-lg-12">
                        <div>&nbsp;</div>
                        <div class="panel panel-default">
                           <!-- /.panel-heading -->
                           <div class="panel-body">{% for key, alert in alerts.iteritems() %}{% if alert.dismissable %}
                              <div class="alert alert-{{ alert.level }} alert-dismissable">
                                <button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>
                                {{ alert.message }}.
                              </div>{% else %}
                              <div class="alert alert-{{ alert.level }}">
                                {{ alert.message }}.
                              </div>{% endif %}{% endfor %}
                           </div>
                        </div>

                    </div>
                    <!-- /.col-lg-12 -->
                </div>
                <!-- /.row -->
                {% endif %}
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
    {% if data.display_captcha %}<div class="g-recaptcha" data-sitekey="6Lf-ECYTAAAAADt-HAksVV_OsiFEziODndQe-xnq"></div>{% endif %}

   {% block body_bottom %}{% endblock %}
   </body>
</html>

