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


from hubble.shell import getEnvironments, Env, run, toDict, empty
from hubble.config import parseConfigs
from six.moves import StringIO
import unittest
import argparse


class TestEnv(unittest.TestCase):
    def test_env(self):
        env = Env()
        env.set('first', 'Derrick', 'section')
        env.set('last', 'Wippler', 'section')
        env.set('string', 'My name is ${first} ${last}', 'section')
        env.eval()
        self.assertEqual(env['string'].value, "My name is Derrick Wippler")
        self.assertEqual(env['string'].section, "section")

    def test_env_toDict(self):
        env = Env()
        env.set('first', 'Derrick', 'section')
        env.set('last', 'Wippler', 'section')
        env.set('no-export', 'wat', 'section', export=False)
        self.assertEqual(env.toDict(), {'first': 'Derrick', 'last': 'Wippler'})

    def test_getEnvironments(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('env')
        parser.add_argument('--user', default='', required=False)
        args = parser.parse_args(['blah'])

        file = StringIO("[hubble]\n"
                        "name=My name is ${FIRST} ${last}\n"
                        "[prod-meta]\n"
                        "meta=['name', 'place']\n"
                        "[name]\n"
                        "FIRST=Derrick\n"
                        "last=Wippler\n")
        file.name = "test-config.ini"
        config = parseConfigs([file], default_section='hubble')
        env = getEnvironments(args, 'name', config)
        self.assertIn('name', env[0])
        self.assertEqual(env[0]['name'].value, 'My name is Derrick Wippler')

        self.assertIn('FIRST', env[0])
        self.assertIn('last', env[0])


class TestHubble(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(empty(None), True)
        self.assertEqual(empty(""), True)
        self.assertEqual(empty("1"), False)
        self.assertEqual(empty("   "), True)
        self.assertEqual(empty("   r"), False)

    def test_toDict(self):
        expected = {'key': 'value', 'foo': 'bar'}
        self.assertEqual(toDict(b"key=value\nfoo=bar\n"), expected)

    def test_run(self):
        env = run('echo "USER=thrawn\nSHELL=bash"', Env())
        self.assertIn('USER', env)
        self.assertIn('SHELL', env)
