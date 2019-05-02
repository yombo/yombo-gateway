<template>
    <div id='footer'>
      <div id='footer-title'>
        Yombo Gateway: {{systemInfo.label}}
        <div class="pull-right">
          <small>Version: {{systemInfo.version}}</small> &nbsp;
        </div>
      </div>
    </div>
</template>

<script>
  export default {
    computed: {
      systemInfo: function () {
        return this.$store.state.gateway.systeminfo;
      }
    }
  }
  // https://www.thepolyglotdeveloper.com/2018/04/vuejs-app-using-axios-vuex/
</script>

<style scoped>
  #footer {
    height:auto;
    background: #2a5687;
    text-align:center;
    position:fixed;
    bottom:0px;
    width:100%;
    color:white;
  }
  #footer-title {
    line-height:40px;
    font-size:18px;
    font-weight:bold;
  }
  #footer-copyright {
    /*line-height:20px;*/
    font-size:14px;
  }
</style>
