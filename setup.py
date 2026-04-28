#!/usr/bin/env python

from setuptools import setup
import configparser
import os
import re


def read(fname):
    path = os.path.join(os.path.dirname(__file__), fname)
    with open(path, encoding='utf-8') as handle:
        return handle.read()


config = configparser.ConfigParser()
config.read_file(open('tryton.cfg', encoding='utf-8'))
info = dict(config.items('tryton'))

for key in ('depends', 'extras_depend', 'xml'):
    if key in info:
        info[key] = info[key].strip().splitlines()

major_version, minor_version = 6, 0
requires = []

for dep in info.get('depends', []):
    if dep == 'health':
        requires.append('gnuhealth == %s' % (info.get('version')))
    elif dep.startswith('health_'):
        health_package = dep.split('_', 1)[1]
        requires.append('gnuhealth_%s == %s' % (
            health_package, info.get('version')))
    else:
        if not re.match(r'(ir|res|webdav)(\W|$)', dep):
            requires.append(
                'trytond_%s >= %s.%s, < %s.%s' % (
                    dep, major_version, minor_version,
                    major_version, minor_version + 1))

requires.append('trytond >= %s.%s, < %s.%s' % (
    major_version, minor_version, major_version, minor_version + 1))

setup(
    name='z_wizard_patients',
    version=info.get('version', '0.0.1'),
    description='GNU Health quick patient and party creation wizard',
    long_description=read('README.rst'),
    author='ALFA Custom',
    author_email='',
    url='',
    download_url='',
    package_dir={'trytond.modules.z_wizard_patients': '.'},
    packages=[
        'trytond.modules.z_wizard_patients',
        'trytond.modules.z_wizard_patients.wizard',
    ],
    package_data={
        'trytond.modules.z_wizard_patients': (
            info.get('xml', [])
            + info.get('translation', [])
            + ['tryton.cfg', 'README.rst', 'view/*.xml',
               'locale/*.po', 'data/messages/*.xml', 'wizard/*.xml']
        ),
    },
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Plugins',
        'Framework :: Tryton',
        'Intended Audience :: Developers',
        'Intended Audience :: Healthcare Industry',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Natural Language :: Spanish',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
    ],
    license='GPL-3',
    install_requires=requires,
    zip_safe=False,
    entry_points="""
    [trytond.modules]
    z_wizard_patients = trytond.modules.z_wizard_patients
    """,
    test_suite='tests',
    test_loader='trytond.test_loader:Loader',
)
