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
