#!/bin/bash
# Copia o site marca-passos.com para navegação offline
# Uso: ./copiar.sh [diretório-saída]

set -e

URL="https://www.marca-passos.com/"
OUT="${1:-.}/marca-passos"

echo "Copiando $URL para $OUT..."
echo "(respeitando robots.txt, esperando 0.5s entre requests)"

python3 -m site_copier "$URL" -o "$OUT" \
  --max-pages 1000 \
  --max-depth 15 \
  --respect-robots \
  --delay 0.5 \
  --workers 2

echo ""
echo "✓ Cópia completa!"
echo "Abra no navegador: $OUT/www.marca-passos.com/index.html"
