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


from hubble.shell import getEnvironments, Env, run, toDict, parseFiles
from StringIO import StringIO
import unittest
import argparse


class TestEnv(unittest.TestCase):
    def test_env(self):
        env = Env()
        env.set('first', 'Derrick')
        env.set('last', 'Wippler')
        env.set('string', 'My name is ${first} ${last}')
        env.eval()
        self.assertEquals(env['string'].value, "My name is Derrick Wippler")

    def test_env_toDict(self):
        env = Env()
        env.set('first', 'Derrick')
        env.set('last', 'Wippler')
        self.assertEquals(env.toDict(), {'first': 'Derrick', 'last': 'Wippler'})

    def test_getEnvironments(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('env')
        parser.add_argument('--user', default='', required=False)
        args = parser.parse_args(['name'])

        file = StringIO("[hubble]\n"
                        "name=My name is ${FIRST} ${last}\n"
                        "[prod-meta]\n"
                        "meta=['name', 'place']\n"
                        "[name]\n"
                        "FIRST=Derrick\n"
                        "last=Wippler\n")
        env = getEnvironments(args, parseFiles([file]))
        self.assertIn('name', env[0])
        self.assertEquals(env[0]['name'].value, 'My name is Derrick Wippler')

        self.assertIn('FIRST', env[0])
        self.assertIn('last', env[0])

    def test_toDict(self):
        self.assertEquals(toDict("key=value\nfoo=bar\n"), {'key': 'value', 'foo': 'bar'})

    def test_run(self):
        env = run('echo "USER=thrawn\nSHELL=bash"')
        self.assertIn('USER', env)
        self.assertIn('SHELL', env)

