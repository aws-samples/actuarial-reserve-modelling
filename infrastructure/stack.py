import os
from aws_cdk import (
    CfnOutput,
    Duration,
    Fn,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_fsx as fsx,
    aws_s3 as s3,
    aws_iam as iam,
    aws_batch as batch,
    aws_s3_deployment as s3_deploy,
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as targets,
    Stack,
)
from constructs import Construct
from aws_cdk.aws_ecr_assets import DockerImageAsset


os.chdir('../')
cwd = os.getcwd()
account=os.environ["CDK_DEFAULT_ACCOUNT"]
region=os.environ["CDK_DEFAULT_REGION"]


class CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = self.create_aws_actuary_vpc()
        self.bucket = self.create_actuary_calculating_bucket()
        self.compute_env_sg = self.create_compute_environment_sg()
        self.asset = self.build_docker_image()
        self.fsx_sg = self.create_fsx_security_group()
        self.fsx_ingress_rule_self  = self.create_fsx_ingress_from_self()
        self.fsx_ingress_rule_batch = self.create_fsx_ingress_from_batch()
        self.fsx_file_system = self.create_fsx_file_system()
        self.lambda_function_calculate = self.calculate_average_reserves()
        self.launch_template = self.create_launch_template()
        self.compute_env_ecs_instance_role = self.create_compute_environemnt_ecs_instance_role()
        self.compute_environment_instance_profile = self.create_compute_environment_instance_profile()
        self.compute_environment_service_role = self.create_compute_environment_service_role()
        self.batch_compute_environment = self.create_batch_compute_environment()
        self.job_queue = self.create_batch_job_queue()
        self.job_definition = self.create_batch_job_definition()
        self.event_rule = self.create_batch_job_completed_event_rule()
        self.add_s3_permission_to_lambda()
        self.add_fsx_permissions_to_lambda()
        self.outputs()
    

    # create S3 bucket
    def create_actuary_calculating_bucket(self):
        bucket = s3.Bucket(
            self,
            "actuary-calculating-bucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # deploy policies to S3 bucket
        s3_deploy.BucketDeployment(self, "DeployPolicies",
                                    sources=[s3_deploy.Source.asset(os.path.join(cwd, "policies"))],
                                    destination_bucket=bucket,
                                    destination_key_prefix="input",
                                    exclude=["*.DS_Store"])

        return bucket
    

    # lambda function to kick off data repository export task and sum up the reserves across workers
    def calculate_average_reserves(self):
        lambda_function_calculate = lambda_.Function(
            self,
            "sumReservesFunction",
            code=lambda_.Code.from_asset(os.path.join(cwd, "lambda_code")),
            handler="calculate_average_reserves.lambda_handler",
            runtime=lambda_.Runtime.PYTHON_3_9,
            timeout=Duration.seconds(180),
            environment={
                "FSX_SYSTEM_ID": self.fsx_file_system.file_system_id,
                "FSX_PATH": "output/",
                "S3_BUCKET_NAME": self.bucket.bucket_name
            }
        )

        return lambda_function_calculate


    # add s3 permissions to lambda function
    def add_s3_permission_to_lambda(self):
        lambda_function = self.lambda_function_calculate

        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:*"
                ],
                resources=[self.bucket.bucket_arn,
                           self.bucket.bucket_arn + "/*"]
            )
        )

        return lambda_function
    

    # add fsx permissions to lambda function
    def add_fsx_permissions_to_lambda(self):
        lambda_function = self.lambda_function_calculate

        lambda_function.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "fsx:*"
                ],
                resources=["*"]
            )
        )

        return lambda_function


    # create vpc
    def create_aws_actuary_vpc(self):
        vpc = ec2.Vpc(self, "ActuaryCalculatingVPC",
                      ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
                      max_azs=1,
                      enable_dns_hostnames=True,
                      enable_dns_support=True,
                      subnet_configuration=[
                            ec2.SubnetConfiguration(
                                name="PrivateSubnet", 
                                cidr_mask=17, 
                                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                            ec2.SubnetConfiguration(
                                name="PublicSubnet", 
                                cidr_mask=17,
                                subnet_type=ec2.SubnetType.PUBLIC)],
                     nat_gateways=1,
                     nat_gateway_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC))
                          
        return vpc
    

    # create fsx security group
    def create_fsx_security_group(self):
        fsx_sg = ec2.SecurityGroup(
            self,
            "FsxSecurityGroup",
            vpc=self.vpc,
            description="Allow all outbound",
            allow_all_outbound=True
            )
        
        return fsx_sg


    # create fsx security group from self
    def create_fsx_ingress_from_self(self):
        fsx_ingress_rule_from_self = ec2.CfnSecurityGroupIngress(
            self, "FSxFileSystemSecurityGroupFromSelf",
            description="Allow inbound from self",
            ip_protocol="tcp",
            from_port=988,
            to_port=1023,
            group_id=self.fsx_sg.security_group_id,
            source_security_group_id=self.fsx_sg.security_group_id
        )

        return fsx_ingress_rule_from_self


    # create fsx security group from compute environment
    def create_fsx_ingress_from_batch(self):
        fsx_ingress_rule_batch = ec2.CfnSecurityGroupIngress(
            self, "FSxFileSystemSecurityGroupFromComputeEnvironment",
            ip_protocol="tcp",
            from_port=988,
            to_port=1023,
            group_id=self.fsx_sg.security_group_id,
            source_security_group_id=self.compute_env_sg.security_group_id
        )

        return fsx_ingress_rule_batch
    

    # create fsx file system
    def create_fsx_file_system(self):
        fsx_file_system = fsx.LustreFileSystem(
            self,
            "FsxFileSystem",
            storage_capacity_gib=1200,
            vpc=self.vpc,
            vpc_subnet=self.vpc.private_subnets[0],
            security_group=self.fsx_sg,
            removal_policy=RemovalPolicy.DESTROY,
            lustre_configuration=fsx.LustreConfiguration(
                deployment_type=fsx.LustreDeploymentType.SCRATCH_2,
                auto_import_policy=fsx.LustreAutoImportPolicy.NEW_CHANGED_DELETED,
                import_path="".join([self.bucket.s3_url_for_object(), "/input"]),
                export_path="".join([self.bucket.s3_url_for_object(), ""])
            )
        )
        
        return fsx_file_system
    
    
    # create Amazon EC2 Launch Template for the compute environment instances
    def create_launch_template(self):

        __user_data = """MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="==MYBOUNDARY=="

--==MYBOUNDARY==
Content-Type: text/cloud-config; charset="us-ascii"

runcmd:
- amazon-linux-extras install -y lustre2.10
- mkdir -p /fsx
- mount -t lustre -o noatime,flock {}.fsx.{}.amazonaws.com@tcp:/{} /fsx

--==MYBOUNDARY==--""".format(self.fsx_file_system.file_system_id, region, self.fsx_file_system.mount_name)

        launch_template = ec2.CfnLaunchTemplate(
            self,
            "LaunchTemplate",
            launch_template_name=f"{self.stack_name}-LaunchTemplate",
            launch_template_data=ec2.CfnLaunchTemplate.LaunchTemplateDataProperty(
                user_data=Fn.base64(__user_data))
        )
        
        return launch_template


    # create compute environemnt sg
    def create_compute_environment_sg(self):
        compute_env_sg = ec2.SecurityGroup(
            self,
            "ComputeEnvironmentSecurityGroup",
            vpc=self.vpc,
            description="Allow all outbound",
            allow_all_outbound=True
        )

        return compute_env_sg


    # create Compute Environment ECS Instance Role
    def create_compute_environemnt_ecs_instance_role(self):
        compute_env_ecs_instance_role = iam.Role(
            self,
            "ComputeEnvironmentEcsInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )

        compute_env_ecs_instance_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2ContainerServiceforEC2Role"))

        return compute_env_ecs_instance_role
    

    # create Compute Environment Instance Profile
    def create_compute_environment_instance_profile(self):
        compute_environment_instance_profile = iam.CfnInstanceProfile(
            self,
            "ComputeEnvironmentInstanceProfile",
            roles=[self.compute_env_ecs_instance_role.role_name]
        )

        return compute_environment_instance_profile
    

    # create Compute Environment Service Role
    def create_compute_environment_service_role(self):
        compute_environment_service_role = iam.Role(
            self,
            "ComputeEnvironmentServiceRole",
            assumed_by=iam.ServicePrincipal("batch.amazonaws.com")
        )

        compute_environment_service_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSBatchServiceRole"))

        return compute_environment_service_role
    

    # create AWS Batch Compute Environment
    def create_batch_compute_environment(self):
        batch_compute_environment = batch.CfnComputeEnvironment(
            self,
            "ComputeEnvironment",
            compute_environment_name="Batch-Actuary-Computing",
            service_role=self.compute_environment_service_role.role_name,
            type="MANAGED",
            state="ENABLED",
            compute_resources=batch.CfnComputeEnvironment.ComputeResourcesProperty(
                type="SPOT",
                allocation_strategy="SPOT_CAPACITY_OPTIMIZED",
                bid_percentage=100,
                minv_cpus=0,
                maxv_cpus=320,
                desiredv_cpus=0,
                instance_role=self.compute_environment_instance_profile.attr_arn,
                instance_types=["optimal"],
                image_id="",
                launch_template=batch.CfnComputeEnvironment.LaunchTemplateSpecificationProperty(
                    launch_template_name=self.launch_template.launch_template_name,
                    version="$Latest"),
                security_group_ids=[self.compute_env_sg.security_group_id],
                subnets=[self.vpc.private_subnets[0].subnet_id]
            ),
        )

        batch_compute_environment.add_dependency(self.launch_template)

        return batch_compute_environment
    

    # create AWS Batch Job Queue
    def create_batch_job_queue(self):
        job_queue = batch.CfnJobQueue(
            self,
            "JobQueue",
            job_queue_name="actuary-computing-job-queue",
            compute_environment_order=[
                batch.CfnJobQueue.ComputeEnvironmentOrderProperty(
                    compute_environment=self.batch_compute_environment.compute_environment_name,
                    order=1,
                )
            ],
            priority=1,
        )

        job_queue.add_dependency(self.batch_compute_environment)

        return job_queue


    # create AWS Batch Job Definition
    def create_batch_job_definition(self):
        job_definition = batch.CfnJobDefinition(
            self,
            "JobDefinition",
            type="container",
            job_definition_name="actuary-computing-job-definition",
            platform_capabilities=["EC2"],
            retry_strategy=batch.CfnJobDefinition.RetryStrategyProperty(attempts=3),
            container_properties=batch.CfnJobDefinition.ContainerPropertiesProperty(
                image=self.asset.image_uri,
                vcpus=2,
                memory=7168,
                environment=[batch.CfnJobDefinition.EnvironmentProperty(
                                name="INPUT_DIR",
                                value="/fsx/input"),
                            batch.CfnJobDefinition.EnvironmentProperty(
                                name="OUTPUT_DIR",
                                value="/fsx/output")],
                volumes=[batch.CfnJobDefinition.VolumesProperty(
                            host=batch.CfnJobDefinition.VolumesHostProperty(
                                source_path="/fsx"
                            ),
                            name="fsx"
                        )],
                mount_points=[batch.CfnJobDefinition.MountPointsProperty(
                    container_path="/fsx",
                    read_only=False,
                    source_volume="fsx"
                )],
                log_configuration=batch.CfnJobDefinition.LogConfigurationProperty(
                    log_driver="awslogs"),
                privileged=False,
                readonly_root_filesystem=False
        ))

        job_definition.add_dependency(self.job_queue)

        return job_definition
    

    # amazon eventbridge that is triggered when batch job is completed
    def create_batch_job_completed_event_rule(self):
        event_rule = events.Rule(
            self,
            "BatchJobCompletedEventBridge",
            event_pattern=events.EventPattern(
                                source=["aws.batch"], 
                                detail_type=["Batch Job State Change"],
                                detail={"status": ["SUCCEEDED"]}))

        event_rule.add_target(targets.LambdaFunction(self.lambda_function_calculate))

        return event_rule
    

    # function to build docker image from Dockerfile and push to ecr
    def build_docker_image(self):
        __dirname = os.path.join(cwd, 'docker_files')
        asset = DockerImageAsset(self, "ActuaryCalculatingImage",
                                 directory=__dirname)
        
        return asset
    

    # display outputs 
    def outputs(self):
        return [CfnOutput(self, "VPCId", 
                          value=self.vpc.vpc_id,
                          export_name="VPCId"),
                CfnOutput(self, "FsxFileSystemId", 
                          value=self.fsx_file_system.file_system_id,
                          export_name="FsxFileSystemId"),
                CfnOutput(self, "EventBridgeRuleName",
                          value=self.event_rule.rule_name,
                          export_name="EventBridgeRuleName"),
                CfnOutput(self, "LambdaFunctionName",
                          value=self.lambda_function_calculate.function_name,
                          export_name="LambdaFunctionName")]
    

     

        

        

        

        

        

        
