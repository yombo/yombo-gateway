<template>
  <div style="background: rgba(0, 0 ,0, 0);" >
    <GeneralNavbar />
    <nuxt />
    <GeneralFooter />
  </div>
</template>

<script>
  import GeneralFooter from '@/layouts/partials/GeneralFooter.vue';
  import GeneralNavbar from '@/layouts/partials/GeneralNavbar'

  export default {
    components: {
      GeneralNavbar,
      GeneralFooter,
    },
    computed: {
      bgImageNumber: function () {
        return 1;
      },
    }

  }
</script>

<style>
     /*html,body{*/
       /*background-position: center;*/
       /*background-size: cover;*/
       /*background-repeat: no-repeat;*/
       /*height: 100%;*/
       /*font-family: 'Numans', sans-serif;*/
   /*}*/
body {
  font-family: 'Open Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI',
    Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 16px;
  word-spacing: 1px;
  -ms-text-size-adjust: 100%;
  -webkit-text-size-adjust: 100%;
  -moz-osx-font-smoothing: grayscale;
  -webkit-font-smoothing: antialiased;
  /*box-sizing: border-box;*/
  background-image: url('http://localhost:8080/img/bg/1_1536.jpg');
    /*background-size: contain;*/
  background-repeat: no-repeat;
  -webkit-background-size: cover;
  -moz-background-size: cover;
  -o-background-size: cover;
  background-size: cover;
  background-position: right top;
  /*width: 100%;*/
  /*height: 100%;*/
  /*overflow: hidden;*/
}
*,
*:before,
*:after {
  box-sizing: border-box;
  margin: 0;
}
.button--green {
  display: inline-block;
  border-radius: 4px;
  border: 1px solid #3b8070;
  color: #3b8070;
  text-decoration: none;
  padding: 10px 30px;
}
.button--green:hover {
  color: #fff;
  background-color: #3b8070;
}
.button--grey {
  display: inline-block;
  border-radius: 4px;
  border: 1px solid #35495e;
  color: #35495e;
  text-decoration: none;
  padding: 10px 30px;
  margin-left: 15px;
}
.button--grey:hover {
  color: #fff;
  background-color: #35495e;
}
</style>
