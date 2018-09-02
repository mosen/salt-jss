Testing:
  jamf.category:
    - priority: 9


Testing Smart Group:
  jamf.smart_computer_group:
    - name: Testing
    - criteria:
      - Application Title:
          is: AppCode.app
      - Application Version:
          is_not: 2017.1.2

Test Policy:
  jamf.policy:
    - frequency: Ongoing
    - enabled: True
    - category: Testing
    - triggers:
#        - checkin
        - testing
    - scope:
        - all_computers: True
#      - computer_groups:
#          - Testing
    - packages:
        - install:
            - VLC-2.2.8.pkg
#        - distribution_point: Cloud distribution point
    - scripts:
#        - before:
        - after:
            - All Parameters Script: ["parameter4", "parameter5"]

    - maintenance:
        - update_inventory: False
        - reset_names: False
        - install_cached: False
