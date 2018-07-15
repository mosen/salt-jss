computer_extension_attribute1:
  jamf.computer_extension_attribute:
    - name: Display Name
    - description: Description
    - data_type: String
    - inventory_display: General
    - input_type: Script
    - script: |
        #!/bin/bash
        echo "do something"
