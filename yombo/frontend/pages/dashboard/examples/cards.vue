<template>
  <span>
    <card class="card-chart" no-footer-line>
      <div slot="header">
        <h2 class="card-title">
          Frontend layout examples - Cards
        </h2>
      </div>
      <p>Various cards by example.</p>
      <br>
      <div>
        <div>
          <b-card-group deck>
            <b-card bg-variant="primary" text-variant="white" header="Primary" class="text-center">
              <b-card-text>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</b-card-text>
            </b-card>

            <b-card bg-variant="secondary" text-variant="white" header="Secondary" class="text-center">
              <b-card-text>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</b-card-text>
            </b-card>

            <b-card bg-variant="success" text-variant="white" header="Success" class="text-center">
              <b-card-text>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</b-card-text>
            </b-card>
          </b-card-group>
        </div>
        <div class="mt-3">
          <b-card-group deck>
            <b-card bg-variant="info" text-variant="white" header="Info" class="text-center">
              <b-card-text>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</b-card-text>
            </b-card>

            <b-card bg-variant="warning" text-variant="white" header="Warning" class="text-center">
              <b-card-text>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</b-card-text>
            </b-card>

            <b-card bg-variant="danger" text-variant="white" header="Danger" class="text-center">
              <b-card-text>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</b-card-text>
            </b-card>
          </b-card-group>
        </div>
        <div class="mt-3">
          <b-card-group deck>
            <b-card bg-variant="light" header="Light" class="text-center">
              <b-card-text>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</b-card-text>
            </b-card>

            <b-card bg-variant="dark" header="Dark" text-variant="white" class="text-center">
              <b-card-text>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</b-card-text>
            </b-card>

            <b-card header="Default" class="text-center">
              <b-card-text>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</b-card-text>
            </b-card>
          </b-card-group>
        </div>
      </div>
    </card>
  </span>
</template>
<script>

export default {
  layout: 'dashboard',
};
</script>
<style scoped>
.table-transparent {
  background-color: transparent !important;
}
</style>
