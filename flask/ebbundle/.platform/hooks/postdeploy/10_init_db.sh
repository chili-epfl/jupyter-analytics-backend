#!/usr/bin/env bash
if [ -f /tmp/leader_only ]; then
    echo "Running init_db.py script on leader container"
    docker exec flask-container python3 init_db.py
fi