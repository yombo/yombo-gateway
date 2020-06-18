<!DOCTYPE html>
<html>
   <head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      @import url('https://fonts.googleapis.com/css?family=Open+Sans');
       @media screen and (min-width: 1365px) {
          body {
           background-image: url('/img/bg/{{ bg_image_id() }}_2048.jpg');
          }
       }

       @media screen and (min-width: 601px) and (max-width:1364px) {
          body {
           background-image: url('/img/bg/{{ bg_image_id() }}_1364.jpg');
          }
       }

       @media screen and (max-width:600px) {
          body {
           background-image: url('/img/bg/{{ bg_image_id() }}_600.jpg');
          }
       }

       @media (max-width: 767px) {
          #content .modal.fade.in {
            top: 5%;
          }
       }

       html,body{
           font-family: 'Open Sans', sans-serif !important;
       }

       html,
           body {
           height: 100%;
       }

       body {
           background-repeat: no-repeat;
           background-size: cover;
           background-color: #4887AF !important;
       }

       .container{
           height: 100%;
           align-content: center;
       }

      .card{
           color: white;
           /*height: 370px;*/
           margin-top: auto;
           margin-bottom: auto;
           /*width: 400px;*/
           background-color: rgba(0,0,0,0.88) !important;
           border-radius: 1rem !important;
       }

       .card-header{
           border-bottom: 1px solid rgba(255,255,255,.2) !important;
       }

       .card-header h3{
           color: white;
       }

       .input-group-prepend span{
           width: 50px;
           background-color: #FFC312;
           color: black;
           border:0 !important;
       }

       input:focus{
           outline: 0 0 0 0  !important;
           box-shadow: 0 0 0 0 !important;

       }

       .links{
           color: white;
       }

       .links a{
           margin-left: 4px;
       }

       pre {
         color: white !important;
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
    <title>{{ misc_wi_data.gateway_label.value }} - Yombo</title>

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
   {% if authentication is defined and authentication is not none %}
       {% set alerts = authentication.get_alerts() %}
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

    <script defer src="https://use.fontawesome.com/releases/v5.11.2/js/all.js" crossorigin="anonymous"></script>
    <!-- jQuery, js.cookie, bootstrap4, bootstrap select, bootstrap datatables, are you sure -->
    <script src="/js/basic_app.js"></script>
    {% block body_bottom_js %}{% endblock %}
    {% block body_bottom %}{% endblock %}
   </body>
</html>
