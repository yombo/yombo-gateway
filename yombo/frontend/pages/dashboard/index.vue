<template>
  <div>
    <div class="row">
      <div class="col-md-12">
        <div class="card card-stats card-raised">
          <div class="card-body">
            <div class="row">
              <div class="col-md-3">
                <div class="statistics">
                  <div class="info">
                    <nuxt-link :to="localePath('dashboard-devices')" class="dropdown-item">
                    <div class="icon icon-primary">
                      <i class="fas fa-wifi fa-2x"></i>
                    </div>
                    <h3 class="info-title">
                      <animated-number :value="device_count"></animated-number>
                    </h3>
                    </nuxt-link>
                    <h6 class="stats-title">
                      <drop-down tag="div" :title="$t('ui.navigation.devices')">
                        <nuxt-link :to="localePath('dashboard-devices')" class="dropdown-item">View</nuxt-link>
                        <nuxt-link :to="localePath('dashboard-devices-add')" class="dropdown-item">Add</nuxt-link>
                        <nuxt-link :to="localePath('controltower')" class="dropdown-item">Control Tower</nuxt-link>
                      </drop-down>
                    </h6>
                  </div>
                </div>
              </div>
              <div class="col-md-3">
                <div class="statistics">
                  <div class="info">
                    <div class="icon icon-success">
                      <i class="fas fa-clock fa-3x"></i>
                    </div>
                    <h3 class="info-title">
                      <animated-number :value="1"></animated-number>
                    </h3>
                    <h6 class="stats-title">{{ $t('ui.navigation.delayed_commands') }}</h6>
                  </div>
                </div>
              </div>
              <div class="col-md-3">
                <div class="statistics">
                  <div class="info">
                    <div class="icon icon-info">
                      <i class="now-ui-icons users_single-02"></i>
                    </div>
                    <h3 class="info-title">
                      <animated-number :value="135"></animated-number>
                    </h3>
                    <h6 class="stats-title">{{ $t('ui.navigation.commands') }}</h6>
                    <small>In last 24 hours</small>

                  </div>
                </div>
              </div>
              <div class="col-md-3">
                <div class="statistics">
                  <div class="info">
                    <div class="icon icon-danger">
                      <i class="now-ui-icons objects_support-17"></i>
                    </div>
                    <h3 class="info-title">
                      <animated-number :value="353"></animated-number>
                    </h3>
                    <h6 class="stats-title">Something</h6>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>

    <div class="row">
      <div class="col-lg-6">
        <card class="card-chart" no-footer-line>
          <div slot="header">
            <h5 class="card-category">Commands Performed</h5>
            <h2 class="card-title">
              <animated-number :value="436">
              </animated-number>
            </h2>
            <drop-down :hide-arrow="true" position="right">
              <n-button slot="title" class="dropdown-toggle no-caret" round simple icon>
                <i class="now-ui-icons loader_gear"></i>
              </n-button>

              <a class="dropdown-item" href="#">Action1</a>
              <a class="dropdown-item" href="#">Another action2</a>
              <a class="dropdown-item" href="#">Something else here3</a>
              <a class="dropdown-item text-danger" href="#">Remove Data</a>
            </drop-down>

          </div>
          <div class="chart-area">
            <line-chart :labels="charts.activeUsers.labels"
                       :data="charts.activeUsers.data"
                       :color="charts.activeUsers.color"
                       :height="200">
            </line-chart>
          </div>
          <div class="table-responsive">
            <n-table :data="tableData">
              <template slot-scope="{row}">
                <td>{{row.country}}</td>
                <td class="text-right">
                  {{row.value}}
                </td>
                <td class="text-right">
                  {{row.percentage}}
                </td>
              </template>
            </n-table>
          </div>
          <div slot="footer" class="stats">
            <i class="now-ui-icons arrows-1_refresh-69"></i> Just Updated
          </div>
        </card>
      </div>

      <div class="col-lg-6">
        <card class="card-chart" no-footer-line>
          <div slot="header">
            <h5 class="card-category">Some other Metric</h5>
            <h2 class="card-title">
              <animated-number :value="55300">
              </animated-number>
            </h2>
            <drop-down position="right">
              <n-button slot="title" class="dropdown-toggle no-caret" round simple icon>
                <i class="now-ui-icons loader_gear"></i>
              </n-button>

              <a class="dropdown-item" href="#">Action</a>
              <a class="dropdown-item" href="#">Another action</a>
              <a class="dropdown-item" href="#">Something else here</a>
              <a class="dropdown-item text-danger" href="#">Remove Data</a>
            </drop-down>

          </div>
          <div class="chart-area">
            <line-chart :labels="charts.emailsCampaign.labels"
                       :data="charts.emailsCampaign.data"
                       :color="charts.emailsCampaign.color"
                       :height="200">
            </line-chart>
          </div>
          <div class="card-progress">
            <n-progress label="Electric Usage" :value="90" show-value></n-progress>
            <n-progress type="success" label="Gas Usage" :value="5" show-value></n-progress>
            <n-progress type="info" label="Water Usage" :value="12" show-value></n-progress>
            <n-progress type="warning" label="Noise Pollution" :value="60" show-value></n-progress>
          </div>
          <div slot="footer" class="stats">
            <i class="now-ui-icons arrows-1_refresh-69"></i> Just Updated
          </div>
        </card>
      </div>
    </div>
  </div>
</template>
<script>

import LineChart from '../../components/Common/Charts/LineChart';
import Command from '@/models/command'
import Device from '@/models/device'

import {
  StatsCard,
  Card,
  Table as NTable,
  Checkbox,
  AnimatedNumber,
  Progress as NProgress
} from '@/components/Common';

export default {
  layout: 'dashboard',
  components: {
    Checkbox,
    Card,
    NTable,
    StatsCard,
    AnimatedNumber,
    NProgress,
    LineChart
  },
  data() {
    return {
      progress: 0,
      charts: {
        activeUsers: {
          labels: [
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep',
            'Oct',
            'Nov',
            'Dec'
          ],
          data: [542, 480, 430, 550, 530, 453, 380, 434, 568, 610, 700, 630],
          color: '#f96332'
        },
        emailsCampaign: {
          labels: ['12pm,', '3pm', '6pm', '9pm', '12am', '3am', '6am', '9am'],
          data: [40, 500, 650, 700, 1200, 1250, 1300, 1900],
          color: '#18ce0f'
        },
        activeCountries: {
          labels: [
            'January',
            'February',
            'March',
            'April',
            'May',
            'June',
            'July',
            'August',
            'September',
            'October'
          ],
          data: [80, 78, 86, 96, 83, 85, 76, 75, 88, 90],
          color: '#2CA8FF'
        }
      },
      tableData: [
        {
          country: 'USA',
          value: '2.920',
          percentage: '53.23%'
        },
        {
          country: 'Germany',
          value: '1.300',
          percentage: '20.43%'
        },
        {
          country: 'Australia',
          value: '760',
          percentage: '10.35%'
        },
        {
          country: 'United Kingdom',
          value: '690',
          percentage: '7.87%'
        },
        {
          country: 'United Kingdom',
          value: '600',
          percentage: '5.94%'
        },
        {
          country: 'Brasil',
          value: '550',
          percentage: '4.34%'
        }
      ],
      productsTable: [
        {
          image: 'img/saint-laurent.jpg',
          title: 'Suede Biker Jacket',
          subTitle: 'by Saint Laurent',
          color: 'Black',
          size: 'M',
          price: 3390,
          quantity: 1,
          amount: 3390
        },
        {
          image: 'img/balmain.jpg',
          title: 'Jersey T-Shirt ',
          subTitle: 'by Balmain',
          color: 'Black',
          size: 'M',
          price: 499,
          quantity: 2,
          amount: 998
        },
        {
          image: 'img/prada.jpg',
          title: 'Slim-Fit Swim Short ',
          subTitle: 'by Prada',
          color: 'Red',
          size: 'M',
          price: 200,
          quantity: 1,
          amount: 200
        }
      ],
      mapData: {
        AU: 760,
        BR: 550,
        CA: 120,
        DE: 1300,
        FR: 540,
        GB: 690,
        GE: 200,
        IN: 200,
        RO: 600,
        RU: 300,
        US: 2920
      }
    };
  },
  computed: {
    device_count () {
      return Device.query().count();
    },
    command_count () {
      return Command.query().count();
    },
    device_age () {
      return (new Date(Date.now()/1000)) - this.$store.state.devices.last_download_at
    },
    devices () {
      return Device.query().with('locations').orderBy('id', 'desc').get()
    }
  },
  created: function () {
    console.log("dashboard home: created....")
    this.$store.dispatch('yombo/categories/refresh');
    this.$store.dispatch('yombo/commands/refresh');
    this.$store.dispatch('yombo/device_command_inputs/refresh');
    this.$store.dispatch('yombo/device_type_commands/refresh');
    this.$store.dispatch('yombo/device_types/refresh');
    this.$store.dispatch('yombo/devices/refresh');
    this.$store.dispatch('yombo/gateways/refresh');
    this.$store.dispatch('yombo/input_types/refresh');
    this.$store.dispatch('yombo/locations/refresh');
    this.$store.dispatch('yombo/modules/refresh');
    this.$store.dispatch('yombo/module_device_types/refresh');
  },
};
</script>
<style>
</style>
