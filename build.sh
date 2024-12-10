#!/usr/bin/env bash
export V="${1:-latest}"
docker build --platform=linux/amd64 \
    -t  ghcr.io/pfc-developer/symphony-feeder:${V} .
docker push  ghcr.io/pfc-developer/symphony-feeder:${V}