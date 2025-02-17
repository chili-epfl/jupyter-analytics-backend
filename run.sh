#!/bin/bash

# default values
ENVIRONMENT="prod"
DETACH=false
VOLUMES=false

# parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"

    case $key in
        -e|--env)
            ENVIRONMENT="$2"
            shift
            ;;
        -d|--detach)
            DETACH=true
            ;;
        -v|--volumes)
            VOLUMES=true
            ;;
        *)
            # unknown option
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
    shift
done

# run the corresponding docker-compose file
case $ENVIRONMENT in
    "debug")
        DOCKER_COMPOSE_FILE="docker-compose.debug.yml"
        ;;
    "dev")
        DOCKER_COMPOSE_FILE="docker-compose.dev.yml"
        ;;
    "prod")
        DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
        ;;
    *)
        echo "Invalid environment. Use 'debug', 'dev', or 'prod'."
        exit 1
        ;;
esac

# kill the previous containers and clear the volumes if requested
if [ "$VOLUMES" = false ]; then
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
else
    docker-compose -f "$DOCKER_COMPOSE_FILE" down -v
fi

# build and start the services
docker-compose -f "$DOCKER_COMPOSE_FILE" up --build -d

# run init_db script
docker-compose -f "$DOCKER_COMPOSE_FILE" exec flask python init_db.py

# if not in detached mode, show the real-time logs in the current shell
if [ "$DETACH" = false ]; then
    docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f
fi
