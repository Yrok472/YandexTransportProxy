#!/bin/bash

# "cd" into "ytp" before script running

# Preconditions:
# docker login https://harbor.smartvz.site # enter creds from https://harbor.smartvz.site

docker image rm infra/ytp
docker image rm ytp
docker build . -t ytp:latest
docker tag ytp harbor.smartvz.site/infra/ytp:latest
docker push harbor.smartvz.site/infra/ytp:latest
