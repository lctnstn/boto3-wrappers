from setuptools import setup, find_packages

import boto3_wrappers

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='boto3_wrappers',
    long_description="Helpful wrappers for boto3.",
    long_description_content_type="text/markdown",
    install_requires=requirements,
    author='Nathan Lichtenstein',
    author_email='nathan@lctnstn.com',
    url='https://github.com/lctnstn/boto3-wrappers',
    version=boto3_wrappers.version,
    description='Wrapper classes for boto3.',
    packages=find_packages(exclude=('tests', 'docs')),
)
