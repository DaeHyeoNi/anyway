#!/bin/sh
set -e
git pull
docker compose restart
