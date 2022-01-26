#!/usr/bin/env python3

import shlex
import argparse
import os.path
import subprocess
import sys
import requests
import tempfile
from os.path import exists

# Constants
INGEST_DEV_WEBSERVICE_URL = "https://ingest-api.dev.hubmapconsortium.org/"

def main():
    # Configure the top level Parser
    parser = argparse.ArgumentParser(prog='hubmap-clt', description='Hubmap Command Line Transfer', usage='''
        $ hubmap-clt command
 
        List of commands:
            transfer    Transfer files and directories to local endpoint from information on a manifest file 
            login       Login to Globus via the default web browser
            whoami      Show information about the currently logged in user if logged in
 
    ''')
    subparsers = parser.add_subparsers()

    # Create Subparsers to give subcommands
    parser_transfer = subparsers.add_parser('transfer', help='Initiate Globus Transfer from a Manifest Text File')
    parser_transfer.add_argument('manifest', type=str, help='Name of the Manifest File Including the Path if it is not '
                                                            'Located in the Current Directory')
    parser_login = subparsers.add_parser('login', help='Initiates a Globus Login Through the Default Web Browser')
    parser_whoami = subparsers.add_parser('whoami', help='Displays Information of the Currently Logged-In User. If not '
                                                         'Logged in, User will be Prompted to Log-In with "hubmap-clt '
                                                         'login"')

    # Assign subparsers to their respective functions
    parser_transfer.set_defaults(func=transfer)
    parser_login.set_defaults(func=login)
    parser_whoami.set_defaults(func=whoami)
    parser.set_defaults(func=base_case)

    # Parse the arguments and call appropriate functions
    args = parser.parse_args()
    if len(sys.argv) == 1:
        args.func(args, parser)
    else:
        args.func(args)


# This is the primary function of the hubmap_clt. Accepts a single argument which is the path/name of a manifest file.
# A transfer is initiated from the uuid's and paths located within the file.
def transfer(args):
    # Verify existence of the manifest file
    file_name = args.manifest
    if not exists(file_name):
        print(f"The file {file_name} cannot be found. You may need to include the path to the file. Example: \n"
              f"/Documents/manifest.txt \n")
        sys.exit(1)

    # Obtain the local-id of the endpoint
    local_id_process = subprocess.Popen(["globus", "endpoint", "local-id"], stdout=subprocess.PIPE)
    local_id = local_id_process.communicate()[0].decode('utf-8')
    if local_id_process.returncode != 0:
        print(local_id)
        sys.exit(1)

    # Verify that the endpoint is connected
    endpoint_show_process = subprocess.Popen(["globus", "endpoint", "show", local_id], stdout=subprocess.PIPE)
    endpoint_show = endpoint_show_process.communicate()[0].decode('utf-8')
    if endpoint_show_process.returncode != 0:
        print(endpoint_show)
        sys.exit(1)
    endpoint_connected = False
    for line in endpoint_show.splitlines():
        if line.startswith("GCP Connected"):
            colon_index = line.find(":") + 1
            substring = line[colon_index:].strip()
            if substring == "True":
                endpoint_connected = True
    if endpoint_connected is False:
        print(f"The endpoint {local_id} is not active. Please consult the Globus Connect documentation  \n "
              f"to start the local endpoint. Once the endpoint is connected, try again")
        sys.exit(1)

    # Open the manifest file and verify the contents
    f = open(file_name, "r")
    # A list of the ID's is necessary to send to the ingest webservice. The dictionary is used to map the output of the
    # webservice back to the manifest entry it came from.
    id_list = []
    manifest_dict = {}
    for x in f:
        if x != "":
            try:
                line = shlex.split(x)
            except ValueError:
                print(f"There was a problem with one of the entries in {file_name} such as a hanging quotation mark."
                      f"Please review {file_name} and check for any formatting errors")
                sys.exit(1)
            if len(line) != 2:
                print(f"There are entries in {file_name} that contain more or fewer than 2 entries.\n"
                      f"Each line on the manifest must be the id for the dataset/upload, followed by its path and \n"
                      f"separated with a space. Example: HBM744.FNLN.846 /expr.h5ad")
                sys.exit(1)
            id_list.append(line[0].strip('"'))
            manifest_dict[line[0].strip('"')] = line[1].strip('"')
    if len(id_list) == 0:
        print(f"File {file_name} contained nothing or only blank lines. \n"
              f"Each line on the manifest must be the id for the dataset/upload, followed by its path and \n"
              f"separated with a space. Example: HBM744.FNLN.846 /expr.h5ad")
        sys.exit(1)
    # send the list of uuid's to the ingest webservice to retrieve the endpoint uuid and relative path.
    r = requests.post(f"{INGEST_DEV_WEBSERVICE_URL}entities/file-system-rel-path", json=id_list)
    path_json = r.json()
    # Create a list of the unique endpoint uuid's. For each entry in the list, a separate call to globus transfer
    # must be made
    unique_globus_endpoint_ids = []
    # Add the particular path from manifest_dict into path_dict
    for each in path_json:
        each["specific_path"] = manifest_dict[each['id']].strip('"')
        if each["globus_endpoint_uuid"] not in unique_globus_endpoint_ids:
            unique_globus_endpoint_ids.append(each["globus_endpoint_uuid"])
    for each in unique_globus_endpoint_ids:
        endpoint_list = []
        for item in path_json:
            if item["globus_endpoint_uuid"] == each:
                endpoint_list.append(item)
        batch_transfer(endpoint_list, each, local_id)


def batch_transfer(endpoint_list, globus_endpoint_uuid, local_id):
    temp = tempfile.NamedTemporaryFile(mode='w+t')
    for each in endpoint_list:
        is_directory = False
        # We use "/" rather than os.sep because the file system for globus always uses "/"
        full_path = each["rel_path"] + "/" + each["specific_path"].lstrip("/")
        if os.path.basename(full_path) == "":
            is_directory = True
        if is_directory is False:
            line = f'"{full_path}"' + f" {os.path.basename(full_path)} \n"
        else:
            slash_index = full_path.rstrip('/').rfind("/")
            local_dir = full_path[slash_index:].rstrip('/')
            local_dir.replace("/", os.sep)
            line = f'"{full_path}"' + f" {local_dir} --recursive \n"
        temp.write(line)
    temp.seek(0)
    # if running in a linux/posix environment, default folder will be ~/Downloads.
    # if not, don't specify the target directory. Will need to add implementation for other OS's
    if os.name == 'posix':
        globus_transfer_process = subprocess.Popen(["globus", "transfer", globus_endpoint_uuid,
                                                    f"{local_id}:~/Downloads", "--batch", temp.name],
                                                   stdout=subprocess.PIPE)
    else:
        globus_transfer_process = subprocess.Popen(["globus", "transfer", globus_endpoint_uuid,
                                                    f"{local_id}", "--batch", temp.name],
                                                   stdout=subprocess.PIPE)
    globus_transfer = globus_transfer_process.communicate()[0].decode('utf-8')
    if globus_transfer_process.returncode != 0:
        print(globus_transfer)
        sys.exit(1)
    print(globus_transfer)
    temp.close()


def whoami(args):
    # Makes the command "globus whoami". If the user is logged in, their identity will be printed. If they are not
    # Logged in, they will be prompted to use the command "hubmap-clt login"
    whoami_process = subprocess.Popen(["globus", "whoami"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    whoami_show = whoami_process.communicate()[0].decode('utf-8')
    if whoami_process.returncode == 0:
        print(whoami_show)
    else:
        print(f"MissingLoginError: Missing login for auth.globus.org, please run \n\n \thubmap-cli login\n")


def login(args):
    # Forces a login to globus through the default web browser
    subprocess.run(["globus", "login", "--force"])


def base_case(args, parser):
    # If no sub-commands are given, the help and usage information will be displayed
    parser.print_help()


if __name__ == '__main__':
    main()
