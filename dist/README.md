This is here to keep the dist directory when all files in it get deleted.
And as a HOWTO for installation:

In the following, change the version to the one you actually want,
which is likely the latest.

The following installs version 0.1.x for use by python2 and python3
when this project is cloned:

``` sh
sudo -H pip2 install dist/mythtv_services_api-0.1.x-py2-none-any.whl
sudo -H pip3 install dist/mythtv_services_api-0.1.x-py3-none-any.whl
```
Alternatively, without cloning the project, these would do the same.
```
pip install https://raw.githubusercontent.com/billmeek/MythTVServicesAPI/master/dist/mythtv_services_api-0.1.x-py2-none-any.whl
pip install https://raw.githubusercontent.com/billmeek/MythTVServicesAPI/master/dist/mythtv_services_api-0.1.x-py3-none-any.whl
```
