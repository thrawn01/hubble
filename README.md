# Introduction
*hubble* is an environment variable manager for tools like cinderclient, novaclient,
swiftclient and swiftly that rely on environment variables for configuration.

It is inspired by the most excellent supernova written by Major Haden
(https://github.com/major/supernova/). Imagine hubble as supernova, but
not just for nova

# Installation
## GIT
```
git clone git://github.com/thrawn01/hubble.git
cd hubble
python setup.py install
```
## PIP
```
pip install git+git://github.com/thrawn01/hubble.git@master
```

# Usage
To use hubble, you must define some environments in the config file ``~/.hubblerc``.
Each environment is given a name followed by the variables that will be populated
into the environment when that environment is chosen from the command line

Hubble has 2 modes of usage, Invocation Discovery and Command Configuration

## Invocation Discovery (Recommended)
With Invocation Discovery hubble chooses the command it will run by inspecting
the name of the program it was invoked as.

The following is an example with two environments *prod* and *staging*
```
[hubble]
# Variables defined here are included in all environments
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

Now create a local directory in your path and link hubble to the commands
you want to use. 

```
mkdir ~/bin
export PATH="~/bin;$PATH"
ln -s /usr/bin/hubble ~/bin/nova
ln -s /usr/bin/hubble ~/bin/swiftly
```
When hubble is executed, it will inspect the name it was invoked as (in 
this case the linked name) and attempt to execute *that* name as the command.
If executables for nova and swiftly are installed in ``/usr/bin``; Your done!

You can now type the following
```
$ nova prod list
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks
+--------------------------------------+--------------+--------+----------------
| 54e2b87c-2850-11e2-a96f-e3cb6992c8ed | thrawn01.org | ACTIVE | public=10.26.18
+--------------------------------------+--------------+--------+----------------

$ swiftly staging get /
/thrawn01.org-files
/images
/src


```
### Executables in non-standard locations (like virtualenv)
Often commands to be executed are not located in ``/usr/bin`` or you don't want to
replace the original command with one linked to ``hubble``. In this case hubble allows
you to tell it what command should be called dependent upon the invocation name

In the following example we have *hubble*, *nova* and *cinder* installed in a local virtualenv.
Here we don't want to override the use of ``nova`` so we create a new link called 
``supernova`` and tell ``hubble`` when it sees an invocation as ``supernova`` run the 
``nova`` command

```
# Add the following section to your ~/.hubblerc file.
[hubble-commands]
swiftly=/home/username/virtualenv/python/bin/swiftly
supernova=/home/username/virtualenv/python/bin/nova
cinder=/home/username/virtualenv/python/bin/cinder

# Now create a link for supernova
$ ln -s /home/username/virtualenv/python/bin/hubble ~/bin/supernova

# Run hubble like Supernova
$ supernova prod list
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks
+--------------------------------------+--------------+--------+----------------
| 54e2b87c-2850-11e2-a96f-e3cb6992c8ed | thrawn01.org | ACTIVE | public=10.26.18
+--------------------------------------+--------------+--------+----------------
```

## Command Configuration
With Command Configuration we use the ``~/.hubblerc`` sections to define what command 
should be executed when ``hubble`` runs

In the following example we create two config sections for each environment. One for the 
``nova`` command and the other for the ``swiftly`` command
```
[hubble]
# Variables defined here are included in all environments
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
| ID                                   | Name         | Status | Networks
+--------------------------------------+--------------+--------+----------------
| 54e2b87c-2850-11e2-a96f-e3cb6992c8ed | thrawn01.org | ACTIVE | public=10.26.18
+--------------------------------------+--------------+--------+----------------

$ hubble swiftly-staging get /
/thrawn01.org-files
/images
/src

```

## Directory specific configuration
Hubble supports a directory-scoped configuration. For instance, if you are in a development
directory you may want ``nova`` and ``swift`` commands to use a specific environment
by default, (perhaps a development environment) or have access to environments you should 
only access from a specific directory.

To support this, you can create a ``.hubblerc`` file in the local directory. Hubble will
read this file during invocation and overide any global configuration with the local one.

In addition you can set a *default* environment when none is found on the command line. To do this,
you must define ``default-env`` in the ``[hubble]`` section of the config. 

For example, create a file called ``.hubblerc`` in the directory called ``~/dev``
```
[hubble]
default-env=development

[development]
OS_AUTH_URL=https://development.auth.thrawn01.org/v1.0
OS_USERNAME=dev-user
OS_PASSWORD=dev-password
OS_TENANT_NAME=000001
OS_REGION_NAME=USA
cmd=/usr/bin/cinder
```
Now run the following, and hubble will always use the 'development' environment
```
$ cd ~/dev
$ hubble list
```
If you have a Invocation Discovery configuration, you can invoke your command
of choice and the default environment will be used. The use of hubble in this configuration
is completely transparent!
```
$ cd ~/dev
$ nova list
+--------------------------------------+-------------+--------+----------------
| ID                                   | Name        | Status | Networks
+--------------------------------------+-------------+--------+----------------
| 54e2b87c-2850-11e2-a96f-e3cb6992c8ed | devel-box   | ACTIVE | public=10.26.18
+--------------------------------------+-------------+--------+----------------
$ swiftly get /
/devel-box-files
/images
/src
```

*NOTE:* One side effect of using ``default-env`` is that you cannot get to hubble's ``-h`` help option.
Hubble will always pass along the ``-h`` to the command defined by the default environment (In the above case, cinder)

## But I don't want to store my passwords in plain text!
You can use a third party script (coming soon) to retrieve passwords out of a keyring (like OSX Keychain)
Just add the ``env-cmd`` to an environment in your ``~/.hubblerc`` like so.
```
[prod]
OS_AUTH_URL=https://prod.auth.thrawn01.org/v1.0
OS_REGION_NAME=USA
env-cmd=keyring-command --get ${section} 
```
``${section}`` will get expanded to the section you defined the ``env-cmd`` in. You also have access to any other variables
available in the section. For example you could key off of the $OS_AUTH_URL to get your credentials
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
A new line ‘\n’ must separate each variable. As an example the following is a valid
``env-cmd`` that will add a variable 'FOO' to the environment ``env-cmd=echo 'FOO=BAR' ``

## What if I want to optionally execute an external script? (For impersonating customers!)
hubble provides an ``-o`` option to pass in additional information on the command line when building an environment.
If the ``-o`` option is used hubble will look for a ``opt-cmd`` in the selected section defined in ```.hubblerc```

As an example, take the following [prod] section
```
[prod]
OS_AUTH_URL=https://prod.auth.thrawn01.org/v1.0
OS_REGION_NAME=USA
env-cmd=keyring-command --auth ${OS_AUTH_URL} --get ${section}
opt-cmd=get-customer-credentials --auth ${OS_AUTH_URL} --username ${opt.option}
```
With this configuration it is possible to access the prod environment with your credentials
```
nova prod list
```
or with a customers credentials
```
nova prod -o cust-user-name list
```

## How about running a command across multiple environments?
You can define a section in ```~/.hubblerc``` as a meta section. 
The meta section tells hubble to source all the environment variables in the current
section, then source and run the command for each section listed in the meta list.

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
| ID                                   | Name         | Status | Networks
+--------------------------------------+--------------+--------+----------------
| 54e2b87c-2850-11e2-a96f-e3cb6992c8ed | thrawn01.org | ACTIVE | public=10.26.18
+--------------------------------------+--------------+--------+----------------

-- [chicago] --
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks
+--------------------------------------+--------------+--------+----------------
| 6f586a82-2858-11e2-bbfe-e3c8f66fdabb | backup01.org | ACTIVE | public=11.20.16
+--------------------------------------+--------------+--------+----------------
```

## How about running an arbitrary command?
When executing remote ssh commands with tools like fabric or dsh the local user
environment doesn't get sourced which makes running custom scripts that make
use of CinderClient or NovaClient difficult to run without hard coding
environment variables. Hubble improves this situation by allowing a minimal
`.hubblerc` file with the ability to execute arbitrary commands via the command
line

Here is an example of a minimal `.hubblerc`
```
[hubble]
OS_AUTH_URL=https://development.auth.thrawn01.org/v1.0
OS_USERNAME=user
OS_PASSWORD=password
OS_TENANT_NAME=000001
OS_REGION_NAME=USA
default-env=local
```
Notice the inclusion of the [hubble] section is optional. With this config we
can run hubble with our custom command remotely like so

```
ssh thrawn@my-host.com /usr/bin/hubble -e /path/to/custom-command
```

## Complete list of available variables
* *${section}** - The name of the current environment (useful when using **meta**)
* **${cmd}** - Name of the command running for this environment
* **${opt-cmd}** - The value of the optional command for this environment
* **${env-cmd}** - The value of the env command for this environment
* **${opt.option}** - The argument passed in via the -o|--option command line argument
* **${opt.env}** - The environment name passed in as a command line argument
* **${opt.debug}** - 'True' if --debug was used on the command line else 'False'

