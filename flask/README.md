# Flask Application Source Code

## Structure

- `Dockerfile` : to build the container
- `requirements.txt` : to install the dependencies within the container
- `application.py` : creates and runs the app by using the `create_app()` method defined in `app/__init__.py`
- `init_db.py` : script that can be run to initialize the database with the tables defined in `app/models/*.py`. This script is called in the `docker-compose` files and also upon startup of the AWS deployments
- `app/` : where the application logics are defined
  - `__init__.py` : defining the app configuration
  - `models/` : where the database table models are defined
  - `views/` : where all the blueprints and all routes are defined
  - `utils/` : where the utility functions are defined
  - `templates/` : where a basic HTML signup page is defined
- `ebbundle/` : directory that contains the content to zip and provide to Elastic Beanstalk to generate a new release. To read more about releasing a new version of the app : <a href="../RELEASE.md">RELEASE.md</a>. `ebbundle/` contains:
  - `docker-compose.yml` : this is the file that you need to provide within a zipped bundle to Elastic Beanstalk if willing to run a Docker image. You then need to provide the registry URL of your image and set it behind an nginx reverse proxy.
  - `.ebextensions` : where you define configs that are executed by Elastic Beanstalk after it spins up instances but before the container application is started. This is useful for example. Here they're used to enable some `nginx` logging and allow to execute the `init_db.py` script only in the leader container of a release deployment.
  - `.platform` : where you define hooks that can be run pre- or post-deployment, in our case the `init_db.py` requires the application to be running, so using a `postdeploy` hook.
  - `nginx-proxy` : configuration of the nginx proxy to route traffic to the flask service and enable access and error logs.
- `tests/` : containing the functional and unit tests for the app. The tests are defined using PyTest but are not integrated as part of any workflow anymore at the moment. To manually run the test or add them as part of a workflow step, do : `docker exec -u root flask-container sh -c "python -m pytest"`.
- `migrations/` : folder containing the migration scripts generated using `Flask-Migrate`.

The application is using `flask-jwt-extended` to protect some routes and blueprints with a login system. It uses an access token and returns a refresh token to provide short-lived credentials to the clients but let them have a way to refresh their credentials. The login and token generation logics are defined in `app/views/auth.py`.

Explanation of the blueprints :

1. `auth.py` : defining the login callback and the routes to whitelist users for specific notebooks
2. `dashboard_interaction.py` : routes to add/retrieve TA user interaction with the dashboards to the database.
3. `dashboard.py` : routes queried by the `jupyterlab-unianalytics-dashboard` extension to fill the dashboards with data. All the routes of this blueprint are protected with authentication and with a notebook existence check.
4. `delete.py` : unused, but sometimes uncommented to define temporary routes to delete specific rows with a token for testing.
5. `event.py` : routes to query the number of entries in certain tables for debugging purposes.
6. `groups.py` : routes to add or update TA groups.
7. `jwt.py` : routes for common authorization workflows and role-based access controls (admin > superuser > user, while **admin permission needs be granted manually in the database**)
8. `main.py` : blueprint for the healthcheck and check the hostname of the instance dealing with the request.
9. `notebook.py` : to upload or download notebooks. Uploading a notebook is protected with authentication.
10. `send.py` : gathering all the routes that are targeted by the `jupyterlab-unianalytics-telemetry` extension to add entries to the database. Those routes don't require authentication.
11. `sockets.py` : defining the handlers using `Flask-SocketIO` to open or close websocket connections with users. Also storing and retrieving connected user id's from the redis cache.

## Perform a Migration

To perform a migration, the `Flask-Migrate` library can come in handy. In `app/__init__.py` the application is wrapped with the `Flask-Migrate` wrapper :

```python
from flask_migrate import Migrate
migrate = Migrate()
...
def create_app():
  ...
  migrate.init_app(app, db)
```

Thanks to that, you can make changes to the database models while the application is running (if running Flask in development mode) and then changes will be picked up and you can generate migration scripts that can then be reused to perform migrations in the production environment.

### Steps to Achieve a Migration

#### Locally

1. First perform the schema change in your local development environment :

   a. Make sure you're running in debug mode with `docker-compose.debug.yml` or refreshing the Flask app by saving will not have any impact on the running environment.

   b. Start the containers

2. Enter Flask container as root user to generate the migration scripts :

```sh
$ docker exec -u root -it flask-container sh

# if it's the first time ever running a migration, run the following, but not if you already have any migration history as in this repository
$ flask db init
```

3. Make some changes to your tables in your IDE and hit save

4. Update the migration head and generate the migration script :

```sh
$ flask db stamp head

# generate the migration script
$ flask db migrate -m "Description of migration"
```

5. Now a new migration script will appear in `migrations/versions/`. `Flask-Migrate` tries to guess what has changed in your schemas to define an `upgrade()` and `downgrade()` method. It usually does a good job, but make sure you check the content that's been guessed because it sometimes does not pick up some changes, such as changing an Enum type. You can then perform the migration locally :

```sh
$ flask db upgrade
```

#### In the Production Environment

1. Since the migration scripts are also included in the `Dockerfile`, you can build, push and deploy the new image in production with the new schemas using the appropriate workflows.
2. Enter the production environment to execute the migration script :

   On Elastic Beanstalk : navigate to one of the EC2 instances of your new Elastic Beanstalk deployment > Connect > Session Manager, and connect to your instance. Then :

   ```sh
   $ bash
   $ sudo su
   $ docker exec -it -u root flask-container sh
   $ flask db stamp head
   $ flask db upgrade
   ```
