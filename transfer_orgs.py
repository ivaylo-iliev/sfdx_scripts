#!/usr/bin/python
import subprocess
import json
import os.path
import fnmatch
import argparse
from sys import argv
from concurrent.futures import ThreadPoolExecutor

parser = argparse.ArgumentParser(description='Usage:')
requiredNamed = parser.add_argument_group('Required arguments')
requiredNamed.add_argument('-b', '--backup', type=str, help='Perform credentials backup to a specified path')
requiredNamed.add_argument('-r', '--restore', type=str, help='Perform credentials restore from a specified path')

if not len(argv) >= 3:
	parser.print_help()
	exit(0)

args = parser.parse_args()

if args.backup != None and args.restore != None:
	parser.print_help()
	exit(0)

def read_stored_credentials():
	p = subprocess.run(["sfdx", "force:auth:list",  "--json"], capture_output=True, text=True)
	return json.loads(p.stdout)

def write_to_file(directory, username, alias):
	p = subprocess.run(["sfdx", "force:org:display", "-u", username, "--verbose", "--json"], capture_output=True, text=True)
	org_data_as_json = json.loads(p.stdout)

	file_name = os.path.join(directory, 'sfdx_{}.txt'.format(alias))
	f = open(file_name, "w")
	f.write(org_data_as_json["result"]["sfdxAuthUrl"])
	f.close()

def store_credentials(output_directory):
	if not os.path.isdir(output_directory):
		os.makedirs(output_directory)

	credentials_data = read_stored_credentials()
	with ThreadPoolExecutor(max_workers=50) as executor:
		for value in credentials_data['result']:
			
			alias = None
			if value["alias"] != None and value["alias"] != "":
				alias = value["alias"]
			else:
				alias = value["id"]

			executor.submit(write_to_file, output_directory, value["username"], value["alias"])

def restore_credentials(input_directory):
	if not os.path.isdir(input_directory):
		print('Specified directory {} not found.'.format(input_directory))
		exit(1)

	files = fnmatch.filter(os.listdir(input_directory), 'sfdx_*.txt')
	if len(files) <= 0:
		print('No authorized orgs backup found. Exiting.')
		exit(0)

	with ThreadPoolExecutor(max_workers=50) as executor:
		for file in files:
			alias = file.split('_')[1].split('.')[0]
			full_path = os.path.join(input_directory, file)
			future = executor.submit(read_from_file, full_path, alias)

def read_from_file(full_path, alias):
	subprocess.run(["sfdx", "force:auth:sfdxurl:store", "-f", full_path, "-a", alias ], capture_output=False)

if args.backup != None:
	print('You are about to perform backup of all sfdx connections.')
	answer = input('Do you want to continue? (Y/N): ')
	if answer.lower() in ['y', 'yes']:
		store_credentials(args.backup)

if args.restore != None:
	print('You are about to perform restore of previously backed up sfdx connections.')
	answer = input('Do you want to continue? (Y/N): ')
	if answer.lower() in ['y', 'yes']:
		restore_credentials(args.restore)