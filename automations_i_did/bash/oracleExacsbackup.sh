#!/bin/bash
set -eo pipefail

DB_SCRIPT=$(readlink -f "${0}")
DB_SCRIPT_DIR=$(dirname "$DB_SCRIPT")

declare -a REQUIRED_ENV_VARS=(
    DATABASE_USER
    DATABASE_TABLESPACE_NAME
    DB_HOST
    DB_PORT
    DB_SERVICE
    # DB_ADMIN_USER
    # DB_ADMIN_PASSWORD
    # DATABASE_DUMP_FILE
    DATABASE_DUMP_DIR
	WO
)
ERRORS=""
# Verify required environment variables are set before continuing.
for VAR in "${REQUIRED_ENV_VARS[@]}"; do
    if [ -z "${!VAR:-}" ]; then
        ERRORS+="!ERROR: Required environment variable \"$VAR\" is not set !!!\n"
    fi
done

echo "Checking for sqlplus"
if ! sqlplus -v; then
    ERRORS+="!ERROR: sqlplus -v did not work. Is sqlplus available?\n"
fi

echo "Checking for expdp"
if ! which expdp; then
    ERRORS+="!ERROR: expdp command not found. Is Data Pump installed?\n"
fi

# Check if there are any errors
if [ -n "$ERRORS" ]; then
    echo -e "$ERRORS" >&2
    echo "****************************************************************"
    echo 'FAILED.  Exiting due to errors !!!'
    echo "****************************************************************"
    exit 1
fi


export PL_CONNECT_STRING="abc/"******"@$DB_HOST:$DB_PORT/$DB_SERVICE" 
export SPOOL_FILE=./logerror.spool
export EXL=statistics
export CDATE=`date +%s`

# Create  Data Pump Directory
echo "Creating Data Pump Directory ${DATABASE_DUMP_DIR} for exporting DB dump"
sqlplus -s "${PL_CONNECT_STRING}" <<EOF || { echo "!ERROR: Failed to execute SQL script for DATA PUMP Directory"; exit 1; }
    SPOOL ${SPOOL_FILE}
    WHENEVER SQLERROR EXIT SQL.SQLCODE
    CREATE OR REPLACE DIRECTORY DPUMP_EXP AS '${DATABASE_DUMP_DIR}';
EOF
STATUS=$?
if [ ${STATUS} -ne 0 ]; then
    echo "!ERROR: Failed to create data pump at ${DATABASE_DUMP_DIR}"
    echo "Check the DB Connectivity and permissions.. It failed even before triggering the backup operation..."
    cat ${SPOOL_FILE}
    exit 1
else
    echo "Datapump Directory at ${DATABASE_DUMP_DIR} created successfully";
fi

# Function to format LIST_OF_TABLES with schema prefix
format_table_list() {
    local formatted_tables=""
    IFS=',' read -ra tables <<< "$LIST_OF_TABLES"
    for table in "${tables[@]}"; do
        if [ -n "$formatted_tables" ]; then
            formatted_tables+=","
        fi
        formatted_tables+="${DATABASE_USER}.${table}"
    done
    echo "$formatted_tables"
}

# Set the log file name
LOGFILE="expdp_${DATABASE_TABLESPACE_NAME}_${WO}_${CDATE}.log"

# Run expdp with logging
if [ -n "${LIST_OF_TABLES}" ]; then
    # Format LIST_OF_TABLES with schema prefix
    formatted_tables=$(format_table_list)
    echo "Exporting specific tables: ${formatted_tables}";
    
    # Export specific tables
    expdp_output=$(expdp ${PL_CONNECT_STRING} \
        directory=DPUMP_EXP \
        dumpfile=expdp_custom_${DATABASE_TABLESPACE_NAME}_${WO}_${CDATE}_%U.dmp \
        logfile=${LOGFILE} \
        tables=${formatted_tables} \
        PARALLEL=16 \
        exclude=${EXL} \
        cluster=N \
        metrics=y ) || { echo "!ERROR: Failed to execute SQL script for DATA PUMP Export" >&2; exit 1; }
else
    # Export the entire schema
    echo "Exporting the entire schema"
    expdp_output=$(expdp ${PL_CONNECT_STRING} \
        directory=DPUMP_EXP \
        dumpfile=expdp_${DATABASE_TABLESPACE_NAME}_${WO}_${CDATE}_%U.dmp \
        logfile=${LOGFILE} \
        schemas=${DATABASE_USER} \
        PARALLEL=16 \
        exclude=${EXL} \
        cluster=N \
        metrics=y ) || { echo "!ERROR: Failed to execute SQL script for DATA PUMP Export" >&2; exit 1; }
fi

#Sucessfull status check from logs
if echo "$expdp_output" | grep -q "Encrypted data has been stored unencrypted in dump file set"; then
    echo "Looking for successfully loaded message now"
    
    # Extract next 10 lines & Check if "successfully loaded/unloaded" appears in those 10 lines
    NEXT_FEW_LINES=$(echo "$expdp_output" | awk '/Encrypted data has been stored unencrypted in dump file set/ {found=1; next} found && count<10 {print; count++}')

    if echo "$NEXT_FEW_LINES" | grep -q "successfully loaded/unloaded"; then
        echo "Data Pump operation EXPDP completed successfully."
    else
        echo "!ERROR: No success confirmation in expdp output!"
        exit 1
    fi
fi

echo "Oracle DB Backup completed successfully"
exit 0
