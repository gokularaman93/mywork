#!/bin/bash
echo "******************************     INPUT PROVIDED        ***************************************"
echo "VM_NAME: $VM_NAME"
echo "MOUNT_NAME: $MOUNT_NAME"
echo "MOUNT_SIZE: $MOUNT_SIZE"
echo "************************************************************************************************"

# Check if the Terraform Plan file exists
if [ ! -f "$terraformOutputFile" ]; then
    echo "Terraform output file not found: $terraformOutputFile"
    exit 1
fi

# Global Variables
terraformActionsFound=false
prevLine=""
matched_line_plus_1=""
matched_line_plus_2=""

#######################################################################
#Check if the Plan is same as Plan: 1 to add, 1 to change, 1 to destroy
# or
#Check if the Plan is same as Plan: 0 to add, 1 to change, 0 to destroy
########################################################################
CAPTURED_PLAN=$(grep "Plan:" "$terraformOutputFile")
add=$(grep "Plan:" "$terraformOutputFile" | awk '{print $2 $3 $4}')
change=$(grep "Plan:" "$terraformOutputFile" | awk '{print $5 $6 $7}')
destroy=$(grep "Plan:" "$terraformOutputFile" | awk '{print $8 $9 $10}')


#OTHER REGIONS
if [[ "$add" == "1t"* ]] || [[ "$change" == "1t"* ]] || [[ "$destroy" == "1t"* ]]; then
    export TF_ANALYZE="check_for_add_modify_delete"
fi

#SPECFIC REGION
if [[ "$add" == "0t"* ]] || [[ "$change" == "1t"* ]] || [[ "$destroy" == "0t"* ]]; then
    export TF_ANALYZE="check_for_change"
fi

#EXIT if TF_ANALYZE is something else.
if [[ -z "${TF_ANALYZE}" ]]; then
    echo "TF_ANALYZE is empty or not set"
    echo "Failing the Pipeline as the Basic Terraform Plan doesn't match with the Actual Executed TF Plan"
    echo "BASIC PLAN   : Plan: 1 to add, 1 to change, 1 to destroy."
    echo "(OR)"
    echo "BASIC PLAN   : Plan: 0 to add, 1 to change, 0 to destroy."
    echo "CAPTURED PLAN: ${CAPTURED_PLAN}"
    exit 1
fi

##########################
#Analyse Modify and Replacement Resources
###########################
# Read the file line by line
while IFS= read -r line; do
    # Check if the line contains "Terraform will perform the following actions:"
    if [[ $line == *"Terraform will perform the following actions:"* ]]; then
        terraformActionsFound=true
    fi
    
    # Check if terraform actions are found and the line starts with "~ " or "-/+ "
    if [ "$terraformActionsFound" = true ] && [[ $line == "  ~ "* || $line == "-/+ "* ]]; then
        echo "*********************"
        echo "$prevLine"
        echo "$line"
        
        #Fail if there are any modifications other than the servers we provided in input
        echo "$prevLine" | grep "${VM_NAME}-${MOUNT_NAME}-blk01" >/dev/null
        if [[ $? != 0 ]]; then
            echo "ERROR: The BLOCK VOLUME UPDATION is about to happen for a VM different than the user input VM"
            exit 1
        fi

        if [[ $line == "  ~ "* ]]; then
            echo "$prevLine" | grep "oci_core_volume.block_volume" >/dev/null
            if [[ $? != 0 ]]; then
                echo "$prevLine"
                echo "ERROR: Some other resource is getting modified instead of oci_core_volume.block_volume"
                exit 1
            fi
            #get the next two lines
            read -r matched_line_plus_1
            read -r matched_line_plus_2
            echo "$matched_line_plus_2"
            new_storage_value_in_terraform=$(echo "$matched_line_plus_2" | awk -F'"' '{print $(NF-1)}')
            echo "New storage value in Terraform: $new_storage_value_in_terraform"

            #Fail if the storage value in TF is not the same as the user input
            if [[ ${MOUNT_SIZE} != ${new_storage_value_in_terraform} ]]; then
                echo "ERROR: The STORAGE SIZE is not the same as the user input value"
                exit 1
            fi
        fi

        #TF_ANALYZE="check_for_add_modify_delete" Run this only for "BASIC PLAN   : Plan: 1 to add, 1 to change, 1 to destroy."
        if [[ "${TF_ANALYZE}" == "check_for_add_modify_delete" ]] && [[ "$line" == "-/+ "* ]]; then
            echo "$prevLine" | grep "oci_core_volume_backup_policy_assignment" >/dev/null
            if [[ $? != 0 ]]; then
                echo "$prevLine"
                echo "ERROR: Some other resource other than oci_core_volume_backup_policy_assignment is getting replaced"
                exit 1
            fi
        fi
    fi
    prevLine="$line"
done < "$terraformOutputFile"

