# Copyright (c) 2013 Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import fixtures
import os
import testtools

from marconi.common import config

CFG = config.project()


class TestBase(testtools.TestCase):
    """Child class of testtools.TestCase for testing Marconi.

    Inherit from this and write your test methods. If the child class defines
    a prepare(self) method, this method will be called before executing each
    test method.
    """

    def setUp(self):
        super(TestBase, self).setUp()
        self.useFixture(fixtures.FakeLogger('marconi'))

        stdout = self.useFixture(fixtures.StringStream('stdout')).stream
        self.useFixture(fixtures.MonkeyPatch('sys.stdout', stdout))

        stderr = self.useFixture(fixtures.StringStream('stderr')).stream
        self.useFixture(fixtures.MonkeyPatch('sys.stderr', stderr))

    def conf_path(self, filename):
        """Returns the full path to the specified Marconi conf file.

        :param filename: Name of the conf file to find (e.g.,
                         "wsgi_memory.conf")
        """

        parent = os.path.dirname(self._my_dir())
        return os.path.join(parent, 'etc', filename)

    def load_conf(self, filename):
        """Loads `filename` configuration file.

        :param filename: Name of the conf file to find (e.g.,
                         "wsgi_memory.conf")

        :returns: Project's config object.
        """
        CFG.load(filename=self.conf_path(filename))
        return CFG

    def _my_dir(self):
        return os.path.abspath(os.path.dirname(__file__))
