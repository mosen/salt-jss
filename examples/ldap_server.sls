{% set organization = 'organizationguid' %}

JumpCloud:
  jamf.ldap_server:
    - hostname: ldap.jumpcloud.com
    - server_type: Custom
    - port: 636
    - use_ssl: true
    - authentication_type: simple
    - distinguished_username: uid=ldap,ou=Users,o={{ organization }},dc=jumpcloud,dc=com
    - password: P@ssw0rd
    - use_wildcards: true
    - user_mappings:
        - object_classes:
            - inetOrgPerson
        - search_base: ou=Users,o={{ organization }},dc=jumpcloud,dc=com
        - search_scope: All Subtrees
        - map:
            - user_id: uid
            - username: uid
            - realname: cn
            - email_address: mail
            - department: ~
            - building: ~
            - room: ~
            - telephone: ~
            - position: ~
            - user_uuid: uidNumber
    - group_mappings:
        - object_classes:
            - groupOfNames
        - search_base: ou=Users,o={{ organization }},dc=jumpcloud,dc=com
        - search_scope: All Subtrees
        - map:
            - group_id: gidNumber
            - group_name: cn
            - group_uuid: entryUUID
    - membership_mappings:
        - stored_in: group  # "group" or "user"
        - use_dn: true
        - membership_field: member

