Example Computer EA:
  jamf.computer_ea:
    - description: Example Saltstack EA
    - data_type: String
    - input_type: script
    - inventory_display: Extension Attributes
    - contents: |
        #!/bin/bash
        echo "<result>value</result>"
        exit 0

