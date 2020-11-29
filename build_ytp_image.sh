#!/bin/bash

docker image rm yrok472/ytp
docker image rm ytp
docker build . -t ytp:latest
docker tag ytp yrok472/ytp:latest
docker push yrok472/ytp
