Energy Saver Policy:
  jamf.mac_configuration_profile:
    - source: salt://configuration_profiles/energysaver.mobileconfig
    - sign_with: 'Certificate Name'
    - level: Computer
    - category: testing
    - description: asdadf
    - self_service: False
    - targets:
      - computer: asd
      - computer_group: asd
      - building: asd
      - department: asd
    - limitations:
      - segment: lan
    - exclusions: