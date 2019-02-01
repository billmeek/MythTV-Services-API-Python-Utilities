NOTE: This package is now a part of MythTV v30.0 and above.  No more
maintenance will be done here. This page will go away in the future.

Existing v30 users should change their import stataments similar
to the following examples:

    from MythTV.services_api import send as api
    from MythTV.services_api import utilities as util

To avoid confusion, delete any other versions of this package.
Try:
.
	sudo --set-home pip2 uninstall --yes $(PACKAGE)
	sudo --set-home pip3 uninstall --yes $(PACKAGE)

Those building from source must be sure that Python Bindings
are selected in ./configure.



See the README.md under dist for installation options.

For complete help, try this:
```
$ python
>>> from MythTV.services_api import send as api, utilities as util
>>> help(api)
>>> help(util)
```
