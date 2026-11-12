#!/bin/bash
set -e
mkdir -p artifacts/logs
echo "== docker compose ps ==" > artifacts/docker_ps.txt
docker compose ps >> artifacts/docker_ps.txt 2>&1
docker network inspect forummod_net > artifacts/network.json 2>&1
for s in kafka minio postgres elasticsearch api vision text fusion indexer; do
  docker compose logs --no-color --tail=200 $s > artifacts/logs/$s.log 2>&1 || true
done
echo "proofs saved to artifacts/"
