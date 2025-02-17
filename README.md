# Jupyter Analytics Backend

As part of the learning analytics system ([**Jupyter Analytics**](https://github.com/chili-epfl/jupyter-analytics)), the backend handles tasks like request processing, data storage, access control, and pre-processing raw data from [**Telemetry**](https://github.com/chili-epfl/jupyter-analytics-telemetry) to prepare structured data for [**Dashboard**](https://github.com/chili-epfl/jupyter-analytics-dashboard), etc. This repository contains the source code for the backend Flask API as well as the automated workflows to publish the generated Docker image and to deploy a specific version of the app to AWS Elastic Beanstalk.

## Backend Infrastructure

There are 3 ways to deploy this backend:

1. Using `docker-compose`: for development purposes and to iterate on the implementation of the app, typically used for local development. It directly builds the Flask image from the source code in `flask/` and abstracts the other components of the app by spinning up the other containers through the `docker-compose` template.
2. On AWS: which is the production-ready deployment. It grabs the Flask image that can be built and pushed to a registry from this repository and deploys it to Elastic Beanstalk.
3. On a Linux remote server: which is also production-ready, but relies on the available compute resources of where it's being deployed.

Before digging into the requirements and how to run this backend in a local development environment, let's review the architecture. Whether deployed on AWS, or for testing purposes with `docker-compose` as with this repository's source code, the architecture involves the same containers:

- A load balancer, to route traffic to the Flask running containers. This is the only entrypoint of the backend, the other containers cannot be reached from the outside, unless running `docker-compose` in debug mode here. On AWS, it corresponds to an Application Load Balancer and it is managed by AWS. And with `docker-compose`, an Nginx load balancer is spun up.
- Multiple Flask containers, that horizontally scale depending on the traffic. With `docker-compose`, you cannot dynamically increase the number of containers depending on some criteria, hence two containers are started by default.
- A Redis container, which is required by Flask-SocketIO when running more than one Flask instance in order to coordinate them together. On AWS, this Redis container is deployed with ECS (Elastic Container Service) by pulling the Redis official image and enabling traffic coming from the Flask instances.
- A PostgreSQL database. With the `docker-compose`, the PostgreSQL database is created manually by pulling the official image, when on AWS, the database is created using RDS, a managed service to deploy databases that can help with doing backups or restoring snapshots.

Further details about the Flask app implementation and the source code are available <a href="./flask/README.md">here</a>.

## Installation

To run this infrastructure in your personal environment, only Docker is required, as it comes installed with `docker-compose`.

## Deployment

The deployment of the application on AWS can be done in multiple steps. First, the infrastructure (the other components than the Flask app) must be deployed providing a version of the Flask app. Then, the GitHub Actions workflows of this repository in `.github/workflows` can be used to update the running infrastructure in two steps:

1. `push-to-ECR`: which builds the Docker image from the source code of this repository and pushes it to Amazon ECR (Elastic Container Registry), an image public registry.
2. `EB-deploy-from-bundle`: which takes as input an image tag (version) and deploys that Docker image to the running Elastic Beanstalk servers.

To learn more about: how to first deploy the infrastructure with infrastructure-as-code, how the deployment workflows work, and what to look out for before making a release, check the <a href="./RELEASE.md">RELEASE.md</a>.

## Development

To further develop the backend, first clone the repository:

```sh
$ git clone https://github.com/chili-epfl/jupyter-analytics-backend.git
```

Then, add a `.env` file and populate it with your own values, as in the `.env.example`.

To build the containers, there are multiple options. The `run.sh` shell script provides commands that can be run to spin up all the containers with some additional options.

The `run.sh` script can be executed with:

```sh
$ bash ./run.sh [-e <environment>] [-v] [-d]
```

The 3 flags are optional and do the following:

- `-e`/`--env` is either of `debug`, `dev` or `prod` (default) and determines which `docker-compose.<env>.yml` to run. The `debug` environment has logging and development servers, as opposed to the `prod` environment.
- `-v`: if present, will first remove the volumes associated with the containers. For example to remove the content of the database while testing. If not present, will simply bring down all the containers before starting new ones.
- `-d`: if present, will run in detach mode. If not, will finish the execution with `docker-compose logs -f` which displays container logs in real-time in the current shell.

Example (running the backend in `debug` mode and not in detach mode):

```sh
$ bash ./run.sh -e debug -v
```

Then the flask backend API can be accessed from `http://localhost:1015/` or whatever port you expose with the Nginx container.

The `run.sh` script also executes the `flask/db_init.py` script to create the tables in the database according to the models described in `flask/app/models/` so that it works straight away with a fresh start of the containers.

Note that doing `CTRL+C` does not kill the containers, since the `run.sh` is running them in detached mode. To kill them, do:

```sh
# to keep the attached volumes
$ docker-compose -f docker-compose.<ENV>.yml down
# to remove the attached volumes
$ docker-compose -f docker-compose.<ENV>.yml down -v
```

The difference between the 3 modes:

1. Debug: Flask starts with the development server, so you don't need to restart the Flask containers when making a change. Simply saving the file will update the running container. Also the 1st Flask container is listening on port 5000, making it exposed to external connectivity, which can be useful when debugging to bypass the load balancer.

    (Tips: Mac users may find port 5000 already in use: go Apple Menu > System settings > general > AirDrop & Handoff > you will see Airplay Receiver on. Slide it off, which will turn off Airplay Receiver and frees the port 5000.)

2. Dev: Flask is started with gunicorn, as in production and on AWS, making it scalable. It is also started with logging enabled.

3. Prod: Flask is started with gunicorn, but with logging disabled.

## Credits

Jupyter Analytics was initially developed by [**Raphaël Mariétan**](https://github.com/Rmarieta). 🎉

This project is part of the "[Uni Analytics](https://data.snf.ch/grants/grant/187534)" project funded by SNSF (Swiss National Science Foundation). That's why in the source code we put "unianalytics" as the identifier. 😃

## Citation
If you find this repository useful, please cite our paper:
```
Cai, Z., Davis, R., Mariétan, R., Tormey, R., & Dillenbourg, P. (2025).
Jupyter Analytics: A Toolkit for Collecting, Analyzing, and Visualizing Distributed Student Activity in Jupyter Notebooks.
In Proceedings of the 56th ACM Technical Symposium on Computer Science Education (SIGCSE TS 2025).
```

## Copyright
© All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE (EPFL), Switzerland, Computer-Human Interaction Lab for Learning & Instruction (CHILI), 2024

## License
This project is licensed under the MIT License. See the [LICENSE](https://github.com/chili-epfl/jupyter-analytics-backend/blob/main/LICENSE) file for details.