<style>
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

   body {
       background-repeat: no-repeat;
       background-size: cover;
       background-color: #4887AF !important;
   }
   html,
       body {
       height: 100%;
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