
'''
TODO: Go over and document/edit the code to cater toward Timetable authentication

'''

# from django.conf import settings
# from ldap3 import ALL_ATTRIBUTES, SUBTREE, Server, Connection
# from ldap3.core.exceptions import LDAPBindError
# import json


# def authenticate(username, password):
#     server = Server(settings.CHECKOUT_INVENTORY_LDAP_URI)

#     try:
#         auth_conn = Connection(
#             server,
#             user = "uid={},{}".format(username, settings.CHECKOUT_INVENTORY_LDAP_MEMBER_DN),
#             password = password,
#             authentication = 'SIMPLE',
#             check_names = True,
#             client_strategy = 'SYNC',
#             auto_bind = True,
#             raise_exceptions = False
#         )

#         is_valid = auth_conn.bind()
#         if not is_valid:
#             return False

#         conn = Connection(
#             server,
#             user = settings.CHECKOUT_INVENTORY_LDAP_AUTH_DN,
#             password = settings.CHECKOUT_INVENTORY_LDAP_AUTH_PASSWORD,
#             authentication = 'SIMPLE',
#             check_names = True,
#             client_strategy = 'SYNC',
#             auto_bind = True,
#             raise_exceptions = False
#         )

#         conn.bind()

#         conn.search(
#             search_base = "uid={0},{1}".format(username, settings.CHECKOUT_INVENTORY_LDAP_MEMBER_DN),
#             search_filter = settings.CHECKOUT_INVENTORY_LDAP_SEARCH_FILTER,
#             search_scope = SUBTREE,
#             attributes = ALL_ATTRIBUTES
#         )

#         entries = json.loads(conn.response_to_json())['entries']

#         if len(entries) == 0:
#             return False

#         return True

#     except LDAPBindError:
#         return False