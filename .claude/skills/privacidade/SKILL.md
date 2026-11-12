---
name: privacidade
description: Auditoria de privacidade do usuário e da família — repositório no GitHub, dados pessoais nos arquivos e no histórico do git, compartilhamento do Drive, conectores e configurações recomendadas. Use para "privacidade", "segurança" ou "quem pode ver", antes de publicar algo e quando o hook de início de sessão avisar de risco.
---

# privacidade — auditoria e alerta

Objetivo: a maior privacidade possível para o usuário e para a família, e um
aviso imediato quando houver risco. Nunca imprima segredos, senhas, códigos de
verificação, SSN, CPF, números de prontuário ou datas de nascimento: diga só
ONDE está o problema.

## 1. Checar (nesta ordem)

1. **Repositório GitHub** — visibilidade:
   `curl -s https://api.github.com/repos/<owner>/<repo> | jq -r .visibility`
   (privado responde 404/sem campo). Se `public`: risco ALTO.
2. **Arquivos versionados** — padrões sensíveis (SSN, CPF, data de nascimento,
   telefones, e-mails pessoais, nomes de familiares, números de processo,
   prontuário): `git ls-files | xargs grep -nIE '<padrões>'`. Para os nomes e
   números do caso, monte a lista a partir do `03_CONTATOS` e do `01_FATOS`
   num arquivo do scratchpad (nunca no repositório) e use
   `git ls-files -z | xargs -0 grep -nIF -f <lista> | cut -d: -f1,2`. Reporte
   arquivo e linha, não o valor.
3. **Histórico do git** — os mesmos padrões em `git log --all -p` (contagem por
   padrão). Dado já publicado continua no histórico até reescrita.
4. **Google Drive** — `get_file_permissions` na pasta raiz do caso (id no
   CLAUDE.md), nos documentos centrais (`00_ESTADO_ATUAL` a `04_MAPA_DA_PASTA`)
   e nas pastas 10–90. Risco se houver "anyone with the link", domínio ou
   pessoas fora da família autorizada. O id da raiz está neste repositório
   público: a raiz tem de ficar "Restricted" (risco ALTO se não estiver).
5. **Conectores** — liste quais estão ligados (Gmail, Drive, Calendar etc.) e o
   que cada um permite. Não desligue nada sem o usuário pedir.

## 2. Responder (curto, em português, com frases simples)

- Primeira linha: 🔴/🟡/🟢 com o risco mais alto.
- Tabela: o que foi checado · resultado · o que fazer (passo a passo de cliques).
- O que só o usuário pode fazer (ex.: mudar visibilidade do repositório, ativar
  verificação em duas etapas) vs. o que o Claude pode fazer (ex.: tirar nomes
  de arquivos do repositório — só com autorização; reescrever histórico ou
  mexer na branch padrão — só com autorização explícita).

## 3. Configurações recomendadas (checklist para o usuário)

- **Claude (claude.ai):** Settings → Privacy → desligar "Help improve Claude";
  apagar conversas antigas; chat incógnito para assuntos isolados; revisar
  Connectors.
- **ChatGPT:** Settings → Data Controls → desligar "Improve the model for
  everyone"; Temporary Chat; revisar Memory.
- **Google:** myaccount.google.com/security → Security Checkup; verificação em
  duas etapas com passkey ou chave física (opção máxima: Advanced Protection);
  revisar apps de terceiros com acesso; Gmail → Forwarding sem encaminhamentos
  desconhecidos; Drive com compartilhamento "Restricted".
- **GitHub:** repositórios pessoais como Private; verificação em duas etapas
  com passkey + códigos de recuperação guardados fora do celular.
- **Celular:** bloqueio de tela; documentos (SSN, green card, passaporte) fora
  do rolo da câmera.

## 4. Regras

- Dados de paciente e documentos pessoais nunca entram no repositório.
- Ao criar arquivo, skill, artifact ou publicação: perguntar "isso expõe alguém?"
  antes de salvar ou publicar.
- Se o hook de início de sessão avisar de risco, mencionar na primeira linha da
  resposta, mesmo que o assunto seja outro.
