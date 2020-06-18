<template>
  <span>{{tweeningValue}}</span>
</template>

<script>
import TWEEN from '@tweenjs/tween.js';

export default {
  props: {
    value: {
      type: Number,
      default: 0,
      required: true
    },
    duration: {
      type: Number,
      default: 750
    }
  },
  data: function() {
    return {
      tweeningValue: 0
    }
  },
  watch: {
    value: function(newValue, oldValue) {
      this.tween(oldValue, newValue)
    }
  },
  mounted: function() {
    this.tween(0, this.value)
  },
  methods: {
    tween: function(startValue, endValue) {
      var vm = this;

      function animate() {
        if (TWEEN.update()) {
          requestAnimationFrame(animate)
        }
      }
      new TWEEN.Tween({
          tweeningValue: startValue
        })
        .to({
          tweeningValue: endValue
        }, vm.duration)
        .onUpdate(function() {
          vm.tweeningValue = this._object.tweeningValue.toFixed(0)
        })
        .start();
      animate()
    }
  }
};
</script>
