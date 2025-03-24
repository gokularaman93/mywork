import json
import argparse
import time
import boto3
import csv
import sys
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(format="%(levelname)s: %(asctime)s %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def read_input_file(file_path: str) -> Tuple[List[Dict[str, str]], List[List[str]]]:
    valid_input_entries = []
    skipped_input_entries = []
    
    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as csv_file:
            csv_reader = csv.reader(csv_file)
            for line in csv_reader:
                logger.info(f"Reading line {line}")
                if len(line) == 2:
                    entry = {
                        'region_name': line[0].strip(),
                        'db_cluster_identifier': line[1].strip()
                    }
                    valid_input_entries.append(entry)
                else:
                    logger.warning(f'This line is ignored: {line}')
                    skipped_input_entries.append(line)
                    
        return valid_input_entries, skipped_input_entries
        
    except FileNotFoundError:
        logger.error(f"CSV file not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error reading CSV file: {str(e)}")
        sys.exit(1)

def get_cluster_details(db_cluster_identifier: str, region_name: str) -> Dict[str, str]:
    try:
        rds_client = boto3.client('rds', region_name=region_name)
        response = rds_client.describe_db_clusters(
            DBClusterIdentifier=db_cluster_identifier
        )
        
        if not response.get('DBClusters'):
            logger.error(f"No cluster found with identifier {db_cluster_identifier} in region {region_name}")
            return {}
            
        cluster = response['DBClusters'][0]
        return {
            'db_cluster_identifier': db_cluster_identifier,
            'region_name': region_name,
            'engine_version': cluster.get('EngineVersion', 'Unknown'),
            'db_cluster_arn': cluster.get('DBClusterArn', 'Unknown')
        }
    except rds_client.exceptions.ClientError as e:
        logger.error(f"🚨Error fetching details for {db_cluster_identifier} in region {region_name}: {str(e)}")
        return {}

def check_engine_versions_for_bgd(cluster_details, min_touch_version, max_dont_touch_version):
    goodforbgd = []
    badforbgd = []

    # Extract major.minor from min/max versions
    min_major, min_minor = map(int, min_touch_version.split(".")[:2])
    max_major, max_minor = map(int, max_dont_touch_version.split(".")[:2])

    for cluster_id, details in cluster_details.items():
        try:
            version = details["engine_version"]
            major, minor = map(int, version.split(".")[:2])

            # validate engine version to identify goodforbgd
            if ((major == min_major and minor >= min_minor) or  # Match min limit (e.g., 13.12)
                (major > min_major and major < max_major)):     #or    # In range (e.g., 14.x)
                # (major == max_major and minor < max_minor)):    # Match max limit (e.g., < 15.8) just skip is major version is same as target version major
                
                goodforbgd.append(details)
            else:
                details["status"] = f"Cluster {cluster_id} with version {version} is NOT eligible for BGD (must be >= {min_touch_version} or < {max_dont_touch_version})"
                badforbgd.append(details)
                logger.info(f"Cluster {cluster_id} with version {version} is NOT eligible for BGD (must be >= {min_touch_version} or < {max_dont_touch_version})")

        except (ValueError, IndexError) as e:
            logger.error(f"Error parsing version for cluster {cluster_id}: {str(e)}")
            details["error"] = "Invalid engine version"
            badforbgd.append(details)

    return goodforbgd, badforbgd

def trigger_blue_green_deployment(goodforbgd):
    global target_engine_version
    deployments = {}

    for cluster in goodforbgd:
        rds_client = boto3.client("rds", region_name=cluster["region_name"])
        #deployments = {cluster["db_cluster_identifier"]: cluster for cluster in goodforbgd}
        
        db_cluster_identifier = cluster["db_cluster_identifier"]
        db_cluster_arn = cluster["db_cluster_arn"]
        bgd_deployment_name = f"{db_cluster_identifier}-bgd"
        # region_name = cluster["region_name"]

        try:
            logger.info(f"🚀 Creating Blue-Green Deployment: {bgd_deployment_name} for cluster: {db_cluster_identifier}")

            config = {
                "BlueGreenDeploymentName": bgd_deployment_name,
                "Source": db_cluster_arn,
                "TargetEngineVersion": target_engine_version,
                "TargetDBParameterGroupName": "default-aurora-postgresql15",
                "TargetDBClusterParameterGroupName": "default-aurora-postgresql15"
            }
            logger.info(f"📝 Blue-Green Deployment Configuration:\n{json.dumps(config, indent=4)}")

            response = rds_client.create_blue_green_deployment(**config)

            # Start Blue-Green Deployment
            """
            response = rds_client.create_blue_green_deployment(
                BlueGreenDeploymentName=bgd_deployment_name,
                SourceDBClusterIdentifier=db_cluster_arn,
                TargetEngineVersion=target_engine_version,
                TargetDBParameterGroupName='default-aurora-postgresql15',
                TargetDBClusterParameterGroupName='default-aurora-postgresql15'
            )
            """

            # Extract deployment ID and status from the response
            bgd_deployment_id = response["BlueGreenDeployment"]["BlueGreenDeploymentIdentifier"]
            bgd_deployment_status = response["BlueGreenDeployment"]["Status"]

            # Store in deployments
            deployments[db_cluster_identifier] = cluster  # Store goodforbgd details
            deployments[db_cluster_identifier]["bgd_deployment_id"] = bgd_deployment_id
            deployments[db_cluster_identifier]["bgd_deployment_status"] = bgd_deployment_status

            logger.info(f"✅ Blue-Green Deployment '{bgd_deployment_id}' created successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error triggering Blue-Green Deployment for {db_cluster_identifier}: {str(e)}")
            deployments[db_cluster_identifier] = {"error": str(e)}

    return deployments

def get_bgd_status(rds_client, bgd_deployment_id):
    try:
        response = rds_client.describe_blue_green_deployments(
            BlueGreenDeploymentIdentifier=bgd_deployment_id
        )
        return response["BlueGreenDeployments"][0]["Status"]
    except Exception as e:
        logger.error(f"❌ Error fetching BGD status for {bgd_deployment_id}: {str(e)}")
        return "ERROR"
def get_target_member_arn(rds_client, bgd_deployment_id):
    try:
        response = rds_client.describe_blue_green_deployments(
            BlueGreenDeploymentIdentifier=bgd_deployment_id
        )
        target_member_arn = response["BlueGreenDeployments"][0]["SwitchoverDetails"][0]["TargetMember"]
        return target_member_arn
    except Exception as e:
        logger.error(f"❌ Error fetching TargetMember ARN for {bgd_deployment_id}: {str(e)}")
        return None

def get_engine_version(rds_client, cluster_arn):
    try:
        response = rds_client.describe_db_clusters(
            DBClusterIdentifier=cluster_arn         #.split(":")[-1]
        )
        return response["DBClusters"][0]["EngineVersion"]
    
    except Exception as e:
        logger.error(f"❌ Error fetching engine version for {cluster_arn}: {str(e)}")
        return None

def switchover_bgd(rds_client, bgd_deployment_id):
    try:
        logger.info(f"🔄 Triggering Switchover for '{bgd_deployment_id}'...")
        rds_client.switchover_blue_green_deployment(
            BlueGreenDeploymentIdentifier=bgd_deployment_id,
            SwitchoverTimeout=300
        )
        logger.info(f"✅ Switchover triggered for '{bgd_deployment_id}'")
        return True
    except Exception as e:
        logger.error(f"❌ Error triggering switchover for {bgd_deployment_id}: {str(e)}")
        return False
    
#Continuously monitors Blue-Green Deployments and triggers switchover when ready.
def monitor_and_switchover(deployments):
    global target_engine_version
    while True:
        all_completed = True

        for cluster_id, details in deployments.items():
            rds_client = boto3.client("rds", region_name=details["region_name"])
            bgd_deployment_id = details.get("bgd_deployment_id")

            if not bgd_deployment_id:
                pass  # Skip if no deployment ID

            # Fetch latest BGD status
            bgd_status = get_bgd_status(rds_client, bgd_deployment_id)
            deployments[cluster_id]["bgd_deployment_status"] = bgd_status
            logger.info(f"📌 {cluster_id} - BGD Status: {bgd_status}")

            # Continue loop untill SWITCHOVER_COMPLETED
            if bgd_status in ["PROVISIONING", "AVAILABLE", "SWITCHOVER_IN_PROGRESS"]:
                all_completed = False
                pass

            # If status is AVAILABLE, check engine version before switchover
            if bgd_status == "AVAILABLE":
                cluster_arn = get_target_member_arn(rds_client, bgd_deployment_id)

                if cluster_arn:
                    engine_version = get_engine_version(rds_client, cluster_arn)

                    if engine_version == target_engine_version:
                        # Trigger Switchover
                        switchover_bgd(rds_client, bgd_deployment_id)
                    else:
                        deployments[cluster_id]["bgd_deployment_status"] = "DIFFERENT ENGINE VERSION IN GREEN"
                        logger.warning(f"⚠️ {cluster_id} - Engine version is {engine_version}, expected {target_engine_version}!")

        # Save updated deployments to a JSON file
        with open("deployments.json", "w") as f:
            json.dump(deployments, f, indent=4)

        # Print latest status for visibility
        logger.info(json.dumps(deployments, indent=4))

        # If all deployments have completed, exit loop
        if all_completed:
            logger.info("🎉 All deployments have completed! Exiting loop.")
            break

        # Sleep for 5 minutes before checking again
        logger.info("⏳ Sleeping for 5 minutes before next status check...")
        time.sleep(5 * 60)

def main(valid_input_entries: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    # Initialize cluster_details dictionary
    cluster_details = {}
    
    # Process each entry
    for entry in valid_input_entries:
        db_cluster_identifier = entry['db_cluster_identifier']
        region_name = entry['region_name']
        
        # Get cluster details
        details = get_cluster_details(db_cluster_identifier, region_name)
        
        if details:
            cluster_details[db_cluster_identifier] = details
            logger.info(f"Successfully processed cluster: {db_cluster_identifier}")
        else:
            logger.warning(f"Skipping cluster {db_cluster_identifier} due to errors")
    
    return cluster_details

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create Blue Green Deployment for Aurora RDS cluster')
    parser.add_argument('--file', '-f', required=True, help='Path to the input CSV file with cluster,region')
    parser.add_argument('--engine_version', '-e', required=True, help='Target engine version for BGD')
    parser.add_argument('--min_touch_version', '-m', required=True, help='Minimum version for which you need to trigger BGD')
    args = parser.parse_args()
    
    #Assign variable from input arguments
    target_engine_version = args.engine_version
    min_touch_version = args.min_touch_version
    max_dont_touch_version = target_engine_version

    # Read and validate input CSV entries - skip or pass
    valid_input_entries, skipped_input_entries = read_input_file(args.file)
    logger.info(f"✅Final Valid Input Entries:\n{json.dumps(valid_input_entries, indent=4)}")
    logger.info(f"⚠️ Final Skipped Input Entries: \n{json.dumps(skipped_input_entries, indent=4)}")

    # Extract all related cluster details of the valid inputs to proceed further
    cluster_details = main(valid_input_entries)
    logger.info(f"🔥Final Valid Input Cluster Details:\n{json.dumps(cluster_details, indent=4)}")

    #validate engine version to determine if its good for bgd or not
    goodforbgd, badforbgd = check_engine_versions_for_bgd(cluster_details, min_touch_version, max_dont_touch_version)
    logger.info(f"✅ Good for BGD Deployment:\n{json.dumps(goodforbgd, indent=4)}")
    logger.warning(f"⛔️ Bad for BGD Deployment:\n{json.dumps(badforbgd, indent=4)}")

    #trigger bgd using goodforbgd list
    deployments = trigger_blue_green_deployment(goodforbgd)
    logger.info(f"🔥 Triggered Blue-Green Deployment Status:\n{json.dumps(deployments, indent=4)}")

    #sleep for 30 minutes to get the deployment status
    logger.info("⏳ Sleeping for 30 minutes to allow deployments to stabilize...")
    time.sleep(30 * 60)
    logger.info("✅ Resuming execution after 30 minutes of sleep.")

    #for bgdstatus in bgd_deployment_status is AVAILABLE, then validate and proceed with network switching
    monitor_and_switchover (deployments)