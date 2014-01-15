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

try:
    # Not everyone needs keyring
    import keys
except ImportError:
    keys = None


log = logging.getLogger(__name__)


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

        def endswith(self, needle):
            return self.value.endswith(needle)

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

    def eval(self, section):
        """ Exapand all the ${variable} directives in the collection """
        for key, item in self.iteritems():
            self[key].value = self.expandVar(section, key, item.value)
        return self

    def expandVar(self, section, variable, value):
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
        # Expand keyring values if any
        return self.expandKeyringVar(section, variable, result)

    def expandKeyringVar(self, section, variable, value):
        """ Find 'USE_KEYRING' directives and expand them using the keyring """
        identifier = value.strip()
        if identifier.startswith("USE_KEYRING"):
            if keys is None:
                raise RuntimeError("found USE_KEYRING for '%s' but python "
                                   "keyring or getpass modules are not "
                                   "installed are required for keyring "
                                   "support" % variable)
            if identifier == "USE_KEYRING":
                return keys.get_password(section, variable)
            else:
                regex = "USE_KEYRING\[([\x27\x22])(.*)\\1\]"
                var = re.match(regex, value).group(2)
                return keys.get_password('global', variable)
        return value

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


class SafeConfigParser(ConfigParser.RawConfigParser):
    """ Simple subclass to add the safeGet() method """
    def getError(self):
        return None

    def safeGet(self, section, key):
        try:
            return ConfigParser.RawConfigParser.get(self, section, key)
        except (NoSectionError, NoOptionError):
            return None


class ErrorConfigParser(SafeConfigParser):
    """ Simple subclass to inform users of a parse error """
    def __init__(self, msg):
        SafeConfigParser.__init__(self)
        self.msg = msg

    def getError(self):
        return self.msg


def empty(value):
    """ Return true if 'value' only has spaces or is empty """
    return value is None or re.match('^(|\s*)$', value) is not None


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
        return ErrorConfigParser("Unable to find config files in these"
                                 " locations [%s]" % ", ".join(files))
    return parseConfigs([openFd(file) for file in files])


def parseConfigs(fds):
    """ Given a list of file handles, parse all the files with ConfigParser() """
    # Read the config file
    config = SafeConfigParser()
    # Don't transform (lowercase) the key values
    config.optionxform = str
    # Read all the file handles passed
    for fd in fds:
        if fd is None:
            continue
        config.readfp(fd)
    return config


def getEnvironments(args, choice, config):
    """ Get the environment collection requested from args.env """
    sections = [choice]
    results = []
    conf = {}

    try:
        # Get the default variables if exists
        conf = dict(config.items('hubble'))
    except NoSectionError:
        pass

    # Merge in the requested environment
    conf.update(dict(config.items(choice)))
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
        results.append(env.eval(section))
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


def evalArgs(conf, parser):
    env = conf.safeGet('hubble', 'default-env')
    # If no default environment set, look for an
    # environment choice on the command line
    if not env:
        parser.add_argument('env', nargs='?', metavar='<ENV>',
                help="The environment defined in ~/.hubblerc to use")
        (arg1, arg2) = parser.parse_known_args()
        return (arg1, arg2, arg1.env)
    # Return the args with the default environment choice
    (arg1, arg2) = parser.parse_known_args()
    return (arg1, arg2, env)


def main():
    logging.basicConfig(format='-- %(message)s')
    log.setLevel(logging.CRITICAL)
    parser = argparse.ArgumentParser(add_help=False,
         formatter_class=argparse.RawDescriptionHelpFormatter,
         description = textwrap.dedent("""\
            Hubble - An environment variable manager for tools like
            cinderclient, novaclient, swiftclient and swiftly that rely
            on environment variables for configuration.

            Use ~/.hubblerc for user wide environments then place a
            .hubblerc in a local directory to overide ~/.hubblerc
            """))
    parser.add_argument('-o', '--option',
            help="an argument to pass to the opt-cmd")
    parser.add_argument('-e', '--execute', metavar='COMMAND',
            help="execute a command in the specified environment")
    parser.add_argument('-h', '--help', action='store_true',
            help="show this help message and exit")
    parser.add_argument('-d', '--debug', action='store_true',
            help="Adds CINDERCLIENT_DEBUG=1 to the environment and passes"
            " --debug to selected command")

    try:
        # Read the configs
        conf = readConfigs()
        # Evaluate the command line arguments and return our args
        # the commands args and the environment choice the user made
        hubble_args, other_args, choice = evalArgs(conf, parser)
        # Do this so we pass along the -h to the command
        # if we are using invocation discovery
        if hubble_args.help and (choice is None):
            return parser.print_help()

        # If there was an error
        if conf.getError():
            print conf.getError()
            return 1

        if choice is None:
            print "Environments Configured: %s" % ",".join(conf.sections())
            print "See --help for usage"
            return 1
        if hubble_args.help:
            other_args.append('--help')

        # Set our log level
        if hubble_args.debug:
            log.setLevel(logging.DEBUG)

        # Read environment values from config files
        environments = getEnvironments(hubble_args, choice, conf)
        for env in environments:
            # Populate environment vars by running opt-cmd
            # if -o was passed on the commandline
            if hubble_args.option:
                if 'opt-cmd' not in env:
                    raise RuntimeError("provided -o|--option, but 'opt-cmd' is not defined in"
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

            if hubble_args.execute:
                # Use the command provided
                env.add({'cmd': hubble_args.execute})

            # At this point we should know our 'cmd' to run
            if 'cmd' not in env:
                raise RuntimeError("Please specify a 'cmd' somewhere in your config")

            # If --debug; print out our env config and pass along the --debug arg
            if hubble_args.debug:
                # For cinder client debug
                if env['cmd'].endswith('cinder'):
                    env.add({'CINDERCLIENT_DEBUG': '1'})
                print "%r\n" % env
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
                if e.errno == 2:
                    print "-- No such executable '%s', you must specify the executable "\
                        "in the [hubble-commands] section of the config (See README)"\
                        % env['cmd'].value
                raise RuntimeError("exec failed '%s' - %s" % (env['cmd'].value, e))
            print "\n",

    except (RuntimeError, CalledProcessError, NoSectionError), e:
        log.critical(e)
        return 1
