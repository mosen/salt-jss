========
salt-jss
========

Configure your JAMF Pro server using SaltStack.


Configuration
-------------

Configuration can be retrieved from the minion executing these module(s)/state(s).

This is done by editing the file :file:`/etc/salt/minion`, which is YAML formatted, example::

	jss:
	  url: https://localhost:8444/
	  username: admin
	  password: p@ssw0rd
	  ssl_verify: False
