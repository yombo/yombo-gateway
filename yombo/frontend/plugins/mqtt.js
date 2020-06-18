import mqtt from 'mqtt';

import database from '@/database/index'
import extend from '~/util/extend-vue-app'

import { Local_Presence } from '@/models/local_presence'

export default function ({ app }) {
  extend(app, {
    data() {
      return {
        mqtt: null,
      };
    },
    methods: {
      /**
       * Much like the do_inserts from db_mutations.js file, this accepts JSON API data and
       * updates the various local vuex orm items.
       */
      async do_inserts(incoming) {
        if (!(incoming instanceof Array)) {
          incoming = [incoming];
        }
        let Model = null;
        let model_name = null;
        let temp_model_name = null;
        let models_updated = {};
        Object.keys(incoming).forEach(key => {
          temp_model_name = `gw_${incoming[key]['type']}`
          if (model_name !== temp_model_name || Model === null) {
            model_name = temp_model_name;
            if (!(model_name in models_updated)) {
              models_updated[model_name] = [];
            }
            Model = database.model(model_name);
          }
          Model.insertOrUpdate({
            data: incoming[key]['attributes'],
          });
          models_updated[model_name].push(incoming[key]['id']);
        });
        return models_updated;
      },
      async incoming_yombo_mqtt_presence(topic, message, packet) {
        let topics = topic.split("/")

        await Local_Presence.create({
          data: {
            id: `${topics[1]}-${topics[2]}`,
            presence_type: topics[1],
            presence_id: topics[2],
            updated_at: Number(Date.now()),
          }
        });
      },
      async incoming_yombo_mqtt_general(topic, message, packet) {
        let payload = message.toString();
        if ('contentType' in packet.properties) {
          if (packet.properties.contentType === 'json') {
            try {
              payload = JSON.parse(payload);
            }
            catch(err) {
              console.log(`Error decode JSON message from MQTT: ${err}`);
              return;
            }

          }
        }
        if (!("jsonapi" in packet.properties.userProperties)) {
          return;
        }

        let models_updated_data = await this.do_inserts(payload['data']);

        let models_updated_includes = {};
        if(typeof(payload.included) !== "undefined") {
          models_updated_includes = await this.do_inserts(payload['included']);
        }

        let models_updated = {...models_updated_data, ...models_updated_includes};
        if (Object.keys(models_updated).length >= 0) {
          for (let key in models_updated) {
            let ids = models_updated[key];
            window.$nuxt.$bus.$emit(`store_${key}_updated`, ids);
          }
        }
      }
    },
    beforeMount() {
      let nuxtEnv = this.$store.state.nuxtenv;
      // console.log(`nuxtenv: ${JSON.stringify(this.$store.state.nuxtenv)}`);
      const protocol = ('https:' == document.location.protocol ? 'wss://' : 'ws://');
      const portPart = ('https:' == document.location.protocol ?
        nuxtEnv['mqtt_port_websockets_ssl'] : nuxtEnv['mqtt_port_websockets']);
      const uriBase =  protocol + document.location.hostname + ":" + portPart;
      const session = this.$store.state.gateway.access_token.session;

      let options = {
        username: `web-${session}`,
        password: "1",  // Need something here, not checked.
        clean: true,
        reconnectPeriod: 2000,
        protocolVersion: 5,
      }
      this.mqtt = mqtt.connect(uriBase, options);
      let that = this;
      that.mqtt.on('connect', function () {
        that.mqtt.subscribe('yombo_presence/#',
        {
            properties: {
              subscriptionIdentifier: 4
            }
              });
        that.mqtt.subscribe('yombo/#',
          {
            properties: {
              subscriptionIdentifier: 5
            }
          },
          function (err) {
          if (!err) {
            console.log("mqtt publishing to mytest");
            that.mqtt.publish('yombo/mytest', 'Hello mqtt', {properties: {
              userProperties: {thisisatest: "asdfasdf"}
              }})
          }
        })
      });
      this.mqtt.on('message', function (topic, message, packet) {
        // console.log(`mqtt got message: ${topic}`);
        // console.log(JSON.stringify(packet.properties));
        if (packet.properties.subscriptionIdentifier == 4) {
          that.incoming_yombo_mqtt_presence(topic, message, packet);
          return;
        }
        if (packet.properties.subscriptionIdentifier == 5) {
          that.incoming_yombo_mqtt_general(topic, message, packet);
          return;
        }
      });
    },
    beforeDestroy() {
      this.mqtt.end()
    }
  })
}
