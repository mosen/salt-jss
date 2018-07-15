#'All Managed Clients':
#  jamf.smart_computer_group:
#    site: -
#    criteria:
#      - name: Operating System
#        priority: 0
#        and_or: and
#        search_type: not like
#        value: server
#        opening_paren: false
#        closing_paren: false
#      - name: Application Title
#        priority: 1
#        and_or: and
#        search_type: is not
#        value: Server.app
#        opening_paren: false
#        closing_paren: false


AppCode Not Installed:
  jamf.smart_computer_group:
    - criteria:
      - Application Title:
          is: AppCode.app
      - Application Version:
          is_not: 2017.1.2

