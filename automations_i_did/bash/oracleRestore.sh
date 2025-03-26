#!/bin/bash
###################################################################

set -eo pipefail

DB_SCRIPT=$(readlink -f "${0}")
DB_SCRIPT_DIR=$(dirname "$DB_SCRIPT")

declare -a REQUIRED_ENV_VARS=(
    DATABASE_USER
    DATABASE_TABLESPACE_NAME
    DATABASE_SCHEMA
    DB_HOST
    DB_PORT
    DB_SERVICE
    # DB_ADMIN_USER
    # DB_ADMIN_PASSWORD
    DATABASE_DUMP_FILE
    DATABASE_DUMP_DIR
    TABLE_EXISTS_ACTION
    DROP_CONTENTS
)

################################################################
# Validate required parameters before proceeding with execution
################################################################
ERRORS=""

# Check for required environment variables
for VAR in "${REQUIRED_ENV_VARS[@]}"; do
    if [ -z "${!VAR:-}" ]; then
        ERRORS+="!ERROR: Required environment variable \"$VAR\" is not set !!!\n"
    fi
done

# Check for sqlplus availability
echo "Checking for sqlplus"
if ! sqlplus -v &>/dev/null; then
    ERRORS+="!ERROR: sqlplus -v did not work. Is sqlplus available?\n"
fi

# Check for impdp availability
echo "Checking for impdp"
if ! which impdp &>/dev/null; then
    ERRORS+="!ERROR: which impdp did not work. Is impdp available?\n"
fi

# Check if there are any errors
if [ -n "$ERRORS" ]; then
    echo -e "$ERRORS" >&2
    echo "****************************************************************"
    echo 'FAILED.  Exiting due to errors !!!'
    echo "****************************************************************"
    exit 1
fi

echo "****************************************************************"
echo "All required inputs are verified. sqlplus and impdp are available."
echo "****************************************************************"

export PL_CONNECT_STRING="abc/****@$DB_HOST:$DB_PORT/$DB_SERVICE" 
export SPOOL_FILE=./logerror.spool
export CDATE=$(date +%s)

#################################
########### DB REFRESH ##########
#################################

# Function to generate a drop script for a schema
generate_drop_script() {
    local database_schema=$1
    local drop_script="drop_${database_schema}_${CDATE}.sql"

    echo "Generating drop script for schema ${database_schema}"

    sqlplus -s "${PL_CONNECT_STRING}" <<EOF > "${drop_script}" || { echo "!ERROR: Failed to generate drop script for ${database_schema}" >&2; exit 1; }
        set echo off head off verify off feedb off pages 0 long 10000 longchunk 10000 trimspool on lines 2000 timing off term off
        spool ${drop_script}
        select 'drop ' || object_type || ' "' || owner || '"."' || object_name || '";'
        from dba_objects
        where object_type in ('TABLE', 'VIEW', 'PACKAGE', 'SEQUENCE', 'PROCEDURE', 'FUNCTION', 'INDEX') 
        and owner = '${database_schema}';
        spool off;
EOF

    # Ensure drop script is not empty
    if [ ! -s "${drop_script}" ]; then
        echo "!ERROR: Drop script ${drop_script} is empty. No objects found for schema ${database_schema}." >&2
        exit 1
    fi

    echo "Drop script ${drop_script} generated successfully."

    # Execute the drop script
    echo "Executing drop script: ${drop_script} on database ${database_schema}"

    sqlplus -s "${PL_CONNECT_STRING}" <<EOF || { echo "!ERROR: Failed to execute drop script: ${drop_script}" >&2; exit 1; }
        @${drop_script}
EOF

    echo "Drop script executed successfully, schema ${database_schema} contents dropped."
}

# Function to format LIST_OF_TABLES with schema prefix
format_table_list() {
    local formatted_tables=""
    IFS=',' read -ra tables <<< "$LIST_OF_TABLES"
    for table in "${tables[@]}"; do
        if [ -n "$formatted_tables" ]; then
            formatted_tables+=","
        fi
        formatted_tables+="${DATABASE_SCHEMA}.${table}"
    done
    echo "$formatted_tables"
}

# Function to restore database dump
restore_db_dump() {
    local tablespace_name=$1
    local schema_name=$2
    local dump_file=$3
    local log_file=$4
    local table_exists_action=$5
    local additional_params=$6
    local table_list=$7

    echo "Restoring DB Dump from file ${dump_file} using impdp"

    if [ -n "${table_list}" ]; then
        # Format LIST_OF_TABLES with schema prefix
        formatted_tables=$(format_table_list)
        echo "Exporting specific tables: ${formatted_tables}";

        # Restore only specific tables if provided
        impdp ${PL_CONNECT_STRING} \
              directory=DPUMP_RES \
              dumpfile="${dump_file}" \
              logfile="${log_file}" \
              tables="${formatted_tables}" \
              TABLE_EXISTS_ACTION="${table_exists_action}" \
              PARALLEL=16 \
              metrics=y \
              cluster=N \
              transform=disable_archive_logging:y || { echo "!ERROR: Data Pump import failed!" >&2; exit 1; }
              #${additional_params} 2>&1) 
    else
        # Restore entire schema if no specific tables are provide
        #Its going to be full restore of same backup or diff backup(Refresh)
        impdp_output=$(impdp ${PL_CONNECT_STRING} \
              directory=DPUMP_RES \
              dumpfile="${dump_file}" \
              logfile="${log_file}" \
              TABLE_EXISTS_ACTION="${table_exists_action}" \
              PARALLEL=16 \
              metrics=y \
              cluster=N \
              transform=disable_archive_logging:y \
              ${additional_params} ) || { echo "!ERROR: Full schema import failed!" >&2; exit 1; }

        # Check if the output contains the specific ORA-00001 error message
        if echo "$impdp_output" | grep -q "ORA-00001: unique constraint"; then
            echo "Detected: Unique Constraint Error. Retrying with TABLE_EXISTS_ACTION=SKIP..."
            
            # Re-run the impdp command with TABLE_EXISTS_ACTION set to "SKIP"
            impdp ${PL_CONNECT_STRING} \
                directory=DPUMP_RES \
                dumpfile="${dump_file}" \
                logfile="${log_file}" \
                TABLE_EXISTS_ACTION="SKIP" \
                PARALLEL=16 \
                metrics=y \
                cluster=N \
                transform=disable_archive_logging:y \
                ${additional_params} || { echo "!ERROR: Retrying with TABLE_EXISTS_ACTION=SKIP failed!" >&2; exit 1; }
        fi
    fi
    echo "DB Dump restored successfully."
}

# Function to create Data Pump directory
create_data_pump_directory() {
    local directory=$1

    echo "Creating Data Pump Directory ${directory}"
    sqlplus -s "${PL_CONNECT_STRING}" <<EOF || { echo "!ERROR: Failed to create Data Pump directory at ${directory}" >&2; exit 1; }
        SPOOL  ${SPOOL_FILE}
        WHENEVER SQLERROR EXIT SQL.SQLCODE
        CREATE OR REPLACE DIRECTORY DPUMP_RES AS '${directory}';
EOF

    echo "Data Pump Directory at ${directory} created successfully."
}

################################
##### MAIN ####################
################################
# Drop contents of target if set to true
if [ "${DROP_CONTENTS}" == "yes" ]; then
    echo "DROP_CONTENTS is set to yes...Hence proceeding..."
    generate_drop_script "${DATABASE_SCHEMA}"
else
    echo "DROP_CONTENTS is set to no. Skipping schema drop."
fi


# Define schema and tablespace remapping if DB_REFRESH is true
if [ "${DB_REFRESH}" == "true" ]; then
    ADDITIONAL_PARAMS="remap_schema=${SOURCE_DATABASE_SCHEMA}:${DATABASE_SCHEMA} remap_tablespace=${SOURCE_DATABASE_TABLESPACE_NAME}:${DATABASE_TABLESPACE_NAME}"
else
    ADDITIONAL_PARAMS="schemas=${DATABASE_SCHEMA}"
fi


# Create Data Pump directory
create_data_pump_directory "${DATABASE_DUMP_DIR}"

# Set log file name
LOG_FILE="IMPDP_${DATABASE_TABLESPACE_NAME}_${WO}_${CDATE}.log"

#restore
restore_db_dump "${DATABASE_TABLESPACE_NAME}" "${DATABASE_SCHEMA}" "${DATABASE_DUMP_FILE}" "${LOG_FILE}" "${TABLE_EXISTS_ACTION}" "${ADDITIONAL_PARAMS}" "${LIST_OF_TABLES}"

echo "Oracle DB Restore completed successfully"
exit 0