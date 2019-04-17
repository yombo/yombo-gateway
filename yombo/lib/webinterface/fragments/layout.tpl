<!DOCTYPE html>
<html>
   <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      @import url('https://fonts.googleapis.com/css?family=Open+Sans');
       html,body{
           font-family: 'Open Sans', sans-serif !important;
       }
    </style>
	{% block head_top %}{% endblock %}
    <link rel="apple-touch-icon" sizes="180x180" href="/img/icons/apple-touch-icon.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/img/icons/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/img/icons/favicon-16x16.png">
    <link rel="manifest" href="/img/icons/site.webmanifest">
    <link rel="mask-icon" href="/img/icons/safari-pinned-tab.svg" color="#5bbad5">
    <link rel="shortcut icon" href="/img/icons/favicon.ico">
    <meta name="msapplication-TileColor" content="#da532c">
    <meta name="msapplication-config" content="/img/icons/browserconfig.xml">
    <meta name="theme-color" content="#ffffff">

    <title>{{ misc_wi_data.gateway_label() }} - Yombo</title>

    <!-- Bootstrap4 Core CSS, bootstrap select-->
    <link href="/css/basic_app.min.css" rel="stylesheet">
    {% block head_css %}{% endblock %}
	{% block head_bottom %}{% endblock %}
    {%- if nuxtpreload is defined %}
       {%- for nuxtjs in nuxtpreload %}
         <link rel="preload" href="/_nuxt/{{nuxtjs[1]}}" as="script">
       {%- endfor %}
    {%- endif %}
   </head>
   <body>
   {% if variable is defined %}
       {% set alerts = get_alerts(session) %}
   {% else %}
       {% set alerts = {} %}
   {% endif %}
   {%- if alerts|length != 0 %}
       <div class="alert-messages" style="z-index: 999;">
       {%- for key, alert in alerts.items() %}
          {%- if alert.deletable %}
            <div class="alert alert-{{ alert.level }} alert-dismissible fade show" role="alert" data-the_alert_id="{{ key }}"">
              {{ alert.message }}
              <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
          {%- else %}
              <div class="alert alert-{{ alert.level }}" role="alert">
                {{ alert.message }}
              </div>
          {%- endif -%}
       {%- endfor -%}
       </div>
    {%- endif %}
    {%- block content %}{% endblock %}

    <script defer src="https://use.fontawesome.com/releases/v5.8.1/js/all.js" integrity="sha384-g5uSoOSBd7KkhAMlnQILrecXvzst9TdC09/VM+pjDTCM+1il8RHz5fKANTFFb+gQ" crossorigin="anonymous"></script>
    <!-- jQuery, js.cookie, bootstrap4, bootstrap select, bootstrap datatables, are you sure -->
    <script src="/js/basic_app.js"></script>
    {% block body_bottom_js %}{% endblock %}
   {% block body_bottom %}{% endblock %}
   </body>
</html>

