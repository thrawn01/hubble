# Introduction
*hubble* is an environment variable manager for tools like cinderclient, novaclient, swiftclient and swiftly that rely on environment variables for configuration.

# Installation
```
git clone git://github.com/thrawn01/hubble.git
cd hubble
python setup.py install
```

# What do now?
Say you have 2 environments, one is production, the other is staging. Both environments have swift and nova! What do you do?

## Option 1 - Invocation (Recommended)
Create a ``~/.hubblerc`` file
```
[hubble]
# Variables that are defined for all sections
OS_AUTH_URL=https://production.auth.thrawn01.com
OS_SERVICE_NAME=cloudserversOpenStack
OS_VERSION=2.0

[staging]
# Swiftly Client
SWIFTLY_AUTH_URL=https://staging.auth.thrawn01.org/v1.0
SWIFTLY_AUTH_USER=staging-swift-user
SWIFTLY_AUTH_KEY=staging-swift-user
# Nova
OS_AUTH_URL=https://staging.auth.thrawn01.org/v1.0
OS_USERNAME=staging-user
OS_PASSWORD=staging-password
OS_TENANT_NAME=000001
OS_REGION_NAME=USA

[prod]
# Swiftly Client
SWIFTLY_AUTH_URL=https://staging.auth.thrawn01.org/v1.0
SWIFTLY_AUTH_USER=prod-swift-user
SWIFTLY_AUTH_KEY=prod-swift-key
# Nova
OS_AUTH_URL=https://prod.auth.thrawn01.org/v1.0
OS_USERNAME=prod-username
OS_PASSWORD=prod-password
OS_TENANT_NAME=000001
OS_REGION_NAME=USA
```

Now create a local directory in your path and link hubble to the commands you want to use.
```
mkdir ~/bin
export PATH="~/bin;$PATH"
ln -s /usr/bin/hubble ~/bin/nova
ln -s /usr/bin/hubble ~/bin/cinder
ln -s /usr/bin/hubble ~/bin/swiftly
```

If actual executables for nova, cinder and swiftly are installed in ``/usr/bin`` Your done! You can now execute the following.
```
$ nova prod list
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks                                                                            |
+--------------------------------------+--------------+--------+----------------
| 54e2b87c-2850-11e2-a96f-e3cb6992c8ed | thrawn01.org | ACTIVE | public=10.26.18
+--------------------------------------+--------------+--------+----------------

$ swiftly staging get /
/thrawn01.org-files
/images
/src

```
### For executables in non-standard locations (like virtualenv)
Add the following section to your ``~/.hubblerc`` file. This tells hubble where to look when executing the client
```
[hubble-commands]
swiftly=/home/username/virtualenv/python/bin/swiftly
nova=/home/username/virtualenv/python/bin/nova
cinder=/home/username/virtualenv/python/bin/cinder
```

## Option 2 - Define command specific sections
Create a ``~/.hubblerc`` file
```
[hubble]
# Variables that are defined for all sections
OS_AUTH_URL=https://production.auth.thrawn01.com
OS_SERVICE_NAME=cloudserversOpenStack
OS_VERSION=2.0

[nova-staging]
OS_AUTH_URL=https://staging.auth.thrawn01.org/v1.0
OS_USERNAME=staging-user
OS_PASSWORD=staging-password
OS_TENANT_NAME=000001
OS_REGION_NAME=USA
cmd=/usr/bin/nova

[swiftly-staging]
SWIFTLY_AUTH_URL=https://staging.auth.thrawn01.org/v1.0
SWIFTLY_AUTH_USER=staging-swift-user
SWIFTLY_AUTH_KEY=staging-swift-user
cmd=/usr/bin/swiftly

[nova-prod]
OS_AUTH_URL=https://prod.auth.thrawn01.org/v1.0
OS_USERNAME=prod-username
OS_PASSWORD=prod-password
OS_TENANT_NAME=000001
OS_REGION_NAME=USA
cmd=/usr/bin/nova

[swiftly-prod]
SWIFTLY_AUTH_URL=https://staging.auth.thrawn01.org/v1.0
SWIFTLY_AUTH_USER=prod-swift-user
SWIFTLY_AUTH_KEY=prod-swift-key
cmd=/usr/bin/swiftly
```
You can now execute the following.
```
$ hubble nova-prod list
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks                                                                            |
+--------------------------------------+--------------+--------+----------------
| 54e2b87c-2850-11e2-a96f-e3cb6992c8ed | thrawn01.org | ACTIVE | public=10.26.18
+--------------------------------------+--------------+--------+----------------

$ hubble swiftly-staging get /
/thrawn01.org-files
/images
/src

```

# But I don't want to store my passwords in plain text!
You can use a third party script (comming soon) to retrieve passwords out of a keyring (like OSX Keychain)
Just add the ``env-cmd`` to a section in your ``.hubblerc`` file like so.
```
[prod]
OS_AUTH_URL=https://prod.auth.thrawn01.org/v1.0
OS_REGION_NAME=USA
env-cmd=keyring-command --get ${section} 
```
${section} will get expanded to the section you the ``env-cmd`` is in. You also have access to any other variables
available in the section. For example you could key off of the OS_AUTH_URL to get your credentials
```
[prod]
OS_AUTH_URL=https://prod.auth.thrawn01.org/v1.0
OS_REGION_NAME=USA
env-cmd=keyring-command --auth ${OS_AUTH_URL} --get ${section}
```

The only requirement for the ``env-cmd`` is that it must output the variables in the following format
```
KEY=VALUE
key=value
```
Each variable must be separated by a new line '\n'. As an example the following is a valid
``env-cmd``` that will add a variable 'FOO' to the environment ``env-cmd=echo 'FOO=BAR' ``

# What if I want to optionally execute an external script? (For impersonating customers!)
hubble provides an ``-o`` option to pass in additional information on the command line when building an environment.
If the ``-o`` option is used hubble will look for a ``opt-cmd`` in the selected section defined in ```.hubblerc```

As an example, take the following [prod] sections
```
[prod]
OS_AUTH_URL=https://prod.auth.thrawn01.org/v1.0
OS_REGION_NAME=USA
env-cmd=keyring-command --auth ${OS_AUTH_URL} --get ${section}
opt-cmd=get-customer-credentials --auth ${OS_AUTH_URL} --username ${opt.options}
```
With this configuration it is possible to access the prod environment with your credentials
```
nova prod list
```
or with a customers credentials
```
nova prod -o cust-user-name list
```

# How about running a command accross multiple environments?
You can define a section in ```~/.hubblerc``` as a meta section. 
The meta section tells hubble to source all the environment variables in the current
section, then source and run a command for each section listed in the meta list.

As an example
```
[usa]
OS_AUTH_URL=http://usa.auth.thrawn01.org
meta=['chicago', 'dallas']

[london]
OS_AUTH_URL=http://lon.auth.thrawn01.org

[chicago]
OS_USERNAME=ord-user
OS_PASSWORD=ord-password
OS_TENANT_NAME=000001

[dallas]
OS_USERNAME=dallas-user
OS_PASSWORD=dallas-password
OS_TENANT_NAME=000001
```
This configuration allows a user to specify a 'usa' environment that will run
a command for both the chicago and dallas environments
```
$ nova usa list
-- [dallas] --
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks                                                                            |
+--------------------------------------+--------------+--------+----------------
| 54e2b87c-2850-11e2-a96f-e3cb6992c8ed | thrawn01.org | ACTIVE | public=10.26.18
+--------------------------------------+--------------+--------+----------------

-- [chicago] --
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks                                                                            |
+--------------------------------------+--------------+--------+----------------
| 6f586a82-2858-11e2-bbfe-e3c8f66fdabb | backup01.org | ACTIVE | public=11.20.16
+--------------------------------------+--------------+--------+----------------
```
