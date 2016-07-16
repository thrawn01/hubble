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

from io import StringIO
import os
import tempfile
import unittest

from hubble.shell import main


def safe_eval(io_out):
    str_out = io_out.getvalue()
    print(str_out)
    if len(str_out) != 0:
        return eval(str_out)
    return {}


def run_main(config, argv):
    stdout = StringIO()
    stderr = StringIO()
    ret = main(argv, stdout=stdout, stderr=stderr, files=[config])
    return ret, safe_eval(stdout), safe_eval(stderr)


def generate_test_cmd(print_stmt):
    with tempfile.NamedTemporaryFile(delete=False) as fd:
        fd.write("#! /usr/bin/env python\n"
                 "from __future__ import print_function\n"
                 "import os\n"
                 "{0}\n".format(print_stmt).encode())
        fd.flush()
    os.chmod(fd.name, 0o755)
    return fd.name


class TestHubble(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.opt_cmd = generate_test_cmd("print('opt-injected-key=value\\n')")
        cls.cmd = generate_test_cmd("print(dict(os.environ))")

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.opt_cmd)
        os.unlink(cls.cmd)

    def test_opt_cmd(self):
        config = StringIO(u"""[hubble]
            name=Test
            opt-cmd={0} ${{opt.option}} ${{name}}
            [dfw]
            cmd={1}
            SOME=Thing""".format(self.opt_cmd, self.cmd))
        config.name = "test.conf"

        ret, out, err = run_main(config, ["hubble", "-o", "my-option",
                                          "dfw", "--debug"])
        self.assertEqual(ret, 0)
        self.assertEqual(out['SOME'], "Thing")
        self.assertEqual(out['opt-injected-key'], "value")
