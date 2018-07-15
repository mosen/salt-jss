# All objects go into the testing category
testing:
  jamf.category:
    - priority: 9

# Example 1: Fill every single parameter, and use a source file from the salt master.
example_script_1:
  jamf.script:
    - name: All Parameters Script
    - category: testing
#    - filename: filename.sh
    - info: More information
    - notes: Created by salt-jss
    - priority: Before
    # - priority: After
    - os_requirements: 10.13.x,10.12.x,10.11.x
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
    - require:
      - jamf: testing


# Example 2: Use the `content` property to supply an inline script.
example_script_2:
  jamf.script:
    - name: Content Script
    - category: testing
    - filename: script2.sh
    - info: Script information
    - notes: Script notes
    - contents: |
        #!/bin/bash
        echo "Inline Content"
    - require:
      - jamf: testing


# Example 3: Use a jinja template as the script.
example_script_3:
  jamf.script:
    - name: Jinja Script
    - category: testing
    - notes: This script tests the availability of the jinja templating engine.
    - source: salt://templates/script.sh
    - template: jinja
    - require:
      - jamf: testing
