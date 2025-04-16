aws --region $AWS_REGION cloudformation create-stack \
    --stack-name ${prefix}-${customername}-poc-${identifier} \
    --template-body file:///${WORKSPACE}/cfn/aurora-rds.json \
    --parameters \
    ParameterKey=DBClusterName,ParameterValue=${prefix}-${customername}-poc-${identifier} \
    ParameterKey=DBPassword,ParameterValue=$rds_password \
    ParameterKey=DBName,ParameterValue=$rds_dbname \
    ParameterKey=VpcId,ParameterValue=$managementvpc \
    ParameterKey=DBInstanceClass,ParameterValue=$InstanceSize \
    ParameterKey=DBClusterParameterGroupName,ParameterValue=$DBClusterParameterGroupName \
    ParameterKey=DBParameterGroup,ParameterValue=$DBParameterGroup \
    ParameterKey=securitygroupID,ParameterValue=$rds_poc_sg_id \
    ParameterKey=EnvironmentName,ParameterValue=poc \
    ParameterKey=CustomerName,ParameterValue=$customerservicename \
    ParameterKey=Subnets,ParameterValue="\"$managementvpc_subnets\""