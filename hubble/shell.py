#   Copyright 2012 Derrick J. Wippler
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

from subprocess import check_output, CalledProcessError, Popen
from ConfigParser import NoSectionError, NoOptionError
import ConfigParser
import collections
import argparse
import textwrap
import logging
import sys
import re
import os


log = logging.getLogger(__name__)



class FileFormat(argparse._HelpAction):
    def __call__(self, parser, *args, **kwargs):
        print textwrap.dedent("""\
            [hubble]
            # Variables that are defined for all sections
            OS_AUTH_URL=https://identity.api.rackspacecloud.com
            CINDER_VOLUME_SERVICE_NAME=cloudBlockStorage
            OS_SERVICE_NAME=cloudserversOpenStack
            CINDERCLIENT_INSECURE=1
            OS_VERSION=2.0
            OS_NO_CACHE=1

            # Specify the command to run for all
            # sections, unless redefined in a section
            cmd=nova

            # The output from this command gets sourced
            # into the environment
            env-cmd=echo 'SOME_SCRIPT_DEFINED_VAR=1'

            # Same as the 'env-cmd' but only when the
            # -o option is used
            opt-cmd=rax-auth ${OS_AUTH_URL} ${opt.options}

            [us-cinder]
            OS_USERNAME=username
            OS_PASSWORD=password
            OS_TENANT_NAME=000001
            # Run 'cinder' for both 'dfw' and 'ord'
            meta=['dfw', 'ord']
            # The command to run for this section
            cmd=cinder

            [lon-cinder]
            OS_AUTH_URL=https://lon.identity.api.rackspacecloud.com
            OS_USERNAME=username
            OS_PASSWORD=password
            OS_TENANT_NAME=000001
            OS_REGION_NAME=LON
            cmd=cinder

            [dfw]
            OS_REGION_NAME=DFW

            [ord]
            OS_REGION_NAME=ORD

            [us-nova]
            OS_USERNAME=username
            OS_PASSWORD=password
            OS_TENANT_NAME=000001
            meta=['dfw', 'ord']
            cmd=nova

            [dfw-nova]
            OS_AUTH_SYSTEM=rackspace
            OS_REGION_NAME=DFW
            OS_USERNAME=username
            OS_PASSWORD=56fbd016277f11e2b9511bcea8800b42
            OS_TENANT_NAME=000001
            cmd=nova

            [dfw-cinder]
            CINDER_RAX_AUTH=1
            OS_REGION_NAME=DFW
            OS_USERNAME=username
            OS_PASSWORD=56fbd016277f11e2b9511bcea8800b42
            OS_TENANT_NAME=000001
            cmd=cinder
        """)
        parser.exit()


class Env(dict):
    """ A dict() collection of Pair() objects """

    class Pair():
        """
        Pair object that knows if the key=value should be
        exported to the environment or not
        """
        def __init__(self, value='', export=''):
            self.value = value
            self.export = export

        def __repr__(self):
            return "Pair('%s', %s)" % (self.value, self.export)

    def set(self, key, value, export=True):
        """ Sets the value with a Pair() """
        self[key] = self.Pair(value, export)

    def delete(self, key):
        """ A safe delete """
        try:
            del self[key]
        except KeyError:
            pass

    def add(self, envs):
        """ Adds or removes items in the dict 'envs' to the collection """
        for key, value in envs.iteritems():
            # if the value is empty
            if empty(value):
                # Delete the key from the env 
                self.delete(key)
            # else add it
            self.set(key, value, key.isupper())

    def eval(self):
        """ Exapand all the ${variable} signatures in the collection """
        for key, item in self.iteritems():
            self[key].value = self.expandVar(item.value)
        return self

    def expandVar(self, value):
        """ Find a ${some_var} signature and expand it """
        result = value
        # Find all the ${...}
        for match in re.finditer("\$\{\S+\}", value):
            try:
                # Extract the variable name from ${...}
                var = match.group(0)
                key = var[2:-1]
                # Replace the entire ${...} sequence with the value named
                result = str.replace(result, var, self.get(key).value)
            except AttributeError:
                raise RuntimeError("no such environment variable "
                                   "'%s' in '%s'" % (key, result))
        return result

    def toDict(self):
        """
        Convert the entire collection of Pair() objects to a
        dict({'key': str()}) only where export == True
        """
        return dict([(key, value.value) for key, value in self.iteritems() if value.export])

    def __repr__(self):
        """ Pretty print the collection """
        # Calculate the max length of any key, and indent by that amount
        fmt = "%{0}s: %s".format(len(max(self.keys(), key=len)))
        return '\n'.join([fmt % (key, value.value) for key, value in self.iteritems()])


def empty(value):
    """ Return true if 'value' only has spaces or is empty """
    return re.match('^(|\s*)$', value) is not None


def green(msg):
    """ ASCII encode the string with green """
    return "\033[92m%s\033[0m" % msg


def openFd(file):
    """ Open the file if possible, else return None """
    try:
        return open(file)
    except IOError:
        return None


def readConfigs(files=None):
    """ Given a list of file names, return a list of handles to succesfully opened files"""
    files = files or [os.path.expanduser('~/.hubblerc'), '.hubblerc']
    # If non of these files exist, raise an error
    if not any([os.path.exists(rc) for rc in files]):
        raise RuntimeError("Unable to find config files in these locations [%s] "
            "(See --help for file format)" % ",".join(files))
    return parseFiles([openFd(file) for file in files])


def parseFiles(fds):
    """ Given a list of file handles, parse all the files with ConfigParser() """
    # Read the config file
    config = ConfigParser.RawConfigParser()
    # Don't transform (lowercase) the key values
    config.optionxform = str
    # Read all the file handles passed
    for fd in fds:
        if fd is None:
            continue
        config.readfp(fd)
    return config


def getEnvironments(args, config):
    """ Get the environment collection requested from args.env """
    sections = [args.env]
    results = []

    # Get the default variables
    conf = dict(config.items('hubble'))
    # Merge in the requested section
    conf.update(dict(config.items(args.env)))
    # If requested section is a meta section
    if 'meta' in conf:
        # Evaluate the list of sections this is a meta for
        sections = eval(conf['meta'])

    for section in sections:
        env = Env()
        # Add the name of the section
        env.add({'section': section})
        # Add the choosen section
        env.add(conf)
        # Add the env section
        env.add(dict(config.items(section)))
        # Add the args to the environment as opt.'<arg_name>'
        env.add(dict(map(lambda i: ("opt.%s" % i[0], str(i[1])), vars(args).items())))
        # Apply var expansion
        results.append(env.eval())
    return results


def toDict(string):
    """ Parse a string of 'key=value' into a dict({'key': 'value'}) """
    return dict([[i.strip() for i in line.split('=', 1)]
            for line in string.rstrip().split('\n')])


def run(cmd):
    """ Parse the output from the command passed into a dict({'key': 'value'}) """
    # don't attempt to run an empty command
    if empty(cmd):
        return {}
    return toDict(check_output(cmd, shell=True))


def cmdPath(cmd, conf):
    """ Find the 'cmd' in the config, or default to /usr/bin/'cmd' """
    basename = os.path.basename(cmd)
    try:
        return conf.get('hubble-commands', basename)
    except NoSectionError:
        log.warning("Missing [hubble-commands] section in config")
    except NoOptionError:
        log.debug("'%s' not found in [hubble-commands] section" % basename)
        return "/usr/bin/%s" % basename


def main():
    logging.basicConfig(format='-- %(message)s')
    log.setLevel(logging.CRITICAL)
    parser = argparse.ArgumentParser(add_help=False,
         formatter_class=argparse.RawDescriptionHelpFormatter,
         description = textwrap.dedent("""\
            An environment manager for openstack. Can be used with 'novaclient'
            and 'cinderclient'

            Use ~/.hubblerc for user wide environments then place a
            .hubblerc in a local directory to overide ~/.hubblerc
            """))

    parser.add_argument('env', nargs='?', metavar='<ENV>',
            help="The section in ~/.hubblerc to use")
    parser.add_argument('-o', '--options',
            help="Optional argument to be passed to the 'opt-cmd'")
    parser.add_argument('--file-format', action=FileFormat,
            help="Show an example ~/.hubblerc")
    parser.add_argument('-h', '--help', action='store_true',
            help="show this help message and exit")
    parser.add_argument('-d', '--debug', action='store_true',
            help="Adds CINDERCLIENT_DEBUG=1 to the environment and passes"
            " --debug to selected command")
    hubble_args, other_args = parser.parse_known_args()

    # Do this so we pass along the -h to cinder or nova if we are impersonating
    if hubble_args.help and (hubble_args.env is None):
        return parser.print_help()
    if hubble_args.env is None:
        print "Environments Configured: %s" % ",".join(readConfigs().sections())
        print "See --help for usage"
        return 1
    if hubble_args.help:
        other_args.append('--help')

    # Set our log level
    if hubble_args.debug:
        log.setLevel(logging.DEBUG)

    try:
        conf = readConfigs()
        # Read environment values from config files
        environments = getEnvironments(hubble_args, conf)
        for env in environments:
            # Populate environment vars by running opt-cmd
            # if -o was passed on the commandline
            if hubble_args.options:
                if 'opt-cmd' not in env:
                    raise RuntimeError("provided --options, but 'opt-cmd' is not defined in"
                            " '%s' section" % env['section'].value)
                env.add(run(env['opt-cmd'].value))

            # Populate environment vars by running the env-cmd if it exists
            if 'env-cmd' in env:
                env.add(run(env['env-cmd'].value))

            # If querying multiple environments, display the env name
            if len(environments) != 1 or hubble_args.debug:
                print "-- [%s] --" % green(env['section'].value)

            # If our invocation name is not 'hubble'
            if not sys.argv[0].endswith('hubble'):
                # Use the invocation name as our 'cmd'
                env.add({'cmd': cmdPath(sys.argv[0], conf)})

            # At this point we should know our 'cmd' to run
            if 'cmd' not in env:
                raise RuntimeError("Please specify a 'cmd' somewhere in your config")

            # FIXME: when using rackspace auth cinder doesn't know how to discover
            # the /v2.0 version endpoint. So we must specify v2.0 here
            env['OS_AUTH_URL'].value = env['OS_AUTH_URL'].value + "/v2.0"

            # If --debug; print out our env config and pass along the --debug arg
            if hubble_args.debug:
                print "%r\n" % env
                env.add({'CINDERCLIENT_DEBUG': '1'})
                other_args.insert(0, '--debug')

            # Grab a copy of the local environment and inject it into our environment
            environ = os.environ.copy()
            environ.update(env.toDict())

            try:
                # Run the requested command
                p = Popen([env['cmd'].value] + other_args,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    env=environ)
                # Wait for the command to complete
                p.wait()

            except OSError, e:
                raise RuntimeError("exec failed '%s' - %s" % (env['cmd'].value, e))
            print "\n",

    except (RuntimeError, CalledProcessError, NoSectionError), e:
        log.critical(e)
        return 1
