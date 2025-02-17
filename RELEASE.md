# Release Guidelines

### Making the 1st Deployment

### AWS

The whole AWS infrastructure can be deployed on a new or existing AWS account by running a CloudFormation template. To run the CloudFormation template, go to `AWS > CloudFormation > Create Stack (new resources) > Choose an existing template > Upload a template file`, upload the Cloudformation file (`cloudformation/unianalytics-prod.yml`), then provide the following values to the Parameters :

- `HostedZoneId` : here you need to own a domain in Route53 to have the infrastructure run behind HTTPS. Provide the hosted zone id
- `RedisInstanceType` : `t4g.nano` or `t4g.micro` to be sage
- `SSHKey` : provide an ssh key to ssh into the Elastic Beanstalk instances. If you don't see any, generate one in `EC2 > Key Pairs > Create key pair`. Don't leave this blank or it will cause the stack to fail.
- `EBInstanceType` : pick the instance type for the Elastic Beanstalk. `t4g.micro` is good.
- `EBMinSize` and `EBMaxSize` : 1-3 should be good.
- `EBImageTag` : here provide the image tag of the Flask image that you want to deploy.
- `DBInstanceType` : `db.t4g.micro` is good.

Then submit the stack and wait for it to create. Upon stack completion : in the `Outputs` tab of CloudFormation, there should be the endpoint URL that should be used to reach the API.

The template creates the following resources :

- `VPCStack` : creates a public VPC with subnets, route tables, internet gateway and associated resources to have a dedicated cloud infrastructure to host the resources. This creates a nested stack since it reads the content of another generic template hosted in `https://unianalytics-iac.s3.eu-north-1.amazonaws.com/child-public-vpc-3-subnets.yml`.
- `SharedRedisPrivateHostedZone` : creates a private hosted zone to have a DNS record that always maps traffic to the Redis instance private IP address. Since the Redis instance can crash and be replaced, this record is used by the Flask instance to always target the same DNS name and have it resolved with the right IP address.
- `SharedRedisInstanceDnsRecord` : this is the actual DNS record.
- `SharedDNSRecordLambdaExecutionRole` : role with permissions to read/write in Route53.
- `SharedDNSRecordLambdaUpdate` : Lambda function that updates the value of the record and that is called in the bootstrap process (named `UserData`) of the Redis instance instantiation with the newly assigned private IP address.
- `SharedDNSRecordLambdaDelete` : Lambda function that deletes that record upon stack deletion, to ensure a proper clean-up of the resources if the stack is trying to be deleted.
- `SharedOnStackDeletion` : triggers the call of the above Lambda function upon stack deletion.
- `EBHostedZoneNameLambdaExecutionRole` : role with permissions to read/write to Route53.
- `EBHostedZoneNameLambda` : Lambda function to add the record that will route traffic to the load balancer and that will be the endpoint to reach the API. This is required to serve the backend over HTTPS, since load balancer can't be used to associate with an SSL certificate.
- `EBHostedZoneLambdaTrigger` : if an owned domain is provided in the parameters, this will trigger the Lambda function above on stack creation.
- `EBACMCertificate` : creates the SSL certificate that will enable HTTPS traffic termination on the load balancer.
- `EBSecretsGenerationLambdaExecutionRole` : role with permissions to execute a Lambda function
- `EBSecretsGenerationLambdaFunction` : Lambda function that generates all the random strings required as environment variables for the Elastic Beanstalk environment.
- `EBSecretsGenerationLambdaTrigger` : trigger that calls the function to generate all the passwords at the start of the stack creation.
- `EBSecurityGroup` : enables port 22 ingress for ssh connection with the provided key in the Parameters.
- `EBSecurityGroupIngress` : to create an inbound rule from ECS to EB on port 6379 and reference the security group of the ECS resource.
- `EBELBv2SecurityGroup` : to enable HTTP traffic at the load balancer level.
- `EBELBv2SecurityGroupIngress443` : to only enable HTTPS traffic at the load balancer level if a valid `HostedZoneId` is provided.
- `ECSSecurityGroup` : enables ssh from anywhere, and redis traffic from the EB EC2 instances.
- `ECSInstanceProfileRole` : role with permissions to execute the `SharedDNSRecordLambdaUpdate` Lambda function.
- `ECSInstanceProfile` : profile to assume the above role.
- `ECSLaunchTemplate` : defines the type of EC2 instance, the ssh key to enable, the security group and all the config for the ECS instance that will be launched in the ECS cluster.
- `ECSAutoScalingGroup` : autoscaling group with min and max set to 1 to always have one instance running.
- `ECSCluster` : cluster for the ECS task.
- `ECSCapacityProvider` : just needs to be defined with ECS.
- `ECSClusterCPAssociation` : just needs to be defined with ECS.
- `ECSTaskExecutionRole` : role with permissions ot execute a task in ECS.
- `ECSCloudWatchLogsGroup` : log group for ECS.
- `ECSTaskDefinition` : defines what Docker image (redis) to pull and deploy in the single running container. Also defines the port mappings and the architecture of the CPU & operating system configuration.
- `ECSService` : defines how many tasks should be running per EC2 instance (only 1 in our case).
- `EBInstanceProfileRole` : role with permissions to log into the EB instances with `Session Manager` from the console.
- `EBInstanceProfile` : profile to assume the above role.
- `EBS3Bucket` : S3 bucket to store the downloaded zip bundle to deploy the app. This is needed if the stack is created in a different region than `eu-north-1` since that is where I upload the zip, and unfortunately you can't provide the S3 URL of an application version zip that's in a different region in CloudFormation.
- `EBS3BucketPolicy` : policy to let EB read/write to that bucket.
- `EBEmptyS3BucketLambdaExecutionRole` : role with permissions to empty that bucket since a bucket needs to be empty to be deleted. Would make a stack deletion fail if not emptied.
- `EBEmptyS3BucketLambda` : Lambda function that empties the bucket.
- `EBEmptyS3BucketTrigger` : trigger that calls the above Lambda function on stack deletion.
- `EBS3CopyBundleLambdaExecutionRole` : role with permissions to copy the bundle in the above defined S3 bucket.
- `EBS3CopyBundleLambda` : Lambda function that copies the publicly available zip from the `eu-north-1` S3 bucket that we own and that lists the zip bundles to the S3 bucket created in this stack. The URL of the zip takes the `EBImageTag` Parameter as input to adapt which zip should be copied.
- `EBS3CopyBundleTrigger` : trigger that calls the above Lambda function.
- `EBApplication` : defines the Elastic Beanstalk application.
- `EBApplicationVersion` : defines the first version of the application that is then provided to the Environment resource. This is where the key of the S3 object corresponding to the zip bundle is provided. This resource will enable pulling the Docker image specified in the `EBImageTag` Parameter.
- `EBConfigurationTemplate` : defines all the configuration of the EB environment; autoscaling group, ssh key, scaling rules, load balancer, VPC, instance type, environment variables that will be injected in the instances, load balancer listeners (to reroute HTTP traffic to HTTPS), RDS database definition and password.
- `EBEnvironment` : combines the `EBConfigurationTemplate` above with the `EBApplication` and the `EBApplicationVersion` to start the infrastructure.
- `EBLoadBalancerInfoLambdaExecutionRole` : role with permissions to get the id of the load balancer created by the `EBEnvironment`. This is necessary to then add a listener to the load balancer in order to re-route traffic to HTTP on port 80 to HTTPS on port 443 to only enable HTTPS. The id of the load balancer is also used to create a new DNS record to link an endpoint to the load balancer.
- `EBLoadBalancerInfoLambda` : Lambda function that queries the id of the load balancer.
- `EBLoadBalancerInfoTrigger` : trigger that calls the above function.
- `EBDNSRecord` : create a DNS record that routes traffic to our load balancer. This will be the endpoint that the extensions target if a `HostedZoneId` is provided. Otherwise, the traffic is served over HTTP and the endpoint is the DNS name of the load balancer.
- `AWSEBV2LoadBalancerListener` : listener that defines the re-routing from HTTP to HTTPS as explained in `EBLoadBalancerInfoLambdaExecutionRole`.

Some resources might appear useless such as `SharedOnStackDeletion` but they're just added so that the stack can be deleted without errors and manual intervention when deleted through the `Delete` button of the CloudFormation Console.

## Making a New Release

Any change made to the source code of the Flask app can be deployed using the following procedures in both types of deployment environments.

When adding more environment variables or secrets, extra steps are required to inject the additional environment variables into the container, as detailed below in <a href="#modifs">Modifying the Environment Variables</a>.

### AWS

As explained in the <a href="./README.md">README.md</a>, there are two workflows in this repository, the 1st one to build and publish the new Docker image to ECR, and the 2nd one to deploy an image to Elastic Beanstalk given the image tag. Additional details about the workflows :

1. `.github/workflows/push-to-ECR.yml`: this workflow is trigger when pushing to the `push-to-ecr` branch. All the local development is done on the main branch and whenever the app is ready to be uploaded, do the following :

   ```sh
   # still on the main branch
   $ git add .
   $ git commit -m "Commit for deployment workflow"
   $ git push

   # switch to the push-to-ecr branch
   $ git checkout push-to-ecr

   # merge the changes
   $ git merge main

   # push and trigger the deployment
   $ git push
   # if it's the first time pushing to the push-to-ecr branch, set the origin
   $ git push -u origin deploy

   # switch back to the main branch
   $ git checkout main
   ```

   Then the workflow does the following :

   a. Set up QMU and Docker Buildx, in order to build and push multi-platform image that can work on devices of different architectures, here `arm64` and `amd64`.

   b. Retrieve the AWS credentials. This works by assuming a role on AWS and configuring that same role in AWS to enable our specific repository to assume those credentials and define a set of permissions to grant that role once assumed.
   This <a href="https://aws.amazon.com/blogs/security/use-iam-roles-to-connect-github-actions-to-actions-in-aws/">link</a> details how to set up such a role on AWS. In our case, the `GitHubAction-AssumeRoleWithAction` role is granted with the permissions to read/write to the ECR registry and then access services such as S3 to upload the new app version and Elastic Beanstalk to deploy the new version.

   c. Login to ECR with the retrieved credentials

   d. Build and push the multi-platform image by building the image from the source code.

   e. Define the image tag with the current date, e.g. `2024.05.06` so it's always increasing.

   f. Create the zip bundle from the content of `app/ebbundle/` and substitute the image URL in `ebbundle/docker-compose.yml` using the image tag of the newly pushed image.

   g. Upload that zip file to a public S3 bucket, since making an Elastic Beanstalk application version deployment requires to either provide the source code directly or reference a zip file with the URL of the S3 bucket in which it is stored.

2. `.github/workflows/EB-deploy-from-bundle.yml`: this workflow takes the image tag that you want to deploy as input as well as the application and environment names for the Elastic Beanstalk production environment that you want to update. The assumed role obviously needs to have the permissions to update that environment so it must be targetting one of our account's environments. This repository does the following :

   a. Retrieves the zipped bundle uploaded in the `push-to-ECR` workflow.

   b. Retrieve the AWS credentials assuming the same role as in the `push-to-ECR` workflow.

   c. Deploy to Elastic Beanstalk by providing the zip file defining the new release to the workflow step and the AWS credentials retrieved in the previous step.

<h2 id="modifs">Modifying the Environment Variables</h2>

When adding/removing environment variables, adding in particular, extra steps need to be performed to make sure the different infrastructures are in sync and can still be used. Since environment variables are not part of the source code of the Flask app but injected by the parent process, the injection process is not identical in the 2 architectures (docker-compose vs AWS).

The next sections details what should be taken care of if adding an environment variable for each type of architecture.

### Local Development with `docker-compose`

Nothing to do here, since the Flask containers are being fed the whole content of the `.env` file with the following in the `docker-compose.*.yml` files :

```yaml
env_file:
  - .env
```

Then simply adding, removing or changing the environment variable value in the `.env` will directly be picked up in the Flask application. Adapt `.env.example` for readability.

### AWS

Since Elastic Beanstalk is downloading a zipped bundle that contains a `docker-compose.yml` in the background, this `docker-compose`'s `environment` field would have to be adapted in consequence :

```yaml
services:
  flask:
    image: public.ecr.aws/f7y3w4q3/unianalytics-prod:<IMAGE-TAG>
    container_name: flask-container
    environment:
      - RDS_HOSTNAME=${RDS_HOSTNAME}
      - RDS_PORT=${RDS_PORT}
      ...
      - NEW_ENVIRONMENT_VAR=${NEW_ENVIRONMENT_VAR}
```

This `docker-compose.yml` is located in `flask/ebbundle/`. That means that next time you trigger the `push-to-ECR` workflow, it will build the new Flask image expecting a new environment variable, and it will also pick up that change in the `flask/ebbundle/docker-compose.yml` in the uploaded zip bundle.

Now, you still need to add the actual value of the environment variable to the Elastic Beanstalk production environment. To modify the environment variables of an Elastic Beanstalk environment, you can go the <a href="https://eu-north-1.console.aws.amazon.com/elasticbeanstalk/home?region=eu-north-1#/applications">EB Console</a>, navigate to your `Environments > <your-environment> > Configuration` and at the very bottom you can see the values of the environment variables. You can `Edit` them, and apply the changes. This will re-deploy the application.

Once this is done, you can trigger the `EB-deploy-from-bundle` workflow to deploy the new Flask app.

Note that if you're simply updating your running environment then this is all you have to do, but if you use the same CloudFormation template to create the stack again in the future with that new image, you would have to add/remove/update the environment variables injected in the CloudFormation template. To do that, change the `cloudformation/unianalytics-prod.yml` template or create a new one as follow :

- Navigate to the resource of type `AWS::ElasticBeanstalk::ConfigurationTemplate`
- Navigate to `Properties > OptionSettings > Namespace: aws:elasticbeanstalk:application:environment`
- Add or modify the environment variables here. If you simply need to have a new password or randomly generated string, you can use the Lambda trigger similarly to what's done with the `SECRET_KEY` to let the variable be automatically generated upon stack creation. You would have to adapt the `EBSecretsGenerationLambdaFunction` so that it returns a new random string, and then use the value of that string in your environment variable. This is because a Lambda trigger in CloudFormation is only called upon stack creation and deletion, so those passwords are generated at the very start of stack creation, not every time the trigger is called in the template.

### Warning with `SECRET_SALT`

When changing the value of `SECRET_SALT`, the values already hashed in the database will only be compatible with the previous value of the `SECRET_SALT` since all the Flask app does to for example check if a user is whitelisted, is compare the hashed user id with the hash stored in the whitelist table. So in case you ever migrate from one infrastructure to the other like migrating the content of the database from AWS to a Linux remote server, the value of the `SECRET_SALT` would also have to be copied and used. The value of the currently used `SECRET_SALT` can be found in `EB Console > Select your environment > Configuration` and all the way to the bottom of the page are listed the environment values of the application.
