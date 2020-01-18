"""Setup."""

from setuptools import find_packages
from setuptools import setup

setup(
    name='txdnsdoh',
    use_incremental=True,
    packages=find_packages('.'),
    setup_requires=['incremental'],
    install_requires=['incremental',
                      'click',
                      'Twisted[http2,tls]',
                      'dns',
                      'PyYAML'],
    entry_points={
        'console_scripts': [
            'txdnsdoh=txdnsdoh.main:main'
        ],
    },
    url='https://github.com/jcollie/txdnsdoh',
    author='Jeffrey C. Ollie',
    author_email='jeff@ocjtech.us'
)
