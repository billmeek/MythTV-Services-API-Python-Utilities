This is here to keep the dist directory when all files in it get deleted.
And as a HOWTO for installation:

The following installs version 0.1.3 for use by python2 and python3:

``` sh
sudo -H pip2 install dist/mythtv_services_api-0.1.3-py2-none-any.whl
sudo -H pip3 install dist/mythtv_services_api-0.1.3-py3-none-any.whl
```
Alternatively, without cloning the project, these would do the same.
```
pip install https://raw.githubusercontent.com/billmeek/MythTVServicesAPI/master/dist/mythtv_services_api-0.1.3-py2-none-any.whl
pip install https://raw.githubusercontent.com/billmeek/MythTVServicesAPI/master/dist/mythtv_services_api-0.1.3-py3-none-any.whl
```
