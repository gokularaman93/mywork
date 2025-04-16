"""
adding a python script to automatically replace the value in the files based on the input csv file passed reducing manual efforts.
Input File : Comma Separated of ServerName,owner,product_line,environment,application,product_name,customer_name
"""

import json
import argparse
import logging
import os
import sys
import csv
from typing import Tuple, Dict, List
import subprocess

#logging
logging.basicConfig(format="%(levelname)s: %(asctime)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def read_input_file(file_path: str) -> Tuple[List[Dict[str, str]], List[List[str]]]:
    
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as csv_file:
            csv_reader = csv.reader(csv_file)
            for line in csv_reader:
                if len(line) == 7:
                    entry = {
                        "servernamexxxxx"            : line[0].strip(),
                        "owner"         : line[1].strip(),
                        "product_line"  : line[2].strip(),
                        "environment"   : line[3].strip(),
                        "application"   : line[4].strip(),
                        "product_name"  : line[5].strip(),
                        "customer_name" : line[6].strip(),
                        # "region"        : line[7].strip()
                    }
                    formatted_entries.append(entry)
                else: 
                    logger.warning("This line is ignored: " + line)
                    skipped_entries.append(line)
                
        return formatted_entries, skipped_entries

    except Exception as e:
        logger.error("ERROR: " + str(e))


def find_tfvars_files_containing_servername(servername, repodir):
    matched_files = []

    #find matching files with the servername/clustername
    for root, _, files in os.walk(repodir):
        for file in files:
            if file.endswith(".tfvars"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        if servername in f.read():
                            matched_files.append(file_path)
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")

    if matched_files:
        logger.info(f"Matching files for {servername} found")
        logger.info(matched_files)
        print("*"*40)
    else:
        logger.warning(f"No matching .tfvars files found for {servername} in {repodir}")
        sys.exit()

    return matched_files

def replace_values(matched_files, input):
    for file in matched_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            updated = False

            for entry in input:
                # last_key = list(entry.keys())[-1]
                for i in range(len(lines)):
                    for key, value in entry.items():
                        if key in lines[i]:
                            # if key == last_key:
                                # lines[i] = f'      "{key}"   = "{value}"\n'
                            # else:
                                lines[i] = f'      "{key}"   = "{value}",\n'
                            
                            # logger.info(f"Updated in {file}: {lines[i].strip()}")
                                updated = True  

            # Write the modified content back to the same file
            if updated:
                with open(file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                logger.info(f"File {file} updated successfully.")
            else:
                logger.info(f"No matches found in {file}. No changes made.")

        except Exception as e:
            logger.error(f"Error processing {file}: {e}")




    
def find_file_and_replace_values(input, repodir):
    for item in input:
        servername = item["servernamexxxxx"][:-1]
        matched_files = find_tfvars_files_containing_servername(servername, repodir)

        if matched_files:
            for file in matched_files:
                # logger.info(f"Found matching file: {file}")
                replace_values(matched_files, [item])
        else:
            logger.warning(f"No matching files found for {servername}")
        
        





#main
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Read CSV and replace values in TF Code')
    parser.add_argument('--file', '-f', required=True, help='Input CSV File')
    parser.add_argument('--path', '-p', required=True, help='Repo path where the files should be replaced with values')
    args = parser.parse_args()

    formatted_entries = []
    skipped_entries = []
    formatted_entries, skipped_entries = read_input_file(args.file)
    logger.info(json.dumps(formatted_entries, indent=4))

    #for servername in formatted entries, find the matching files inside the repo 
    #and replace values with the matching line if line starts/contains with key, replace with "k" = "v"
    find_file_and_replace_values(formatted_entries, args.path)


