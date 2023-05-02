Actuarial-Reserve-Modelling

Before you begin:
It is recommended to run it on a machine other than Mac with M1 chip due to the differences of docker image OS architecture version that M1 chip produces versus what AWS Batch expects. For smooth running, we advise [spinning up](https://docs.aws.amazon.com/cloud9/latest/user-guide/create-environment.html) an [AWS Cloud9](https://aws.amazon.com/cloud9/) instance, copy this git repository in your instance environemnt and proceed straigth to the step #3 below. If you proceed with Cloud9 instance, make sure you [attach](https://catalog.us-east-1.prod.workshops.aws/workshops/ce1e960e-a811-475f-a221-2afcf57e386a/en-US/00-prerequisites/03-attach-machine-role) an IAM Role to the instance in the EC2 console.

To run follow these steps:

1. Make sure you have aws cdk installed. If not, run 'npm install -g aws-cdk' or 'brew install aws-cdk' (on Mac).
2. Make sure you have credentials for IAM User stored in '~/.aws/credentials' (Mac, Linux) or 'C:\Users\ USERNAME \.aws\credentials' (Windows).
3. Run 'git clone git@github.com:rppth/aws-reserve-modelling.git' to clone the repository locally.
4. Go inside /actuary/infrastructure folder and run 'python -m pip install -r requirements.txt'.
5. After the installation from previous step is done, run 'cdk bootstrap --require-approval never && cdk deploy --require-approval never'. 
6. This will build a docker image and push to ECR, deploy the infrastructure and copy policy_[*].csv files to the S3 bucket.
7. After the infrastructure is deployed (this will take ~15-20 minutes for everything to provision) go to the root folder (aws-reserve-modelling).
8. After cdk command succesfully executed, copy "ActuaryCalculationStack.EventBridgeRuleName" value and "ActuaryCalculationStack.LambdaFunctionName" from the cdk ouput in your terminal.
9. Navigate to the root directory and run 'aws batch submit-job --cli-input-json file://test-10-workers.json' to test with 10 workers (or just create another json with different amount of workers).
10. Copy "jobId" value from the cli output.
11. Run 'aws events put-rule --name "ActuaryCalculationStack.EventBridgeRuleName" --event-pattern "{\"source\":[\"aws.batch\"],\"detail-type\":[\"Batch Job State Change\"],\"detail\":{\"jobId\":[\"jobIdValue\"],\"status\":[\"SUCCEEDED\"]}}"'
    - Substitute "ActuaryCalculationStack.EventBridgeRuleName" with rule name that you got in step 8.
    - Substitute "jobIdValue" with jobId that you got in step 10.
12. Go to the AWS Batch console and see the results in the logs of workers. 
13. After execution of your Batch jobs is completed, navigate to your Lambda function (you can find by "ActuaryCalculationStack.LambdaFunctionName" name that you copied in step 7) and see the average reserves across all of your workers in the logs.
14. To destroy the infrastructure, run 'cdk destroy --force' inside the /actuary/infrastructure folder.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

