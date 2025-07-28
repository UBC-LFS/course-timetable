'''
TODO: Go over and document/edit the code to cater toward Timetable authentication

'''

from django.conf import settings
from ldap3 import ALL_ATTRIBUTES, SUBTREE, Server, Connection
from ldap3.core.exceptions import LDAPBindError
import json


def authenticate(username, password) -> bool:
    '''------------AUTHENTICATION SECTION---------------------------'''

  
    server = Server(settings.CHECKOUT_INVENTORY_LDAP_URI) # Get LDAP server URI from environment variable

    try:
        # Create a connection to the LDAP server
        auth_conn = Connection(
            server,
            user = "uid={},{}".format(username, settings.CHECKOUT_INVENTORY_LDAP_MEMBER_DN),
            password = password,
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
            user = settings.CHECKOUT_INVENTORY_LDAP_AUTH_DN,
            password = settings.CHECKOUT_INVENTORY_LDAP_AUTH_PASSWORD,
            authentication = 'SIMPLE',
            check_names = True,
            client_strategy = 'SYNC',
            auto_bind = True,
            raise_exceptions = False
        )

        # Attempt to bind (authenticate) with the provided credentials
        conn.bind()

        conn.search(
            search_base = "uid={0},{1}".format(username, settings.CHECKOUT_INVENTORY_LDAP_MEMBER_DN),
            search_filter = settings.CHECKOUT_INVENTORY_LDAP_SEARCH_FILTER,
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