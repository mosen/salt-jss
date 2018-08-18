Enrollment Settings:
  jamf.enrollment_settings:
    - skip_certificate_install: False  # Always true for jamfcloud customers.
    - management_username: jamf
    - management_password: password
    # or
    # - random_password_length: 12
    - create_management_account: False
    - enable_ssh: False
    - launch_self_service: False
    - sign_quickadd: False
