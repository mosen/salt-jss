salt:
  jamf.account:
    - directory_user: False
    - full_name: SaltStack Admin
    - email: salt@localhost
    - enabled: True
#    - ldap_server:
#    - force_password_change:
    - access_level: Full Access
    - privilege_set: Administrator
