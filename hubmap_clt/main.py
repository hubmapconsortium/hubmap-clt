#!/usr/bin/env python3

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
    parser = argparse.ArgumentParser(description='Hubmap Command Line Transfer', usage='''
        $ python main.py command
 
        List of commands:
            transfer    Transfer files and directories to local endpoint from information on a manifest file 
            login       Login to Globus via the default web browser
            whoami      Show information about the currently logged in user if logged in
 
    ''')
    subparsers = parser.add_subparsers()

    # Create Subparsers to give subcommands
    parser_transfer = subparsers.add_parser('transfer', help='Initiate Globus Transfer from Manifest File')
    parser_transfer.add_argument('manifest', type=str, help='Name of the manifest file including path if not located in'
                                                            ' the current directory')
    parser_login = subparsers.add_parser('login', help='Initiates a Globus Login Through the Default Web Browser')
    parser_whoami = subparsers.add_parser('whoami', help='Displays Information of the Currently Logged-In User')

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
    if endpoint_show_process.returncode !=0:
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
        line = x.split()
        if len(line) != 2:
            print(f"There are entries in {file_name} that contain more or fewer than 2 entries.\n"
                  f"Each line on the manifest must be the id for the dataset/upload, followed by its path and \n"
                  f"separated with a space. Example: HBM744.FNLN.846 /expr.h5ad")
            sys.exit(1)
        id_list.append(line[0].strip('"'))
        manifest_dict[line[0].strip('"')] = line[1].strip('"')

    # send the list of uuid's to the ingest webservice to retrieve the endpoint uuid and relative path.
    #r = requests.get(f"{INGEST_DEV_WEBSERVICE_URL}/datasets/rel-path", json=id_list)
    #path_json = r.json()
    path_json = [
        {
            "entity_type": "Dataset",
            "globus_endpoint_uuid": "ff1bd56e-2e65-4ec9-86fa-f79422884e96",
            "id": "02809d1028ddf24a3d96cddd28ada2c7",
            "rel_path": "/consortium/University of California San Diego TMC/02809d1028ddf24a3d96cddd28ada2c7"
        },
        {
            "entity_type": "Dataset",
            "globus_endpoint_uuid": "2b82f085-1d50-4c93-897e-cd79d77481ed",
            "id": "HBM825.NZXG.447",
            "rel_path": "/f1178f3de96e62fe54093f6cdcee753c"
        }
    ]
    # Create a list of the unique endpoint uuid's. For each entry in the list, a separate call to globus transfer
    # must be made
    unique_globus_endpoint_ids = []
    # Add the particular path from manifest_dict into path_dict
    for each in path_json:
        each["specific_path"] = manifest_dict[each['id'].strip('"')].strip('"')
        if each["globus_endpoint_uuid"] not in unique_globus_endpoint_ids:
            unique_globus_endpoint_ids.append(each["globus_endpoint_uuid"])
    for each in unique_globus_endpoint_ids:
        endpoint_list = []
        for item in path_json:
            if item["globus_endpoint_uuid"] == each:
                endpoint_list.append(item)
        batch_transfer(endpoint_list, each, local_id)


def batch_transfer(endpoint_list, globus_endpoint_uuid, local_id):
    temp = tempfile.TemporaryFile(mode='w+t')
    for each in endpoint_list:
        line = ""
        is_directory = False
        full_path = each["rel_path"] + each["specific_path"]
        if os.path.basename(full_path) == "":
            is_directory = True
        if is_directory is False:
            line = f'"{full_path}"' + f" {os.path.basename(full_path)}"
        else:
            slash_index = full_path.rstrip('/').rfind("/")
            local_dir = full_path[slash_index:].rstrip('/')
            # right now, local_dir is might be a trailing slash when it shouldn't be
            line = f'"{full_path}"' + f" {local_dir} --recursive"
        temp.write(line)
    temp.seek(0)
    globus_transfer_process = subprocess.Popen(["globus", "transfer", globus_endpoint_uuid, local_id, "--batch"],
                                               stdout=subprocess.PIPE)
    globus_transfer = globus_transfer_process.communicate()[0].decode('utf-8')
    if globus_transfer_process.returncode != 0:
        print(globus_transfer)
        sys.exit(1)

def whoami(args):
    subprocess.run(["globus", "whoami"])


def login(args):
    subprocess.run(["globus", "login", "--force"])


def base_case(args, parser):
    parser.print_help()


if __name__ == '__main__':
    main()
