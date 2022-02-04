# hubmap-clt

---

A command line interface to download multiple files and directories from the Globus file transfer service.

### Overview

The HuBMAP Command-Line Transfer uses the Globus cli to transfer files from a manifest file. This file contains the ID (UUID or HuBMAP ID) and the path to the specific file or directory to be downloaded. 

### Installing  and Using hubmap-clt

The HuBMAP Command-Line Transfer requires a local Globus Connect Personal Endpoint to be connected. The user must have an account with Globus and be logged into both the local endpoint as well as the Globus command line interface. Hubmap-clt is available through PyPi and can be installed with:

```bash
pip3 hubmap-clt
```

hubmap-clt requirements can be found [here](requirements.txt)

Consult <a href="https://software.docs.hubmapconsortium.org/">Installing hubmap-clt</a> and Consult <a href="https://software.docs.hubmapconsortium.org/">Using hubmap-clt</a> for full documentation on getting started with hubmap-clt as we as information on the required Globus software. 

### Building and Publishing hubmap-clt

<a href="https://pypi.org/project/setuptools/">SetupTools</a> and <a href="https://pypi.org/project/wheel/">Wheel</a> is required to build the clt distribution. <a href="https://pypi.org/project/twine/">Twine</a> is required to publish to Pypi

Build the distribution directory with: 

```bash
python3 setup.py sdist bdist_wheel
```

from within the hubmap-clt project directory

To publish, from inside the project directory, run:

```bash
twine upload dist/*
```

A prompt to enter login information to the hubmap Pypi account will appear

### Files

This code contains:

**\_\_main\_\_.py**: Contains the implementation of the command-line interface as well as the logic for the clt.

Inside of **\_\_main\_\_.py** are the following classes:

* whoami: Informs the user if they are logged into Globus
* login: Initiates a Globus login using the default web browser
* transfer: Sets up a transfer into the user's downloads file. Accepts a single required argument. This argument is the name of a manifest file which contains information on the files to be downloaded
* batch_transfer: Calls globus batch transfer for each source collection represented in the manifest file. 






