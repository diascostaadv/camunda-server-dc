#!/usr/bin/env bash
set -euo pipefail

# Verifica se já existe um Swarm
if docker info --format '{{ .Swarm.LocalNodeState }}' | grep -qE 'active|pending'; then
  echo "Este nó já faz parte de um Swarm."
  exit 0
fi

# Caso queira juntar‑se a um Swarm existente, exporte SWARM_JOIN_TOKEN e MANAGER_IP
if [[ -n "${SWARM_JOIN_TOKEN:-}" && -n "${MANAGER_IP:-}" ]]; then
  docker swarm join --token "$SWARM_JOIN_TOKEN" "$MANAGER_IP":2377
else
  docker swarm init --advertise-addr "$(hostname -I | awk '{print $1}')"
fi
