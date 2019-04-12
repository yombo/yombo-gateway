<template>
  <div>
    <div class="row">
      <div class="col-md-12">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h2 class="card-title">
                Gateway Backup
              </h2>
            </div>
            <p>
                Although the configuration information is stored on Yombo servers, much of the information
                is encrypted using the gateway's GPG keys, which Yombo does not have access to or store. As such,
                it's important to backup the gateway shortly after installation.<br>
            </p>
            <p>
                There are two backups:
            </p>
                <ul>
                    <li><stong>Configuration</stong> - Saves GPG keys and yombo.ini.
                    <li><stong>Database</stong> - Current database state. Includes historical info.</li>
                </ul>
            <p>
                The <strong>configuration backup</strong> is the most important backup as well as the most sensitive.
                This backup includes GPG encryption keys and the Configuration file. Since all system passwords, as
                well as potential passwords for remote acces, you must keep this backup in a safe place. We highly
                encourage you to use the password backup feature which uses strong AES encryption.
            </p>
            <p>
                The <strong>database backup</strong> simply contains the database file. It's only important to
                periodically backup this file to preserve statistics information. The configurations within
                the database can be restored from the Yombo servers if needed.
            </p>
          </card>
      </div>
    </div>

    <div class="row">
      <div class="col-md-6">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h3 class="card-title">
                Configuration backup
              </h3>
              <p>
                Create a configuration backup, used to quickly reinstall the gateway software without
                loosing important information.
              </p>
              <p>
                <strong>Don't forget your password, there is no possible way to recover the
                data without the password.</strong>
              </p>
            </div>
            <form method="post" action="/system/backup/configuration">
              <label style="margin-top: 0px; margin-bottom: 0px">Password: </label><br>
              <div class="input-group">
                  <input type="password" tabindex="1" class="form-control" name="password1" id="password1" size="25" required>
              </div>

              <label style="margin-top: 0px; margin-bottom: 0px">Confirm password: </label><br>
              <div class="input-group">
                  <input type="password" tabindex="1" class="form-control" name="password2" id="password2" size="25" required>
              </div>
              <br>
              <button type="submit" class="btn btn-success">Download encrypted backup</button>
              </form>
              <p><br>
                  If desired, you can also download an un-encrypted version of the configuration data.
              </p>
              <a href="/system/backup/configuration" class="btn btn-md btn-danger">Download plaintext backup<br>
                <strong>Not recommended!</strong></a>
          </card>
      </div>

      <div class="col-md-6">
          <card class="card-chart" no-footer-line>
            <div slot="header">
              <h3 class="card-title">
                Database backup
              </h3>
            </div>
            <p>
                Current database size: -DB SIZE HERE-
            </p>
            <p>
                <a href="/system/backup/database" class="btn btn-md btn-primary">Download Database</a>
            </p>
            <p>
                You can also manually backup the database:<br>
              {{ sqlite3 }}

            </p>
          </card>
      </div>
    </div>

  </div>
</template>
<script>
  export default {
  layout: 'dashboard',
  computed: {
      sqlite3: function () {
        console.log(window.$nuxt.$gwenv);
      return window.$nuxt.$gwenv['working_dir'] + "/etc/yombo.sqlite3";
      }
  // },
  // methods: {
  //   addTodo (e) {
  //     this.$store.commit('todos/add', e.target.value)
  //     e.target.value = ''
  //   }
  }



};
</script>
<style scoped>
.table-transparent {
  background-color: transparent !important;
}
</style>
