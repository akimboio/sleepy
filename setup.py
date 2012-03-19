#!/usr/bin/python

import os
from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="Sleepy",
    version="0.9.6",
    author="Adam Haney",
    author_email="adam.haney@retickr.com",
    description=("""A RESTful library that is used at retickr on top"""\
                    """of Django we use it for a few apis internally."""),
    license="Closed",
    keywords="JSON RESTful",
    url="http://about.retickr.com",
    packages=['sleepy'],
    long_description=read('README'),
    install_requires=[
        "Django>=1.3",
        ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Topic :: Framework",
        "License :: OSI Approved :: Closed",
        ]
)
