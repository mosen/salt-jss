Scripts:
  jamf.category:
    - priority: 9


example_script_1:
  jamf.script:
    - name: Script Name
    - category: Scripts
    - filename: filename.sh
    - info: Script information
    - notes: Script notes
#    - priority: before | after | reboot
    - os_requirements: 10.13.x
#    - contents: |
#        inline content or
    - source: salt://files/script.sh

example_script_2:
  jamf.script:
    - name: Example 2
#    - category: Category Name
    - filename: script2.sh
    - info: Script information
    - notes: Script notes
    - contents: |
        #!/bin/bash
        echo "Inline Content"
    - parameters:
      - a
      - b
      - c