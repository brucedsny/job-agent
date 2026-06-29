# site_copier

Um agente que copia **todo o conteúdo de um site** para navegação offline.
Escrito 100% em Python da biblioteca padrão — **sem dependências externas**.

A partir de uma URL inicial, ele rastreia o site, baixa as páginas e seus
assets (CSS, JS, imagens, fontes, etc.) e **reescreve os links** para que a
cópia funcione abrindo os arquivos localmente no navegador.

## Uso

```bash
# Copiar um site inteiro para ./site-copy
python -m site_copier https://exemplo.com

# Escolher diretório de saída e limitar o tamanho
python -m site_copier https://exemplo.com -o ./copia --max-pages 200 --max-depth 5

# Ser um bom cidadão: respeitar robots.txt e dar um respiro entre requests
python -m site_copier https://exemplo.com --respect-robots --delay 0.5 --workers 2
```

Depois abra `./site-copy/<host>/index.html` no navegador.

### Vários sites de uma vez

Passe várias URLs, ou um arquivo com uma URL por linha:

```bash
python -m site_copier https://a.com https://b.com -o ./copias

# arquivo: uma URL por linha, '#' são comentários
python -m site_copier --urls-file sites.txt -o ./copias
```

Cada site vai para `./copias/<host>/` e um `./copias/index.html` lista todos.
Um site que falhar não interrompe os demais.

## Opções principais

| Flag | Padrão | Descrição |
|------|--------|-----------|
| `url ...` | — | Uma ou mais URLs iniciais. |
| `-i, --urls-file` | — | Arquivo com uma URL por linha (`#` = comentário). |
| `-o, --out` | `site-copy` | Diretório de saída. |
| `--max-pages` | `500` | Máximo de páginas HTML a baixar. |
| `--max-depth` | `10` | Profundidade máxima de links a partir da URL inicial. |
| `--workers` | `4` | Downloads simultâneos. |
| `--delay` | `0` | Pausa (s) após cada request, por worker. |
| `--same-host-assets` | off | Só baixa assets do domínio inicial. |
| `--allow-host HOST` | — | Permite rastrear páginas de outro host (repetível). |
| `--respect-robots` | off | Obedece ao `robots.txt` do site. |
| `--timeout` | `30` | Timeout por request (s). |
| `-q, --quiet` | off | Silencia o progresso. |

## Como funciona

1. **Crawl (BFS):** a partir da URL inicial, segue links `<a>`/`<iframe>` dentro
   do mesmo host (respeitando `--max-depth` e `--max-pages`) e coleta assets de
   `img`, `script`, `link`, `source`, `srcset`, `style`, `url()` de CSS, etc.
2. **Download:** cada recurso é salvo em `<out>/<host>/<caminho>`. URLs sem
   extensão viram páginas de diretório (`/sobre` → `sobre/index.html`); query
   strings recebem um sufixo de hash para evitar colisões.
3. **Rewrite:** ao final, links em HTML/CSS são reescritos para caminhos
   relativos locais (recursos baixados) ou mantidos como URL absoluta (recursos
   externos não baixados).
4. **Manifesto:** um `manifest.json` lista todos os recursos copiados e erros.

## Uso responsável

Copiar um site consome banda e pode violar os termos de uso. Use apenas em
sites próprios ou com autorização. Prefira `--respect-robots`, `--delay` e um
número baixo de `--workers` para não sobrecarregar o servidor.

## Testes

```bash
python -m unittest discover -s tests
```
