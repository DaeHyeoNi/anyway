#!/bin/sh
set -e
git pull
docker compose up -d --build --remove-orphans
