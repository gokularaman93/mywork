# python3 scriptname.py -f {filepath} -s "${DC}${PRODUCT_KEYWORD}${VM_NUMBER}${VM_TYPE}-${MOUNTNAME}" -v 250

import sys
import argparse

def search_and_replace(file_path, substring, newMountValue):
    try:
        with open(file_path, "r") as file:
            lines = file.readlines()

        # Find the index of the line containing the specified substring
        index = next((i for i, line in enumerate(lines) if substring in line), None)

        if index is not None:
            # Find the index of the line containing "size_in_gbs" after the substring
            size_index = next((i for i, line in enumerate(lines[index:]) if "size_in_gbs" in line), None)

            if size_index is not None:
                # Print the values before replacement
                print(f"Before replacement - Substring: {substring}, old_size: {lines[index + size_index].strip()}")        
                # Replace the line containing "size_in_gbs" with "newsize"
                lines[index + size_index] = f"    size_in_gbs           = {newMountValue}\n"
                # Print the values after replacement
                print(f"After replacement - Substring: {substring}, new_size: size_in_gbs           = {newMountValue}")     

                # Write the modified lines back to the file
                with open(file_path, "w") as file:
                    file.writelines(lines)

                print("Replacement completed.")
            else:
                print("Error: 'size_in_gbs' not found after the specified substring.")
        else:
            print("Error: Substring not found in the file.")

    except FileNotFoundError:
        print(f"Error: File not found at path {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Create an argument parser
    parser = argparse.ArgumentParser(description="Search for lines containing a substring and replace 'size_in_gbs' with a new value.")
    parser.add_argument("-f", "--file", required=True, help="Path to the input file")
    parser.add_argument("-s", "--substring", required=True, help="Servername(Substring) to search for in each line")
    parser.add_argument("-v", "--newMountValue", required=True, help="New mount value to replace in the tfvars")

    # Parse the command-line arguments
    args = parser.parse_args()

    # Call the function with arguments
    search_and_replace(args.file, args.substring, args.newMountValue)


