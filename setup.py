# -*- coding: utf-8 -*-

# Learn more: https://github.com/giangbui/setup.py

from setuptools import setup, find_packages


with open("README.rst") as f:
    readme = f.read()

with open("LICENSE") as f:
    license = f.read()

setup(
    name="APIConnection",
    version="0.1.0",
    description="APIConnection",
    package_data={
        # If any package contains *.txt files, include them:
        "": ["*.csv", "*.yaml"]
    },
    install_requires=[
        'requests==2.26.0',
        'facebook_business==11.0.0',
        'pandas==1.3.2',
        'lxml>=4.6.3',
        'xlwt>=1.3.0',
        'aiohttp==3.7.4.post0',
        'async-timeout==3.0.1',
        'attrs==21.2.0',
        'bcrypt==3.2.0',
        'cachetools==4.2.2',
        'certifi==2021.5.30',
        'cffi==1.14.6',
        'chardet==4.0.0',
        'charset-normalizer==2.0.6',
        'cryptography==3.4.8',
        'curlify==2.2.1',
        'facebook-business==11.0.0',
        'google-api-core==2.0.1',
        'google-api-python-client==2.20.0',
        'google-auth==2.1.0',
        'google-auth-httplib2==0.1.0',
        'google-auth-oauthlib==0.4.6',
        'googleapis-common-protos==1.53.0',
        'google-ads>=0.4.8',
        'httplib2==0.19.1',
        'idna==3.2',
        'multidict==5.1.0',
        'numpy==1.21.2',
        'oauth2client==4.1.3',
        'oauthlib==3.1.1',
        'paramiko==2.7.2',
        'protobuf>=3.18.1',
        'pyasn1==0.4.8',
        'pyasn1-modules==0.2.8',
        'pycountry==20.7.3',
        'pycparser==2.20',
        'PyNaCl==1.4.0',
        'pyparsing==2.4.7',
        'python-dateutil==2.8.2',
        'pytz==2021.1',
        'requests-oauthlib==1.3.0',
        'rsa==4.7.2',
        'six==1.16.0',
        'storage==0.0.4.3',
        'typing-extensions==3.10.0.2',
        'uritemplate==3.0.1',
        'urllib3==1.26.6',
        'yarl==1.6.3',
        'us==2.0.2',
        'pytrends==4.7.3',
        'twitter-ads==10.0.0'
    ],
    long_description=readme,
    author="Giang Bui",
    author_email="giangb.datapal@gmail.com",
    license=license,
    packages=find_packages(exclude=("tests", "docs")),
)
