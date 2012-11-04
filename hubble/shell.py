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
from ConfigParser import NoSectionError
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
            OS_AUTH_URL=https://identity.api.rackspacecloud.com
            CINDER_VOLUME_SERVICE_NAME=cloudBlockStorage
            OS_SERVICE_NAME=cloudserversOpenStack
            OS_AUTH_SYSTEM=rackspace
            CINDERCLIENT_INSECURE=1
            CINDER_RAX_AUTH=1
            OS_VERSION=2.0
            OS_NO_CACHE=1

            # == Variable expansion ==
            # Any variable defined in this file is available for expansion
            # with the format of ${var_name} including these hidden variables
            # 'options.user' - the --user option from the command line
            # 'options.user' - the <env> option from the command line
            # 'secton' - the name of the section the variable is being expanded in

            # Command to run by default
            cmd=cinder

            [prod]
            # Command to populate additional environment variables
            # Great for impersonating customers!
            env_cmd=get-customer-auth ${OS_AUTH_URL} ${options.user}
            # Run the 'cmd' once for each of these environments
            meta=['dfw', 'ord']

            [dfw]
            OS_REGION_NAME=DFW

            [ord]
            OS_REGION_NAME=ORD

            [lon]
            OS_AUTH_URL=https://lon.identity.api.rackspacecloud.com
            OS_REGION_NAME=LON

            [prod-nova]
            cmd=nova
            meta=['dfw', 'ord']

            [staging]
            USERNAME=myusername
            TENANT=73331
            APIKEY=a2a08609c073654e83cd4fa382e09a5a
            REGION=STAGING
        """)
        parser.exit()


class Env(dict):
    class Pair():
        def __init__(self, value='', export=''):
            self.value = value
            self.export = export

        def __repr__(self):
            return "Pair('%s', %s)" % (self.value, self.export)

    def set(self, key, value, export=True):
        self[key] = self.Pair(value, export)

    def add(self, envs):
        for key, value in envs.iteritems():
            self.set(key, value, key.isupper())

    def eval(self):
        for key, item in self.iteritems():
            self[key].value = self.expandVar(item.value)
        return self

    def expandVar(self, value):
        result = value
        for match in re.finditer("\$\{\S+\}", value):
            try:
                var = match.group(0)
                key = var[2:-1]
                result = str.replace(result, var, self.get(key).value)
            except AttributeError:
                raise RuntimeError("no such environment variable "
                                   "'%s' in '%s'" % (key, result))
        return result

    def toDict(self):
        return dict([(key, value.value) for key, value in self.iteritems()])

    def __repr__(self):
        # Calculate the max length of any key, and indent by that amount
        fmt = "%{0}s: %s".format(len(max(self.keys(), key=len)))
        return '\n'.join([fmt % (key, value.value) for key, value in self.iteritems()])

def green(msg):
    return "\033[92m%s\033[0m" % msg

def openFd(file):
    try:
        return open(file)
    except IOError:
        return None


def readConfigs(files=None):
    files = files or [os.path.expanduser('~/.hubblerc'), '.hubblerc']
    # If non of these files exist, raise an error
    if not any([os.path.exists(rc) for rc in files]):
        raise RuntimeError("Unable to find config files in these locations [%s] "
            "(See --help for file format)" % ",".join(files))
    return parseFiles([openFd(file) for file in files])


def parseFiles(fds):
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
        # Add the args to the environment as 'options.<arg_name>'
        env.add(dict(map(lambda i: ("options.%s" % i[0], str(i[1])), vars(args).items())))
        # Apply var expansion
        results.append(env.eval())
    return results


def toDict(string):
    return dict([[i.strip() for i in line.split('=', 1)]
            for line in string.rstrip().split('\n')])


def run(cmd):
    try:
        # don't attempt to run an empty command
        if re.match('^(|\s*)$', cmd):
            return []
        return toDict(check_output(cmd, shell=True))
    except CalledProcessError:
        return []


def main():
    logging.basicConfig(format='-- %(message)s')
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
    parser.add_argument('--file-format', action=FileFormat,
            help="Show an example ~/.hubblerc")
    parser.add_argument('-h', '--help', action='store_true',
            help="show this help message and exit")
    parser.add_argument('-d', '--debug', action='store_true',
            help="Adds CINDERCLIENT_DEBUG=1 to the environment and passes"
            " --debug to selected command")
    hubble_args, other_args = parser.parse_known_args()

    # Do this so we pass along the -h to cinder or nova if we are impersonating
    if hubble_args.help and len(other_args) == 0:
        return parser.print_help()
    if hubble_args.env == None:
        return parser.print_help()
    if hubble_args.help:
        other_args.append('--help')

    # TODO: allow invocation detection (ln -s /usr/bin/cinder /usr/bin/hubble)
    # TODO: Add a --list argument, like supernova

    try:
        # Read environment values from config files
        environments = getEnvironments(hubble_args, readConfigs())
        for env in environments:
            if len(environments) != 1 or hubble_args.debug:
                print "-- [%s] --" % green(env['section'].value)

            if hubble_args.debug:
                print "%r\n" % env

            # TODO: Only invocate if asked to? (my passing -u or make a config option?)
            # maybe call it optional_cmd, and have a always_cmd for always
            if 'env_cmd' in env:
                # run the auth command
                env.add(run(env['env_cmd'].value))

            if 'cmd' not in env:
                raise RuntimeError("Please specify a 'cmd' somewhere in your config")

            if hubble_args.debug:
                env.add({'CINDERCLIENT_DEBUG': '1'})
                other_args.insert(0, '--debug')

            # Grab a copy of the local environment and inject our environment
            environ = os.environ.copy()
            environ.update(env.toDict())
            # Run the requested command for each environment
            p = Popen([env['cmd'].value] + other_args,
                stdout=sys.stdout,
                stderr=sys.stderr,
                env=environ)
            p.wait()
            print "\n",

    except (CalledProcessError, NoSectionError), e:
        log.error("-- %s" % e)
        return 1
