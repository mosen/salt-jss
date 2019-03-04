========
salt-jss
========

Configure your JAMF Pro server using SaltStack.


Pre-Requisites
--------------

The salt machine that is calling the API must have python-jss installed.

If you installed SaltStack via .pkg on macOS, then your SaltStack installation came with its own python.
You typically need to use pip, located at `/opt/salt/bin/pip` to install python modules for usage with SaltStack.

If you are developing with `python-jss` you can run `sudo /opt/salt/bin/python setup.py install` from the python-jss
git repository.

Configuration
-------------

Configuration can be retrieved from the minion executing these module(s)/state(s).

This is done by editing the file :file:`/etc/salt/minion`, which is YAML formatted, example::

	jss:
	  url: https://localhost:8444/
	  username: admin
	  password: p@ssw0rd
	  ssl_verify: False


Proxy Minion Configuration
--------------------------

:file:`/srv/pillar/top.sls`::

    base:
      jss1:
        - jss1

:file:`/srv/pillar/jss1.sls`::

    proxy:
      proxytype: jamf
      url: https://localhost:8444/
      username: admin
      password: p@ssw0rd
      ssl_verify: False

Then, run the proxy minion to control this instance as::

    $ salt-proxy --proxyid=jss1

.. note:: The proxy minion will load its config from ``/etc/salt/proxy`` and not ``/etc/salt/minion``.

Execution Modules
-----------------

- ``jamf.alerts``: List alerts
- ``jamf.cache_settings``: Read cache settings.
- ``jamf.mobile_devices``: List mobile devices.
- ``jamf.selfservice_settings``: Read self-service settings.
- ``jamf.accounts``: List JSS Accounts
- ``jamf.activation_code``: Read registered org and activation code.
- ``jamf.mobiledevice_commands``: List mobile device commands.

Troubleshooting
---------------

If you receive the error:

	Proxymodule jamf_proxy is missing an init() or a shutdown() or both. Check your proxymodule.  Salt-proxy aborted.

It may be due to the fact that salt-jss cannot be located by your minion OR proxy minion. Check either ``/etc/salt/minion``
or ``/etc/salt/proxy`` to make sure that salt-jss is accessible in your file_roots.

TODO
----

- SSO Settings
- APNS certs (requires scraping)
- VPP Accounts

Proxy State Checklist
---------------------

- Make sure you import `salt.utils.platform` so that you can detect whether the minion is a proxy with `salt.utils.platform.is_proxy()`.
- Always source configuration from `__pillar__['proxy']` instead of salt.config.
