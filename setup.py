#!/bin/env python
# -*- coding: utf8 -*-

from distribute_setup import use_setuptools
use_setuptools()

from setuptools import setup, find_packages

version = "0.12.0"

setup(
    name="RepBot",
    version=version,
    description="IRC Reputation bot",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Twisted",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
    ],
    keywords="irc reputation bot",
    author="Matt Soucy",
    author_email="msoucy@csh.rit.edu",
    url="http://github.com/msoucy/RepBot",
    license="MIT License",
    packages=find_packages(
    ),
    scripts=[
        "distribute_setup.py",
    ],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "twisted",
    ],
    #TODO: Deal with entry_points
    #entry_points="""
    #[console_scripts]
    #pythong = pythong.util:parse_args
    #"""
)