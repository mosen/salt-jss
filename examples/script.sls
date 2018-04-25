name_or_unique_id:
  jamf.script:
    - name: Script Name
    - category: Category Name
    - filename: filename.sh
    - info: Script information
    - notes: Script notes
#    - priority: before | after | reboot
#    - parameters:
#      - p4
#      - p5
#      - p6
    - os_requirements: 10.13.x
#    - contents: |
#        inline content or
    - source: salt:///examples/script.sh
