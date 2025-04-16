"""
Description: Adding automated Terraform plan checker for newly added tags
"""
import os
import argparse

# Strings to search for in files
SEARCH_STRINGS = [
    "~ size_in_gbs",
    "~ shape_config",
    "No changes. Your infrastructure matches the configuration."
    "~ launch_options"
    "~ network_type"
]
#instances
INSTANCE_TARGET_LINE = ".oci_core_instance.instance will be updated in-place"
NO_CHANGES_IN_INSTANCE_LINE = "# (6 unchanged blocks hidden)"
#block volumes
TARGET_LINE = ".oci_core_volume.block_volume will be updated in-place"
EXPECTED_NINTH_LINE = "# (13 unchanged attributes hidden)"
POLICY_ASSIGNMENT_LINE = "oci_core_volume_backup_policy_assignment.volume_backup_policy_assignment[0] must be replaced"

def find_matching_files(folder):
    for root, _, files in os.walk(folder):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    for string in SEARCH_STRINGS:
                        if string in content:
                            print(f"🚨 {string} : Match found: {file_path}")
            except Exception as e:
                print(f"\u26A0\uFE0F Could not read file {file_path}: {e}")


def block_volume_plan(folder_path):
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    target_indices = [i for i, line in enumerate(lines) if TARGET_LINE in line]

                    if len(target_indices) in [6, 18]:
                        valid = True
                        for i in target_indices:
                            ninth_valid = i + 9 < len(lines) and lines[i + 9].strip() == EXPECTED_NINTH_LINE
                            seventh_valid = i + 7 < len(lines) and lines[i + 7].strip() == EXPECTED_NINTH_LINE

                            if not ninth_valid and not seventh_valid:
                                valid = False
                                break

                        if not valid:
                            print(f"⚠️ 9th or 7th line didn't match in BLOCK VOLUME updation - Check: {file_path}")
            except Exception as e:
                print(f"\u26A0\uFE0F Could not read file {file_path}: {e}")


def block_volume_plan_inplace(folder_path):
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        if os.path.isfile(file_path) and "NLB" not in file_path:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    target_indices = [i for i, line in enumerate(lines) if TARGET_LINE.strip() in line.strip()]

                    match_count = len(target_indices)
                    if match_count not in [6, 18]:
                        print(f"📧 Found {match_count} matches instead of [6 or 18] for BLOCK VOLUME 'will be updated in-place' — Check: {file_path}")
            except Exception as e:
                print(f"⚠️ Could not read file {file_path}: {e}")

def instance_plan_inplace(folder_path):
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        if os.path.isfile(file_path) and "NLB" not in file_path:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    target_indices = [i for i, line in enumerate(lines) if INSTANCE_TARGET_LINE.strip() in line.strip()]

                    match_count = len(target_indices)
                    if match_count not in [1, 3]:
                        print(f"🚨 Found {match_count} matches for INSTANCE instead of [1 or 3] 'will be updated in-place' — Check: {file_path}")
            except Exception as e:
                print(f"⚠️ Could not read file {file_path}: {e}")

def noshapechanges_inplan_valdiation(folder_path):
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        if os.path.isfile(file_path) and "NLB" not in file_path:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    target_indices = [i for i, line in enumerate(lines) if NO_CHANGES_IN_INSTANCE_LINE.strip() in line.strip()]

                    match_count = len(target_indices)
                    if match_count == 0:
                        print(f"🚨 Some VM Shape Change is about to happen — Check: {file_path}")
            except Exception as e:
                print(f"⚠️ Could not read file {file_path}: {e}")

def block_volume_plan_policy(folder_path):
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        if os.path.isfile(file_path) and "NLB" not in file_path:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    target_indices = [i for i, line in enumerate(lines) if POLICY_ASSIGNMENT_LINE.strip() in line.strip()]

                    match_count = len(target_indices)
                    if match_count not in [6, 18]:
                        print(f"🚨 Found {match_count} matches for backup policy assignment instead of [6 or 18] — Check: {file_path}")
            except Exception as e:
                print(f"⚠️ Could not read file {file_path}: {e}")


def find_plan_output(folder):
    expected_plans = [
        "Plan: 6 to add, 7 to change, 6 to destroy.",
        "Plan: 18 to add, 21 to change, 18 to destroy."
    ]

    for root, _, files in os.walk(folder):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if not any(plan in content for plan in expected_plans):
                            print(f"🚨 Mandatory TF Plan Output(6,7,6) or (18,21,18) not found in {file_path}")
            except Exception as e:
                print(f"Could not read file: {file_path} - {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Validate Terraform Plan Files")
    parser.add_argument('--path', '-p', required=True, help='Path to directory containing Terraform plan files')
    args = parser.parse_args()

    print("***********************")
    print("***********************")
    find_matching_files(args.path)
    print("***********************")
    print("***********************")
    block_volume_plan(args.path)
    print("***********************")
    print("***********************")
    block_volume_plan_inplace(args.path)
    print("***********************")
    print("***********************")
    block_volume_plan_policy(args.path)
    print("***********************")
    print("***********************")
    instance_plan_inplace(args.path)
    print("***********************")
    print("***********************")
    find_plan_output(args.path)
    print("***********************")
    print("***********************")
    noshapechanges_inplan_valdiation(args.path)
