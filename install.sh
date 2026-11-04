#!/usr/bin/env bash
# Copia as skills da agência para ~/.claude/skills (substitui versões anteriores destas skills).
set -euo pipefail
origem="$(cd "$(dirname "$0")" && pwd)/skills"
destino="$HOME/.claude/skills"
mkdir -p "$destino"
for d in "$origem"/*/; do
  nome="$(basename "$d")"
  rm -rf "${destino:?}/$nome"
  cp -r "$d" "$destino/$nome"
  echo "instalada: $nome"
done
registro="$HOME/.claude/agencia/clientes.md"
if [ ! -f "$registro" ]; then
  mkdir -p "$(dirname "$registro")"
  printf '# Clientes da agência\n\n| Cliente | Pasta |\n|---|---|\n' > "$registro"
  echo "criado: $registro"
fi
