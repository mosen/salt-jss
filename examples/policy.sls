policy_unique_name:
  jamf.policy:
    - name: Policy Name
    - enabled: True
    - category: Category Name
    - self_service: False
    - triggers:
      - startup
      - login
      - logout
      - network_state_changed
      - enrollment_complete
      - checkin
      - custom: event_name
    - frequency: once_per_computer | once_per_user etc.
    - target_drive: /
    - restart:
      - logged_in: no | if_required | immediate
      - not_logged_in: no | if_required | immediate
    - maintenance:
      - inventory
      - computer_name
      - install_cached
      - disk_permissions
      - fix_byhost
      - system_caches
      - user_caches
      - verify_startup

    # Package Section
    - packages:
      - name (should auto require jamf.package with this name)


    - software_updates:


    - scripts:


    - printers:


    - disk_encryption:

    - dock_items:

    - local_accounts:

    - management_account:

    - directory_bindings:

    - efi_password:

    -