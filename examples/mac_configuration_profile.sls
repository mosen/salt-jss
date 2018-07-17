Config Profile Test:
  jamf.mac_configuration_profile:
    - description: A configuration profilez
    - source: salt://configuration_profiles/example.mobileconfig
    - category: Testing
    - distribution_method: Install Automatically
    - user_removable: False
    - level: computer
    - scope:
      - all_computers: False
#      - computer:
#          name: Blah
#          udid: 55900BDC-347C-58B1-D249-F32244B11D30
#      - computer:
#          name: Johns iMac
#          udid: 55900BDC-347C-58B1-D249-F32244B11D30
      - computer_group: test
#      - building: Building A
#      - department: Dept B
#    - limitations:
#      - user: Someone
#      - user_group: Blah
#      - network_segment: LAN
#      - ibeacon: Name
#    - self_service:
#      - button: Install
#      - description: Install a config profile
#      -