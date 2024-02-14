## Actuarial-Reserve-Modelling

Actuarial modeling is a key component in the insurance industry, used for analyzing and predicting various risks and potential losses. Due to the complexity of calculations involved, actuarial modeling requires significant computing power and resources. This is where AWS services such as [AWS High Performance Computing (HPC)](https://aws.amazon.com/hpc/) services come in. This repository is an addtion to [this](https://aws.amazon.com/blogs/hpc/high-performance-actuarial-reserve-modeling-using-aws-batch/) blog post where we walk you through on how we can deploy scalable and cost-effective solution for actuarial computing using AWS services.

## Before you begin

It is recommended to run it on a machine other than Mac with M1 chip due to the differences of docker image OS architecture version that M1 chip produces versus what AWS Batch expects. For smooth running, we advise [spinning up](https://docs.aws.amazon.com/cloud9/latest/user-guide/create-environment.html) an [AWS Cloud9](https://aws.amazon.com/cloud9/) instance, copy this git repository to your Cloud9 instance environment and proceed with steps below. If you proceed with Cloud9 instance, make sure you [attach](https://catalog.us-east-1.prod.workshops.aws/workshops/ce1e960e-a811-475f-a221-2afcf57e386a/en-US/00-prerequisites/03-attach-machine-role) an IAM Role to the instance in the EC2 console.

## Prerequisites
- AWS Account(s) with IAM user(s) with appropriate permissions. 
- Docker [installed](https://docs.docker.com/get-docker/) and running on your machine.
- AWS CDK version 2 [installed](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) and [bootstrapped](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html).
- The AWS CLI [installed](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) and [configured](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)

## Deploy infrastructure

- Run `cdk bootstrap --require-approval never && cdk deploy --require-approval never`.
This will build a docker image and push it to [Amazon ECR](https://aws.amazon.com/ecr/), deploy the infrastructure and copy policy_[*].csv files to the [Amazon S3](https://aws.amazon.com/s3/) bucket.
- This process will take ~15-20 minutes for everything to provision.
- After cdk command succesfully executed, copy `ActuaryCalculationStack.EventBridgeRuleName` value and `ActuaryCalculationStack.LambdaFunctionName` from the cdk ouput in your terminal/command line and save them in a text editor of your choice. We will need these values later.

## Submitting batch job

- Navigate to the root `aws-reserve-modelling/` directory and run ```aws batch submit-job --cli-input-json file://test-10-workers.json``` to test with 10 workers (you can also use [test-10-workers.json]() or [test-5-workers.json]() or simply create another json with different amount of workers based on the templates we included).
- Copy `jobId` value from the cli output.
- Run ```aws events put-rule --name "ActuaryCalculationStack.EventBridgeRuleName" --event-pattern "{\"source\":[\"aws.batch\"],\"detail-type\":[\"Batch Job State Change\"],\"detail\":{\"jobId\":[\"jobIdValue\"],\"status\":[\"SUCCEEDED\"]}}"```
    - Substitute `ActuaryCalculationStack.EventBridgeRuleName` with rule name that you got in step 8.
    - Substitute `jobIdValue` with jobId that you got in step 10.
    
## Navigating to the AWS Batch console
    
- Navigate to the AWS Batch console and see the results in the logs of workers.
- Go to the `Jobs` tab, then select `actuary-computing-job-queue` from the drop down menu.
- You can observe the result of the child jobs here and wait until the status of a parent jobs changes for `SUCCEEDED`.

## Navigate to the AWS Lambda console

- After execution of your Batch jobs is completed, navigate to your [AWS Lambda](https://aws.amazon.com/lambda/) function (you can find by `ActuaryCalculationStack.LambdaFunctionName` name that you copied in the above section).
- Select CloudWatch logs tabs and you will be redirected to [Amazon CloudWatch](https://aws.amazon.com/cloudwatch/) console where you can see the average reserves across all of your workers in the logs.
- Look for the `The total reserves` line in the logs.

## Clean-up

To destroy the infrastructure, run `cdk destroy --force` inside the `/actuary/infrastructure` folder. This will delete all the resources that were provisioned in the blog post.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

