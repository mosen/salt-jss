Config Profile Test:
  jamf.mac_configuration_profile:
    - description: A configuration profile
    - source: salt://configuration_profiles/example.mobileconfig
    # - site: Name
    - category: Testing
    - self_service: False  # Distribution Method
    - user_removable: True
    - level: Computer
#    - targets:
#      - computer: asd
#      - computer_group: asd
#      - building: asd
#      - department: asd
#    - limitations:
#      - segment: lan
#    - exclusions: