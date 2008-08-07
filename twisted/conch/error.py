# Copyright (c) 2001-2008 Twisted Matrix Laboratories.
# See LICENSE for details.

"""
An error to represent bad things happening in Conch.

Maintainer: Paul Swartz
"""


class ConchError(Exception):
    def __init__(self, value, data = None):
        Exception.__init__(self, value, data)
        self.value = value
        self.data = data



class NotEnoughAuthentication(Exception):
    """
    This is thrown if the authentication is valid, but is not enough to
    successfully verify the user.  i.e. don't retry this type of
    authentication, try another one.
    """



class ValidPublicKey(Exception):
    """
    This is thrown during the authentication process if the public key is valid
    for the user.
    """



class IgnoreAuthentication(Exception):
    """
    This is thrown to let the UserAuthServer know it doesn't need to handle the
    authentication anymore.
    """



class MissingKeyStoreError(Exception):
    """
    Raised if an SSHAgentServer starts receiving data without its factory
    providing a keys dict on which to read/write key data.
    """
