"""Setup for MythTV Services API"""

import os
from setuptools import setup


def read(readme_filename):
    """Exists to allow reading the README.md file"""
    return open(os.path.join(os.path.dirname(__file__), readme_filename)).read()

setup(
    name='mythtv_services_api',
    py_modules=['send', 'utilities'],
    packages=['mythtv_services_api'],
    version='0.0.3',
    license='GNU/GPLv3',
    description='MythTV Services API tools.',
    long_description=read('README.md'),
    author='Bill Meek',
    classifiers=[
        # 3 - Alpha, 4 - Beta, 5 - Production/Stable
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3'
    ],
    url=['https://www.mythtv.org/wiki/Python_API_Examples']
)
