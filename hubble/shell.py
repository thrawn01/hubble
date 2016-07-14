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

from __future__ import print_function

import argparse
import logging
import os
import re
from subprocess import CalledProcessError, check_output, PIPE, Popen
import sys
import textwrap

from backports.configparser import NoOptionError, NoSectionError

from hubble.config import read_configs

try:
    # Not everyone needs keyring
    from hubble import keys
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
        def __init__(self, value='', section='', export=''):
            self.value = value
            self.export = export
            self.section = section

        def endswith(self, needle):
            return self.value.endswith(needle)

        def __repr__(self):
            return "Pair('%s', %s)" % (self.value, self.export)

    def set(self, key, value, section, export=True):
        """ Sets the value with a Pair() """
        self[key] = self.Pair(value, section, export)

    def delete(self, key):
        """ A safe delete """
        try:
            del self[key]
        except KeyError:
            pass

    def update(self, envs):
        for key, pair in envs.items():
            self[key] = pair

    def add(self, envs, section=None):
        """ Adds or removes items in the dict 'envs' to the collection """
        for key, value in envs.items():
            # if the value is empty
            if empty(value):
                # Delete the key from the env
                self.delete(key)
            # else add it
            self.set(key, value, section, key.isupper())

    def eval(self):
        """ Exapand all the ${variable} directives in the collection """
        for key, pair in self.items():
            self[key].value = self.expand_var(key, pair)
        return self

    def expand_var(self, variable, pair):
        """ Find a ${some_var} signature and expand it """
        result = pair.value
        # Find all the ${...}
        for match in re.finditer("\$\{\S+\}", pair.value):
            try:
                # Extract the variable name from ${...}
                var = match.group(0)
                key = var[2:-1]
                # Replace the entire ${...} sequence with the value named
                result = result.replace(var, self.get(key).value)
            except AttributeError:
                raise RuntimeError("no such environment variable "
                                   "'%s' in '%s'" % (key, result))
        # Expand keyring values if any
        return self.expand_keyring_var(variable, pair, result)

    def expand_keyring_var(self, variable, pair, value):
        """ Find 'USE_KEYRING' directives and expand them using the keyring """
        identifier = value.strip()
        if identifier.startswith("USE_KEYRING"):
            if keys is None:
                raise RuntimeError("found USE_KEYRING for '%s' but python "
                                   "keyring or getpass modules are not "
                                   "installed are required for keyring "
                                   "support" % variable)
            if identifier == "USE_KEYRING":
                return keys.get_password(pair.section, variable)
            else:
                regex = "USE_KEYRING\[([\x27\x22])(.*)\\1\]"
                variable = re.match(regex, value).group(2)
                return keys.get_password(variable, None)
        return value

    def to_dict(self):
        """
        Convert the entire collection of Pair() objects to a
        dict({'key': str()}) only where export == True
        """
        return dict([(key, value.value) for key, value in self.items()
                     if value.export])

    def __repr__(self):
        """ Pretty print the collection """
        # Calculate the max length of any key, and indent by that amount
        fmt = "%{0}s: %s".format(len(max(self.keys(), key=len)))
        return '\n'.join([fmt % (key, value.value) for key, value in
                          self.items()])


def empty(value):
    """ Return true if 'value' only has spaces or is empty """
    return value is None or re.match('^(|\s*)$', value) is not None


def green(msg):
    """ ASCII encode the string with green """
    return "\033[92m%s\033[0m" % msg


def get_environments(args, choice, config):
    """ Get the environment collection requested from args.env """
    sections = [choice]
    results = []
    conf = Env()

    # Merge in the requested environment
    conf.add(dict(config.items(choice)), choice)
    # If requested section is a meta section
    if 'meta' in conf:
        # Evaluate the list of sections this is a meta for
        sections = eval(conf['meta'].value)

    for section in sections:
        env = Env()
        # Add the name of the section
        env.add({'section': section}, section)
        # Add the choosen section
        env.update(conf)
        # Add the env section
        env.add(dict(config.items(section)), section)

        def f(i):
            return "opt.%s" % i[0], str(i[1])
        # Add the args to the environment as opt.'<arg_name>'
        env.add(dict(map(f, vars(args).items())), section)
        # Apply var expansion
        results.append(env.eval())
    return results


def to_dict(buf):
    """ Parse a string of 'key=value' into a dict({'key': 'value'}) """
    try:
        # Convert the bytes to string
        buf = buf.decode('utf-8').rstrip()

        if len(buf) == 0:
            print("-- Warning: executable specified by 'opt-cmd' did not "
                  "return any key=values, environment not updated")
            return dict()
        return dict([[i.strip() for i in line.split('=', 1)]
                     for line in buf.rstrip().split('\n')])
    except ValueError:
        print("-- Output from 'opt-cmd' was not parsed"
              " as a 'key=value' string")
        return dict()


def run(cmd, env):
    """Parse the output from the command passed into a dict({'key':
    'value'})

    """
    if empty(cmd):
        return {}

    # Execute the command with the current env
    # overlaid with our built environment
    environ = os.environ.copy()
    environ.update(env.to_dict())
    # Use of undocumented 'env' option on check_output
    return to_dict(check_output(cmd, shell=True, env=environ))


def cmd_path(cmd, conf):
    """ Find the 'cmd' in the config, or default to /usr/bin/'cmd' """
    basename = os.path.basename(cmd)
    try:
        return conf.get('hubble-commands', basename)
    except NoSectionError:
        log.warning("Missing [hubble-commands] section in config")
    except NoOptionError:
        log.debug("'%s' not found in [hubble-commands] section" % basename)
    return "/usr/bin/%s" % basename


def eval_args(conf, parser):
    env = conf.safe_get(conf.default_section, 'default-env')
    # If no default environment set, look for an
    # environment choice on the command line
    if not env:
        help = "The environment defined in ~/.hubblerc to use"
        parser.add_argument('env', nargs='?', metavar='<ENV>',
                            help=help)
        (arg1, arg2) = parser.parse_known_args()
        return (arg1, arg2, arg1.env)
    # Return the args with the default environment choice
    (arg1, arg2) = parser.parse_known_args()
    return (arg1, arg2, env)


def main():
    logging.basicConfig(format='-- %(message)s')
    log.setLevel(logging.CRITICAL)
    formatter_class = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(add_help=False,
                                     formatter_class=formatter_class,
                                     description=textwrap.dedent("""\
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
                        help="Adds CINDERCLIENT_DEBUG=1 to the environment "
                        "and passes --debug to selected command")

    try:
        # Read the configs
        conf = read_configs(default_section='hubble')
        # Evaluate the command line arguments and return our args
        # the commands args and the environment choice the user made
        hubble_args, other_args, choice = eval_args(conf, parser)
        # Do this so we pass along the -h to the command
        # if we are using invocation discovery
        if hubble_args.help and (choice is None):
            return parser.print_help()

        # If there was an error
        if conf.get_error():
            print(conf.get_error())
            return 1

        if choice is None:
            print("Environments Configured: %s" % ",".join(conf.sections()))
            print("See --help for usage")
            return 1
        if hubble_args.help:
            other_args.append('--help')

        # Set our log level
        if hubble_args.debug:
            log.setLevel(logging.DEBUG)

        # Read environment values from config files
        environments = get_environments(hubble_args, choice, conf)
        processes = []
        for env in environments:
            # Populate environment vars by running opt-cmd
            # if -o was passed on the commandline
            if hubble_args.option:
                if 'opt-cmd' not in env:
                    message = "provided -o|--option, but 'opt-cmd' is not " \
                              "defined in '%s' section" % env['section'].value
                    raise RuntimeError(message)
                env.add(run(env['opt-cmd'].value, env))

            # Populate environment vars by running the env-cmd if it exists
            if 'env-cmd' in env:
                env.add(run(env['env-cmd'].value, env))

            # If querying multiple environments, display the env name
            if hubble_args.debug:
                print("-- [%s] --" % green(env['section'].value))

            # If our invocation name is not 'hubble'
            if not sys.argv[0].endswith('hubble'):
                # Use the invocation name as our 'cmd'
                env.add({'cmd': cmd_path(sys.argv[0], conf)})

            if hubble_args.execute:
                # Use the command provided
                env.add({'cmd': hubble_args.execute})

            # At this point we should know our 'cmd' to run
            if 'cmd' not in env:
                raise RuntimeError("Please specify a 'cmd' somewhere in "
                                   "your config")

            # If --debug; print out our env config and pass along the
            # --debug arg
            if hubble_args.debug:
                # For cinder client debug
                if env['cmd'].endswith('cinder'):
                    env.add({'CINDERCLIENT_DEBUG': '1'})
                print("%r\n" % env)
                other_args.insert(0, '--debug')

            # Grab a copy of the local environment and inject it into
            # our environment
            environ = os.environ.copy()
            environ.update(env.to_dict())

            try:
                # Run the requested command
                p = Popen([env['cmd'].value] + other_args,
                          stdout=PIPE,
                          stderr=PIPE,
                          env=environ)
                processes.append((p, env['section'].value))
            except OSError as e:
                if e.errno == 2:
                    print("-- No such executable '%s', you must specify the "
                          "executable in the [hubble-commands] section of the "
                          "config (See README)" % env['cmd'].value)
                message = "exec failed '%s' - %s" % (env['cmd'].value, e)
                raise RuntimeError(message)

        for p, env in processes:
            if len(environments) != 1:
                print("-- [%s] --" % green(env))
            # Wait for the command to complete
            stdout, stderr = p.communicate()
            sys.stdout.write(stdout.decode('utf-8'))
            sys.stderr.write(stderr.decode('utf-8'))

    except (RuntimeError, NoSectionError) as e:
        log.critical(e)
        return 1
    except CalledProcessError as e:
        log.critical(e.output)
        log.critical(e)
        return 1
