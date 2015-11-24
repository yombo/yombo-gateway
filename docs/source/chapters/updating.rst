.. updating:

##################
Update Gateway
##################

The gateway will automatically download updated modules, but the core
software must be updated manually. To complete an update, login as the
user for the software, change to the gateway directory, and run the
``git pull`` command:

.. code-block:: bash

  sudo service yombo-gateway stop
  cd /opt/yombo-gateway
  git pull
  sudo service yombo-gateway start


This will download and "patch" the gateway to latest version. When the gateway runs,
it will automatically process any required changes to the database as needed.
