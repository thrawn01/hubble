@staticmethod
def fake_inheritance_config(config_factory):
    config_string = u"""
[hubble]
spam = eggs
[a]
a = 1
[b]
b = 2
spam = bar
[c]
%inherit = a
c = 3
[d]
%inherit = c
d = 4
spam = foo
[e]
%inherit =
  d
  b
e = 5
"""

    return config_factory(config_string)
