'''
TODO: Go over and document/edit the code to cater toward Timetable authentication
'''

from django.conf import settings
from ldap3 import ALL_ATTRIBUTES, SUBTREE, Server, Connection
from ldap3.core.exceptions import LDAPBindError
import json
import os


def authenticate(username, password) -> bool:
    '''------------AUTHENTICATION SECTION---------------------------'''
    server = Server(settings.LDAP_URI)  # Get LDAP server URI from environment variable
    
    # print("uid={},{}".format(username, settings.LDAP_MEMBER_DN))
    
    print(f"server {server}")
    try:
        
        # Create a connection to the LDAP server
        auth_conn = Connection(
            server,
            user="uid={},{}".format(username, settings.LDAP_MEMBER_DN),
            password=password,
            authentication = 'SIMPLE',
            check_names = True,
            client_strategy = 'SYNC',
            auto_bind = True,
            raise_exceptions = False
        )

        # print(f"auth_conn: {auth_conn}")

        # Attempt to bind (authenticate) with the provided credentials
        is_valid = auth_conn.bind()
        # print(f"is_valid: {is_valid}")
        # If not a valid authentication, return False
        if not is_valid:
            return False #authentication failed

        '''----------AUTHORIZATION SECTION-----------------'''
        conn = Connection(
            server,
            user = settings.LDAP_AUTH_DN,
            password = settings.LDAP_AUTH_PASSWORD,
            authentication = 'SIMPLE',
            check_names = True,
            client_strategy = 'SYNC',
            auto_bind = True,
            raise_exceptions = False
        )
        # print(f"conn: {conn}")

        # Attempt to bind (authorization) with the provided credentials
        conn.bind() # Boolean 
        
        # print(f"conn.bind(): {conn.bind()}")

        conn.search(
            search_base =  "uid={0},{1}".format(username, settings.LDAP_MEMBER_DN),
            search_filter = settings.LDAP_SEARCH_FILTER,
            # search_filter = settings.LDAP_SEARCH_FILTER,
            search_scope = SUBTREE,
            attributes = ALL_ATTRIBUTES
        )
        
        # print(f"conn.response: {conn.response_to_json()}")

        entries = json.loads(conn.response_to_json())['entries']

        # If not a valid authorization, return False
        # print(f"entries: {entries}")
        if len(entries) == 0:
            return False #authorization failed

        return True

    except LDAPBindError:
        print("LDAP authentication failed.")
        return False