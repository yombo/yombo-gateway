<template>
  <div class="loadingdataspinner"></div>
</template>

<style lang="less" scoped>
.loadingdataspinner {
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
  font-size: 32px;
  overflow: hidden;
  text-align: center;
  align-content: center;
  margin: 50px auto 200px;
  border-top: 16px solid blue;
  border-right: 16px solid green;
  border-bottom: 16px solid red;
  border-left: 16px solid pink;
  border-radius: 50%;
  width: 120px;
  height: 120px;
  animation: spin 3s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
