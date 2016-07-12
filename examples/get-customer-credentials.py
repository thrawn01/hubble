#! /usr/bin/env python

# -----------------------------------------------------------------------------
# This is an example of what a impersonate script might look like for use with
# opt-cmd in hubblerc.
# -----------------------------------------------------------------------------

# flake8: noqa

from __future__ import print_function

from argparse import ArgumentParser
import super
import sys
import os
import re


def empty(value):
    """ Return true if 'value' only has spaces or is empty """
    return value is None or re.match('^(|\s*)$', value) is not None


def main(argv):
    (adminUser, adminPass) = (None, None)
    p = ArgumentParser(prog='get-customer-credentials.py',
                       description="Fetches customer credentials using"
                       " admin credentials passed via environment variables"
                       " OS_USERNAME and OS_PASSWORD")
    p.add_argument('ddi', metavar='<ddi>',
                   help="DDI of the customer you want to impersonate")
    opts = p.parse_args(argv)

    try:
        # Hubble passes all the defined section variables to us in our
        # environment, so these could be any variable defined in hubblerc
        adminUser = os.environ['OS_USERNAME']
        adminPass = os.environ['OS_PASSWORD']
    except KeyError:
        pass

    if empty(adminUser) or empty(adminPass):
        print("-- OS_USERNAME or OS_PASSWORD not supplied in environment",
              file=sys.stderr)
        return 1

    # ----------------------------------------------------
    # Do something here to get the customers credentials
    # ----------------------------------------------------
    creds = super.sekrit.getCreds(adminUser, adminPass, opts.ddi)

    print("OS_USERNAME=%s" % creds['username'])
    print("OS_PASSWORD=%s" % creds['password'])
    print("OS_TENANT_NAME=%s" % creds['tenant-id'])

    # You can also inject extra environment variables
    print("OS_AUTH_SYSTEM=special-auth-system")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
