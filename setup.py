# -*- coding: utf-8 -*-
from setuptools import setup
from setuptools import find_packages

with open("requirements.txt") as requirements_file:
    install_requires = requirements_file.read().split("\n")

setup(
    name='MultiCoudRunner',
    version='0.0.2',
    description='Run experimentation on multiple clouds',
    author='Nicolas Herbaut',
    author_email='nicolas.herbaut@univ-grenoble-alpes.fr',
    url='https://nextnet.top',
     scripts=['mcc'],
    install_requires=install_requires,
    packages=find_packages()
)
