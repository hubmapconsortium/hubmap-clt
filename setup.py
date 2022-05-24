from setuptools import setup
from io import open
from os import path

import pathlib
HERE = pathlib.Path(__file__).parent

README = (HERE / "README.md").read_text()

setup(
    name='hubmap-clt',
    description='A command line interface to download multiple files and directories from Globus file transfer '
                'service using a manifest file.',
    version='1.1.2',
    packages=['hubmap_clt'],
    python_requires='>=3.6',
    entry_points='''
        [console_scripts]
        hubmap-clt=hubmap_clt.__main__:main
    ''',
    author="Hubmap",
    author_email="api-developers@hubmapconsortium.org",
    long_description=README,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent"
    ],
    include_package_data=True,
    install_requires=[
        "certifi>=2021.10.8",
        "charset-normalizer>=2.0.10",
        "idna>=3.3",
        "requests>=2.27.1",
        "urllib3>=1.26.8",
        "globus-cli>=3.1.4",
    ],
    keywords=[
        "HuBMAP CLT",
        "python"
    ]
)
