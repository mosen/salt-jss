#Scripts:
#  jamf.category:
#    - priority: 9


example_script_1:
  jamf.script:
    - name: Script2
    - category: Scripts
    - filename: filename.sh
    - info: More information
    - notes: More notes
    - priority: Before
    - os_requirements: 10.13.x,10.12.x,10.11.x
#    - contents: |
#        #!/bin/bash
#        echo "Inline script content."
    - source: salt://files/script.sh
    - parameters:
      - parameter4
      - parameter5
      - parameter6
      - parameter7
      - parameter8
      - parameter9
      - parameter10
      - parameter11

#example_script_2:
#  jamf.script:
#    - name: Example 2
##    - category: Category Name
#    - filename: script2.sh
#    - info: Script information
#    - notes: Script notes
#    - contents: |
#        #!/bin/bash
#        echo "Inline Content"
#    - parameters:
#      - a
#      - b
#      - c