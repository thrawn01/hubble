#   Copyright 2014 Derrick J. Wippler
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
#   The following code was borrowed heavily from supernova-keyring
#   (https://github.com/major/supernova) under the same license

from argparse import ArgumentParser, RawDescriptionHelpFormatter
import keyring
import getpass


def main():
    description = """
        hubble-keyring - is a companion to hubble that allows
        users to store and retrieve sensitive keys and passwords
        from the local keyring. Works with osx-keychain, gnome-keyring
        and kwallet

        Set the OS_PASSWORD for [chicago] section of .hubblerc
        hubble-keyring --set chicago OS_PASSWORD

        Set the OS_PASSWORD for USE_KEYRING['my-global-password']
        hubble-keyring --set global my-global-password
    """
    parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter,
                            description=description)
    parser.add_argument('-g', '--get', action='store_true', dest='get_pass',
                        help='retrieves credentials'' from keychain storage')
    parser.add_argument('-s', '--set', action='store_true', dest='set_pass',
                        help='stores credentials in keychain storage')
    parser.add_argument('env', help='environment to set the variable in')
    parser.add_argument('variable', help='variable name to put in keyring')
    args = parser.parse_args()

    try:
        if args.set_pass:
            #print "-- Preparing to set a password in the keyring for:"
            #print "  - Environment  : %s" % args.env
            #print "  - Variable     : %s" % args.variable
            #print "\n  If this is correct, enter the corresponding credential"\
                #" to store in \n  your keyring or press CTRL-D to abort: ",

            # Prompt for a password and catch a CTRL-D
            try:
                password = getpass.getpass('Enter Credential (CTRL-D to abort) > ')
            except:
                password = None
                print

            # Did we get a password from the prompt?
            if not password or len(password) < 1:
                print "\n-- No data was altered in your keyring."
                return 1

            set_password(args.env, args.variable, password)
            print "\n-- Successfully stored credentials for '%s' under the " \
                "hubble service." % args.variable
            return 0

        if args.get_pass:
            print get_password(args.env, args.variable)
            return 0

        print "-- Please specify --get or --set on the command line"
        return 1
    except RuntimeError, e:
        print "-- %s" % str(e)
        return 1


def get_password(env, variable):
    try:
        return keyring.get_password('hubble', '%s:%s' % (env, variable))
    except keyring.backend.PasswordSetError, e:
        raise RuntimeError("Unable to retrieve credentials for %s:%s"
                           " (try --set)\n-- %s " % (env, variable, str(e)))


def set_password(env, variable, password):
    # Try to store the password
    try:
        return keyring.set_password('hubble', '%s:%s' % (env, variable),
                                    password)
    except keyring.backend.PasswordSetError, e:
        raise RuntimeError("Unable to store credentials for '%s:%s' under "
                           "the hubble service - %s" %
                           (env, variable, str(e)))
