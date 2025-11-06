import os
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from django.conf import settings

from ldap3 import ALL_ATTRIBUTES, SUBTREE, Server, Connection
from ldap3.core.exceptions import LDAPBindError


def is_ldap_user(cwl, password):
    '''------------------AUTHENTICATION SECTION------------------------------------'''
    if settings.BYPASS_LDAP:
        return True

    ldap_server = Server(os.environ['CHECKOUT_INVENTORY_LDAP_URI']) # Get LDAP server URI from environment variable

    # Distinguished Name (DN) for bind (authenticate) using the CWL
    bind_dn = "uid={},{}".format(
        cwl, os.environ['CHECKOUT_INVENTORY_LDAP_MEMBER_DN'])
    try:
        # Authentication step using the CWL and password
        # Create a connection to the LDAP server
        cwl_conn = Connection(
            ldap_server,
            user=bind_dn,
            password=password,
            authentication='SIMPLE',
            check_names=True,
            client_strategy='SYNC',
            auto_bind=True,
            raise_exceptions=False)

        # Attempt to bind (authenticate) with the provided credentials
        valid_cwl = cwl_conn.bind()

        # If not a valid authentication, return False
        if not valid_cwl:
            return False
        
        '''----------------AUTHORIZATION SECTION---------------------------------'''

        # If authentication is successful, begin to authorize the user
        lfs_conn = Connection(
            ldap_server,
            user=os.environ['CHECKOUT_INVENTORY_LLDAP_AUTH_DN'],
            password=os.environ['CHECKOUT_INVENTORY_LDAP_AUTH_PASSWORD'],
            authentication='SIMPLE',
            check_names=True,
            client_strategy='SYNC',
            auto_bind=True,
            raise_exceptions=False)
        
        # Attempt to bind (authenticate) with the provided credentials
        lfs_conn.bind()

        # This is for authorization, checking if the user is in the staff group
        search_base = "uid={},{}".format(
            cwl, os.environ['CHECKOUT_INVENTORY_LDAP_MEMBER_DN'])
        lfs_conn.search(
            search_base=search_base,
            search_filter=os.environ['CHECKOUT_INVENTORY_LDAP_SEARCH_FILTER'],
            search_scope=SUBTREE,
            attributes=ALL_ATTRIBUTES
        )

        is_inventory_staff = len(lfs_conn.entries) > 0 # TODO 

        return is_inventory_staff
    except LDAPBindError:
        return False
