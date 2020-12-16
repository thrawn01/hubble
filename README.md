[![Coverage Status](https://img.shields.io/coveralls/thrawn01/hubble.svg)](https://coveralls.io/github/thrawn01/hubble)
[![Build Status](https://img.shields.io/travis/thrawn01/hubble/master.svg)](https://travis-ci.org/thrawn01/hubble)

# What is this hubble thing?
*hubble* is an environment variable manager for tools like cinderclient, novaclient,
swiftclient and swiftly that rely on environment variables for configuration.

If you work with openstack deployments in multiple regions, you want to use *hubble*

# What can I do with it?

#### Run nova commands against multiple regions!
```
$ hubble nova-dfw list
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks
+--------------------------------------+--------------+--------+----------------
| 54e2b87c-2850-11e2-a96f-e3cb6992c8ed | dallas.org   | ACTIVE | public=10.26.18
+--------------------------------------+--------------+--------+----------------

$ hubble nova-ord list
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks
+--------------------------------------+--------------+--------+----------------
| a8c0cce4-3bb8-11e5-b530-600308a97d8c | chicago.org  | ACTIVE | public=10.28.11
+--------------------------------------+--------------+--------+----------------
```

#### Run openstack commands across multiple regions
```
$ hubble cinder-all show e5b66064-3bb8-11e5-bdac-600308a97d8c
-- [dfw] --
ERROR: No volume with a name or ID of 'e5b66064-3bb8-11e5-bdac-600308a97d8c' exists.

-- [iad] --
ERROR: No volume with a name or ID of 'e5b66064-3bb8-11e5-bdac-600308a97d8c' exists.

-- [ord] --
ERROR: No volume with a name or ID of 'e5b66064-3bb8-11e5-bdac-600308a97d8c' exists.

-- [hkg] --
+------------------------------+------------------------------------------------------------+
|           Property           |                           Value                            |
+------------------------------+------------------------------------------------------------+
|         attachments          |                             []                             |
|      availability_zone       |                            nova                            |
|           bootable           |                           false                            |
|          created_at          |                 2015-08-05T21:33:52.000000                 |
|     display_description      |                            None                            |
|         display_name         |                            None                            |
|          encrypted           |                           False                            |
|              id              |            e5b66064-3bb8-11e5-bdac-600308a97d8c            |
| os-vol-tenant-attr:tenant_id |                          account1                          |
|             size             |                             1                              |
|            status            |                         available                          |
|         volume_type          |                            SATA                            |
+------------------------------+------------------------------------------------------------+
```

#### Impersonate a tenant (vendor specific)
```
$ hubble nova-ord -o <tenant-id> list
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks
+--------------------------------------+--------------+--------+----------------
| 23dab790-3bba-11e5-8b6e-600308a97d8c | tenant.org   | ACTIVE | public=10.20.10
+--------------------------------------+--------------+--------+----------------
```

#### Use a different region, based off your current directory
```
$ cd ~/dfw-stuff
$ hubble list
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks
+--------------------------------------+--------------+--------+----------------
| 54e2b87c-2850-11e2-a96f-e3cb6992c8ed | thrawn01.org | ACTIVE | public=10.26.18
+--------------------------------------+--------------+--------+----------------

$ cd ~/ord-stuff
$ hubble list
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks
+--------------------------------------+--------------+--------+----------------
| a8c0cce4-3bb8-11e5-b530-600308a97d8c | ubuntu.org   | ACTIVE | public=10.28.11
+--------------------------------------+--------------+--------+----------------
```

#### Create special environment specific commands using hubble
```
$ supernova dfw list
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks
+--------------------------------------+--------------+--------+----------------
| 54e2b87c-2850-11e2-a96f-e3cb6992c8ed | thrawn01.org | ACTIVE | public=10.26.18
+--------------------------------------+--------------+--------+----------------

$ supercinder hkg show e5b66064-3bb8-11e5-bdac-600308a97d8c
+------------------------------+------------------------------------------------------------+
|           Property           |                           Value                            |
+------------------------------+------------------------------------------------------------+
|         attachments          |                             []                             |
|      availability_zone       |                            nova                            |
|           bootable           |                           false                            |
|          created_at          |                 2015-08-05T21:33:52.000000                 |
|     display_description      |                            None                            |
|         display_name         |                            None                            |
|          encrypted           |                           False                            |
|              id              |            e5b66064-3bb8-11e5-bdac-600308a97d8c            |
| os-vol-tenant-attr:tenant_id |                          account1                          |
|             size             |                             1                              |
|            status            |                         available                          |
|         volume_type          |                            SATA                            |
+------------------------------+------------------------------------------------------------+
```
#### Keep your passwords safe
Hubble can store credentials in your operating system's local keystore. Just
use ``hubble-keyring`` to store a credential.
```
hubble-keyring --set my-password
Enter Credential (CTRL-D to abort) >

-- Successfully stored credentials for variable 'my-password' in environment [__global__] under keyring 'hubble'
```
Then use the stored password in ``~/.hubblerc``
```
[dfw]
OS_PASSWORD=USE_KEYRING['my-password']
```

# Installation
## GIT
```
git clone git://github.com/thrawn01/hubble.git
cd hubble
python setup.py install
```
## PIP
```
pip install hubble
```

## Golang Version
This is a work in progress and only supports a subset of features

```
go install github.com/thrawn01/hubble
```

# Configuration
To use hubble, you must define some environments in the config file ``~/.hubblerc``.
Each environment is given a name followed by the variables that will be populated
into the environment when that environment is chosen from the command line

In the following example we create two config sections for each environment.
One for the [nova](https://github.com/openstack/python-novaclient) command and
the other for the [swiftly](https://github.com/gholt/swiftly) command

```
# --------------------------------------------------------
# Variables defined here are included in all environments
# --------------------------------------------------------
[hubble]
OS_AUTH_URL=https://identity.api.rackspacecloud.com/v2.0/
OS_AUTH_SYSTEM=rackspace
NOVA_RAX_AUTH=1

# ------------------------------------
# Credentials
# ------------------------------------
OS_PASSWORD=USE_KEYRING['rackspace-api-key']
OS_USERNAME=your-rackspace-username
OS_TENANT_NAME=123456

# ------------------------------------
# Rackspace Regions
# ------------------------------------
[nova-dfw]
OS_REGION_NAME=DFW
cmd=/usr/bin/nova

[swift-ord]
OS_REGION_NAME=ORD
SWIFTLY_AUTH_URL=${OS_AUTH_URL}
SWIFTLY_AUTH_USER=${OS_USERNAME}
SWIFTLY_AUTH_KEY=USE_KEYRING['rackspace-api-key']
cmd=/usr/bin/swiftly
```

You can now execute the following.
```
$ hubble nova-dfw list
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks
+--------------------------------------+--------------+--------+----------------
| 54e2b87c-2850-11e2-a96f-e3cb6992c8ed | thrawn01.org | ACTIVE | public=10.26.18
+--------------------------------------+--------------+--------+----------------

$ hubble swift-ord get /
/thrawn01.org-files
/images
/src
```

## If your using rackspace cloud
There is a complete ``~/.hubblerc`` example for use with rackspace cloud
available in the
[examples/](https://github.com/thrawn01/hubble/blob/master/examples)
directory.

## Directory specific configuration
Hubble supports a directory-scoped configuration. For instance, if you are in a development
directory you may want ``nova`` and ``swift`` commands to use a specific environment
by default.

To support this, you can create a ``.hubblerc`` file in the local directory. Hubble will
read this file during invocation and override any global configuration with the local one.

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
OS_REGION_NAME=RegionOne
cmd=/usr/bin/cinder
```
Now run the following, and hubble will always use the 'development' environment
```
$ cd ~/dev
$ hubble list
```

*NOTE:* One side effect of using ``default-env`` is that you cannot get to hubble's ``-h`` help option.
Hubble will always pass along the ``-h`` to the command defined by the default environment (In the above case, cinder)

## But I don't want to store my passwords in plain text!

### Global keyring storage
Storing a credential as a global credential allows you to use it across
multiple environments. The greatest benefit of this option is that you only
need to set credentials in one place within your keyring.

To set a global keyring use ``hubble-keyring``
```
$ hubble-keyring --set os-password
Enter Credential (CTRL-D to abort) >

-- Successfully stored credentials for variable 'os-password' in environment [__global__] under keyring 'hubble'
```

You can verify the value stored with the ``--get`` option

```
$ hubble-keyring --get os-password
my-password-i-typed
```

Once you have a credential set in the keystore you can use
``USE_KEYRING['os-password']`` in the hubble config in place of your actual
password. NOTE: The name used 'os-password' holds no special meaning, you can
use what ever name you want to store your username, password or whatever.

```
[dfw]
OS_REGION_NAME=DFW
OS_USERNAME=USE_KEYRING['username']
OS_PASSWORD=USE_KEYRING['dfw-password']

[ord]
OS_REGION_NAME=ORD
OS_USERNAME=USE_KEYRING['username']
OS_PASSWORD=USE_KEYRING['ord-password']
```

### Environment-specific keyring storage
To set a environment specific keyring, first modify the ``.hubblerc`` config.
```
[dfw]
OS_REGION_NAME=DFW
OS_PASSWORD=USE_KEYRING
```

Then set the ``OS_PASSWORD`` with the ``hubble-keyring --set dfw OS_PASSWORD``
```
$ hubble-keyring --set dfw OS_PASSWORD
Enter Credential (CTRL-D to abort) >

-- Successfully stored credentials for variable 'OS_PASSWORD' in environment [dfw] under keyring 'hubble'
```

Now only ``OS_PASSWORD`` in the ``[dfw]`` section will get the stored keystore credential

## What if I want to inject environment variables via an external script? (For impersonating customers!)
hubble provides an ``-o`` option to pass in additional information on the command line when building an environment.
If the ``-o`` option is used hubble will look for a ``opt-cmd`` in the selected section defined in ```.hubblerc```

As an example, take the following [nova-prod] section
```
[nova-prod]
OS_AUTH_URL=https://prod.auth.thrawn01.org/v1.0
OS_REGION_NAME=DFW
opt-cmd=~/bin/get-customer-credentials --auth ${OS_AUTH_URL} --username ${opt.option}
```
With this configuration it is possible to access the prod environment with your credentials
```
hubble nova-prod list
```
or with a customers credentials
```
hubble nova-prod -o cust-tenant-name list
```

Because accessing customer credentials in a multi-tenant environment is very
vendor specific, The end user must provide the ```get-customer-credentials```
script. You can find an example of what this script might look like in the
[examples](https://github.com/thrawn01/hubble/blob/master/examples) directory


## How about running a command across multiple environments?
You can define a section in ```~/.hubblerc``` as a meta section.
The meta section tells hubble to source all the environment variables in the current
section, then source and run the command for each section listed in the meta list.

As an example
```
[cinder-all]
OS_AUTH_URL=http://usa.auth.thrawn01.org
cmd=/usr/bin/cinder
meta=['dfw', 'ord', 'lon']

[lon]
OS_AUTH_URL=http://lon.auth.thrawn01.org

[ord]
OS_USERNAME=ord-user
OS_PASSWORD=ord-password
OS_TENANT_NAME=000001
OS_REGION_NAME=ORD

[dfw]
OS_USERNAME=dfw-user
OS_PASSWORD=dfw-password
OS_TENANT_NAME=000001
OS_REGION_NAME=DFW
```

This configuration allows a user to specify a 'cinder-all' environment that will run
a cinder command in lon, ord and dfw environments
```
$ hubble cinder-all list
```

## What if multiple environments share some options, but not others?
Use section inheritance.

Example
```
[hubble]
OS_AUTH_URL=http://auth.thrawn01.org
OS_USERNAME=global-user

[preprod]
OS_USERNAME=preprod-user

[preprod-region1]
%inherit=preprod
OS_REGION_NAME=region1

[preprod-reigon2]
%inherit=preprod
OS_REGION_NAME=region2
```

This demonstrates nested inheritance; the `preprod-region2` section
will have options from `preprod` and the global `hubble` section.

### Multiple inheritance

Multiple inheritance is also supported; a single `%inherit` option
with multiple newline-separated values should be used if
desired. Option values are resolved in the order they are declared,
top to bottom, the values of earlier sections taking precedent over
later sections.

Example
```
[parent1]
spam = eggs

[parent2]
spam = bacon

[child]
%inherit =
  parent1
  parent2
```

The value of `spam` in the `child` section is `eggs`.

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
default-env=hubble
```
Notice the inclusion of the [hubble] section is optional. With this config we
can run hubble with our custom command remotely like so

```
ssh thrawn@my-host.com /usr/bin/hubble -e /path/to/custom-command
```

## Advanced Usage (Invocation Discovery)
With Invocation Discovery hubble chooses the command it will run by inspecting
the name of the program it was invoked as. This allows you to define a single
environment and have multiple command utilize the same environment config.

The following is an example with two environments *prod* and *staging*
```
[hubble]
# Variables defined here are included in all environments
OS_AUTH_URL=https://identity.api.rackspacecloud.com/v2.0/
OS_AUTH_SYSTEM=rackspace
NOVA_RAX_AUTH=1

# ------------------------------------
# Swiftly Stuff
# ------------------------------------
SWIFTLY_AUTH_URL=${OS_AUTH_URL}
SWIFTLY_AUTH_USER=${OS_USERNAME}
SWIFTLY_AUTH_KEY=USE_KEYRING['rackspace-api-key']

# ------------------------------------
# Credentials
# ------------------------------------
OS_PASSWORD=USE_KEYRING['rackspace-api-key']
OS_USERNAME=your-rackspace-username
OS_TENANT_NAME=123456

[staging]
OS_AUTH_URL=https://staging.mycloud.com/v2.0/
SWIFTLY_AUTH_URL=${OS_AUTH_URL}
OS_REGION_NAME=STAGING

[dfw]
OS_REGION_NAME=USA
```

Now link (ln -s) a command you want to use somewhere in your path that links back to hubble
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

In the following example we have *hubble*, *nova* and *cinder* installed in a
local virtualenv.  Here we don't want to override the use of ``nova`` so we
create a new link called ``supernova`` and tell ``hubble`` when it sees an
invocation as ``supernova`` run the ``nova`` command. By doing this you can
still run ``nova`` without hubble; preserving original behavior.

```
# Add the following section to your ~/.hubblerc file.
[hubble-commands]
swiftly=/home/username/virtualenv/python/bin/swiftly
supernova=/home/username/virtualenv/python/bin/nova
cinder=/home/username/virtualenv/python/bin/cinder

# Now create a link for supernova
$ ln -s /home/username/virtualenv/python/bin/hubble ~/bin/supernova

$ supernova prod list
+--------------------------------------+--------------+--------+----------------
| ID                                   | Name         | Status | Networks
+--------------------------------------+--------------+--------+----------------
| 54e2b87c-2850-11e2-a96f-e3cb6992c8ed | thrawn01.org | ACTIVE | public=10.26.18
+--------------------------------------+--------------+--------+----------------
```

## Complete list of available variables
* **${section}** - The name of the current environment (useful when using **meta**)
* **${cmd}** - Name of the command running for this environment
* **${opt-cmd}** - The value of the optional command for this environment
* **${env-cmd}** - The value of the env command for this environment
* **${opt.option}** - The argument passed in via the -o|--option command line argument
* **${opt.env}** - The environment name passed in as a command line argument
* **${opt.debug}** - 'True' if --debug was used on the command line else 'False'
