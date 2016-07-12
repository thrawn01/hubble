import unittest

from hubble import config
from hubble.tests.unit import fake_configs


class TestCase(unittest.TestCase):
    default_section = 'hubble'

    def fromstring(self, config_string):
        config = self.config_class(
            default_section=self.default_section
        )
        config.read_string(config_string)
        return config

    def set(self, section):
        return set(dict(self.config.items(section)))

    def setUp(self):
        super(TestCase, self).setUp()
        self.config = self.fake_config(self.fromstring)


class TestInheritance(TestCase):
    config_class = config.InheritanceConfigParser
    fake_config = fake_configs.fake_inheritance_config

    def test_items_get(self):
        items = dict(self.config.items('c'))
        value = self.config.get('c', 'a')
        self.assertEqual(items['a'], value)

    def test_inheritance(self):
        c = self.set('c')
        a = self.set('a')
        self.assertTrue(c.issuperset(a))

    def test_nested_inheritance(self):
        d = self.set('d')
        a = self.set('a')
        self.assertTrue(d.issuperset(a))

    def test_multiple_inheritance(self):
        e = self.set('e')
        b = self.set('b')
        d = self.set('d')
        self.assertTrue(e.issuperset(b))
        self.assertTrue(e.issuperset(d))

    def test_value_resolution(self):
        b_spam = self.config.get('b', 'spam')
        self.assertEquals(b_spam, 'bar')
        c_spam = self.config.get('c', 'spam')
        self.assertEquals(c_spam, 'eggs')
        d_spam = self.config.get('d', 'spam')
        self.assertEquals(d_spam, 'foo')
        e_spam = self.config.get('e', 'spam')
        self.assertEquals(e_spam, 'foo')
