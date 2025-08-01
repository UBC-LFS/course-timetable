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
    try:
        server = Server(settings.LDAP_URI)  # Get LDAP server URI from environment variable
    except:
        raise ValueError("LDAP_URI environment variable is not set or invalid.")
    
    try:
        
        # Create a connection to the LDAP server
        auth_conn = Connection(
            server,
            user="uid={},{}".format(username, os.getenv('LDAP_USER_SEARCH_BASE')),
            password=password,
            authentication = 'SIMPLE',
            check_names = True,
            client_strategy = 'SYNC',
            auto_bind = True,
            raise_exceptions = False
        )

        # Attempt to bind (authenticate) with the provided credentials
        is_valid = auth_conn.bind()
        
        # If not a valid authentication, return False
        if not is_valid:
            return False #authentication failed

        '''----------AUTHORIZATION SECTION-----------------'''
        conn = Connection(
            server,
            user = os.getenv('LDAP_DEFAULT_BIND_DN'),
            password = os.getenv('LDAP_PASSWORD'),
            authentication = 'SIMPLE',
            check_names = True,
            client_strategy = 'SYNC',
            auto_bind = True,
            raise_exceptions = False
        )

        # Attempt to bind (authorization) with the provided credentials
        conn.bind()

        conn.search(
            search_base = os.getenv('LDAP_GROUP_SEARCH_BASE'),
            search_filter = os.getenv('LDAP_MEMBER_FILTER'),
            search_scope = SUBTREE,
            attributes = ALL_ATTRIBUTES
        )

        entries = json.loads(conn.response_to_json())['entries']

        # If not a valid authorization, return False
        if len(entries) == 0:
            return False #authorization failed

        return True

    except LDAPBindError:
        return False