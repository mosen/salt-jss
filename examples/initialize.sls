'System is initialized':
  jamf.system_init:
    - activation_code: ABCD
    - institution_name: Some Institution
    - is_eula_accepted: True
    - username: Admin
    - password: Password
    - email: admin@localhost
    - jss_url: https://localhost:8443
