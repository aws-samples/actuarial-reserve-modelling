#!/usr/bin/env python3
import aws_cdk as cdk
from stack import CdkStack

app = cdk.App()
CdkStack(app, "ActuaryCalculationStack", env=cdk.Environment())
app.synth()
