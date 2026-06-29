# Como copiar marca-passos.com para o seu professor

## Pré-requisitos
- Python 3.8+ instalado na sua máquina (`python3 --version`)
- Git (para clonar o repositório)

## Passo a passo

### 1. Clone o repositório
```bash
git clone https://github.com/brucedsny/job-agent
cd job-agent
git checkout claude/website-scraper-agent-fqa6vc
```

### 2. Execute o script de cópia
```bash
chmod +x copiar.sh
./copiar.sh
```

Isso vai:
- Baixar todas as páginas do site marca-passos.com
- Salvar em uma pasta chamada `marca-passos/`
- Reescrever os links para funcionar offline
- Respeitar o `robots.txt` do site (bom cidadão)
- Esperar 0.5s entre cada request (não sobrecarrega)

**Tempo esperado:** 5-15 minutos (depende da conexão e tamanho do site).

### 3. Compartilhe com seu professor
A pasta `marca-passos/` contém tudo. Abra no navegador:
```
marca-passos/www.marca-passos.com/index.html
```

Pronto! Ele pode navegar pelo site inteiro **offline**, mesmo sem internet.

## Customizações (opcional)

Se quiser salvar em outro local:
```bash
./copiar.sh /seu/caminho
```

Para um crawl mais profundo (mais páginas):
```bash
python3 -m site_copier https://www.marca-passos.com/ -o marca-passos \
  --max-pages 2000 --max-depth 20 --respect-robots --delay 0.5 --workers 2
```

## Troubleshooting

**"command not found: python3"**  
→ Instale Python 3 (https://python.org) ou use `python` em vez de `python3`

**"ModuleNotFoundError"**  
→ Garanta que está na pasta correta: `cd job-agent`

**Site não copia completamente**  
→ Aumente `--max-pages` ou `--max-depth` no comando acima

## Dúvidas?
Veja `site_copier/README.md` para opções completas.
