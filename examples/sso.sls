SAML Provider Name:
  jamf.sso_settings:
    - idp_url: ~
#    - metadata_filename: idp_metadata.xml
#    - metadata: abcd
#    - metadata_source: FILE
    - entity_id: https://someone.jamfcloud.com/saml/sso
    - user_mapping: EMAIL
    - user_attribute_name: ~
    - group_attribute_name: http://schemas.xmlsoap.org/claims/memberOf
    - group_rdn_key: CN
#    - group_enrollment_access_name: ~
    - use_for:
        - enrollment
        - jss
        - self_service
#    - session_timeout: 480
    - group_enrollment_access_enabled: False
    - token_expiration_disabled: False
    - allow_bypass: True
