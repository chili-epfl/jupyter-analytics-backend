#!/usr/bin/env bash
if [ -f /tmp/leader_only ]; then
    echo "Deleting leader_only file"
    rm /tmp/leader_only
fi