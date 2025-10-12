#!/usr/bin/env python
from setuptools import setup, find_packages


setup(
    name='qrl',
    version='0.1.0',
    description='Quantum Resistant Ledger',
    author='QRL Team',
    author_email='info@theqrl.org',
    url='https://github.com/yourusername/QRL',
    packages=find_packages(),
    install_requires=[
        'pycryptodomex>=3.6.6',
        'pyqrllib>=1.2.0',
        'pyqryptonight>=0.10.26',
        'pyqrandomx>=0.2.0',
        'PyYAML>=5.1',
        'click>=7.0',
        'colorlog>=3.1.0',
        'grpcio>=1.12.1',
        'grpcio-tools>=1.12.1',
        'protobuf>=3.6.0',
        'pyopenssl>=17.5.0',
        'six>=1.11.0',
        'statistics>=1.0.3.5',
        'twisted>=18.7.0',
        'service_identity>=17.0.0',
    ],
    entry_points='''
        [console_scripts]
        qrl=qrl.cli:main
    ''',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
)