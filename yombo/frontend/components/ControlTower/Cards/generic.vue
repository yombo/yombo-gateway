<template>
  <span>
    <card class="card-state">
      <div slot="header">
        <h6 class="card-title">
          <nuxt-link
              :to="localePath({name: 'dashboard-devices-id-details', params: {id: device.id}})">
            {{device.full_label}}
          </nuxt-link>
        </h6>
      </div>
      <span v-for="(command, key, index) in commands">
        <a href="" v-on:click.prevent.stop="sendCommand(device, command)">{{ command.label }}</a><span v-if="index != Object.keys(commands).length - 1">&#9900;</span>
      </span>
      <br>
      {{state.human_state}}
      <br>
      {{state.human_message}}
      <br>
    </card>
  </span>
</template>

<script>

export default {
  name: 'generic-card',
  props: {
    device: Object,
    state: Object,
    commands: Object,
  },
  methods: {
    sendCommand(device, command) {
      console.log("Send command for de4vice: " + device.full_label + "  Command: " + command.label);
      this.$nuxt.$gwapiv1.devices().sendCommand(device.id, command.id);

    },
  },
};
</script>
