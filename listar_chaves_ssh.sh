#!/usr/bin/env bash
# listar_chaves_ssh.sh
# Mostra todas as chaves públicas em ~/.ssh e suas fingerprints

SSH_DIR="$HOME/.ssh"

if [[ ! -d $SSH_DIR ]]; then
  echo "Diretório $SSH_DIR não existe."
  exit 1
fi

shopt -s nullglob   # evita erro se não houver *.pub
pub_keys=("$SSH_DIR"/*.pub)

if [[ ${#pub_keys[@]} -eq 0 ]]; then
  echo "Nenhuma chave pública (*.pub) encontrada em $SSH_DIR"
  exit 0
fi

echo "Chaves encontradas em $SSH_DIR:"
echo "----------------------------------------"

for pub in "${pub_keys[@]}"; do
  base=$(basename "$pub")
  priv="${pub%.pub}"
  echo "Arquivo: $base"
  [[ -f $priv ]] && echo "  ↳ par privado existe: $(basename "$priv")" || echo "  ↳ **par privado NÃO encontrado**"
  ssh-keygen -lf "$pub" | sed 's/^/  Fingerprint: /'
  echo "----------------------------------------"
done
