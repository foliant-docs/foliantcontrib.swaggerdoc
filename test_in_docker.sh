#!/bin/bash

# Write Dockerfile
echo "FROM python:3.9.21-alpine3.20" > Dockerfile
echo "RUN apk add --no-cache --upgrade bash && pip install --no-build-isolation pyyaml==5.4.1" >> Dockerfile
echo "RUN apk add nodejs npm" >> Dockerfile

# Run tests in docker
docker build . -t test-swaggerdoc:latest

docker run --rm -it -v "./:/app/" -w /app/ test-swaggerdoc:latest "./test.sh"

# Remove Dockerfile
rm Dockerfile