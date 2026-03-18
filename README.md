# Painel Salesforce para TV (Windows Server)

Projeto de dashboard web externo para exibir 3 relatorios Salesforce em colunas com atualizacao automatica para uso em Smart TV/NOC.

## 1) Arquitetura da Solucao

Arquitetura em 3 camadas:

- Frontend (`HTML + CSS + JS`): renderiza 3 colunas e atualiza sem interacao do usuario.
- Backend (`FastAPI`): expone endpoint local `/api/dashboard`.
- Integracao Salesforce (`requests + JWT Bearer Flow`): autentica, busca relatorios via Analytics API, normaliza payload.

Fluxo de dados:

1. Browser da TV acessa `http://localhost:8080`.
2. JS chama `GET /api/dashboard`.
3. Backend autentica no Salesforce (cache de token) e consulta os 3 relatorios.
4. Backend retorna JSON consolidado com `generatedAt`, `refreshSeconds`, `columns`, `errors`, `salesforceStatus` e aliases (`transportadora`, `cliente`, `dia`).
5. Frontend redesenha as 3 colunas e reinicia countdown de refresh.

## 2) Fluxo de autenticacao JWT (OAuth 2.0 JWT Bearer)

Implementado em `app/services/salesforce_auth.py`.

1. Leitura da chave privada (`SF_PRIVATE_KEY_PATH`).
2. Geracao de JWT com claims:
- `iss`: Consumer Key
- `sub`: username de integracao
- `aud`: `https://login.salesforce.com` (ou sandbox)
- `exp`/`iat`: validade curta
- `jti`: nonce unico
3. POST para `/services/oauth2/token` com:
- `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer`
- `assertion=<jwt assinado>`
- `client_id` e `client_secret`
4. Recebe `access_token` e `instance_url`.
5. Token fica em cache em memoria com renovacao automatica quando expira.

## 3) Consumo dos relatorios Salesforce API

Endpoint usado por relatorio:

`/services/data/{version}/analytics/reports/{reportId}?includeDetails=true`

Implementacao em `app/services/salesforce_reports.py`:

- Consulta cada report ID configurado no `.env`.
- Le `reportMetadata.detailColumns` para cabecalhos.
- Le `factMap` para linhas detalhadas e agregacoes (summary/matrix).
- Converte em lista de objetos para facilitar renderizacao no frontend.
- Trata erros por coluna sem derrubar dashboard inteiro.

## 4) Estrutura do backend

- `app/main.py`: inicializacao FastAPI e rota `/` para frontend.
- `app/api/dashboard.py`: endpoints `/api/health` e `/api/dashboard`.
- `app/core/config.py`: configuracoes por variavel de ambiente.
- `app/core/logging_config.py`: log padrao da aplicacao.
- `app/services/salesforce_auth.py`: autenticacao JWT.
- `app/services/salesforce_reports.py`: consumo e consolidacao dos relatorios.

## 5) Estrutura do frontend

- `app/static/index.html`: estrutura visual do painel.
- `app/static/styles.css`: estilo widescreen para TV, tipografia grande, colunas e contraste.
- `app/static/app.js`: fetch dos dados, renderizacao de cards, contador de refresh e indicador de ultima atualizacao.

## 6) Refresh automatico

Implementacao no frontend + backend:

- `setInterval` para countdown visual por segundo.
- loop de refresh baseado em `refreshSeconds` retornado pelo backend.
- cache no backend (`SF_REPORT_CACHE_SECONDS`) para nao consultar Salesforce a cada refresh da TV.
- fallback automatico para ultimo snapshot valido em indisponibilidade do Salesforce.
- ao atualizar dados:
- atualiza `Ultima atualizacao`
- reinicia contagem regressiva
- redesenha colunas

Valor padrao configuravel:

- `.env` -> `REFRESH_DEFAULT_SECONDS=30` (ou `60`)
- `.env` -> `SF_REPORT_CACHE_SECONDS=120`

## 7) Estrutura de pastas

```text
Painel tv/
  app/
    api/
      dashboard.py
    core/
      config.py
      logging_config.py
    services/
      salesforce_auth.py
      salesforce_reports.py
    static/
      index.html
      styles.css
      app.js
    main.py
  scripts/
    start_dashboard.ps1
    install_service.ps1
    create_tv_kiosk_task.ps1
  .env.example
  requirements.txt
  run.ps1
  README.md
```

## 8) Instalacao de dependencias

### Pre-requisitos

- Windows Server 2022
- Python 3.11+
- Connected App (Manage External Client Apps) configurada para JWT
- Chave privada `.key` correspondente ao certificado cadastrado na Connected App

### Passos

1. Copie `.env.example` para `.env` e preencha credenciais.
2. Garanta que `SF_PRIVATE_KEY_PATH` aponte para a chave privada.
3. Execute:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
.\run.ps1 -Port 8080
```

4. Abra no navegador:

`http://localhost:8080`

Para Smart TVs em rede, use o IP do servidor:

`http://IP_DO_SERVIDOR:8080`

## 9) Deploy no Windows Server

### Opcao A (simples)

- Deixe a aplicacao rodando em sessao dedicada via `scripts/start_dashboard.ps1`.

### Opcao B (inicializacao automatica)

- Use `scripts/install_service.ps1` para criar servico do Windows em modo automatico.

Exemplo:

```powershell
.\scripts\install_service.ps1 -ProjectPath "E:\PROJETOS DEV\Painel tv" -Port 8080
```

## 10) Abrir automaticamente na TV

Use modo kiosk do Edge com task no logon:

```powershell
.\scripts\create_tv_kiosk_task.ps1 -DashboardUrl "http://localhost:8080"
```

Isso cria uma tarefa agendada que abre o painel em fullscreen:

- `--kiosk`
- `--edge-kiosk-type=fullscreen`

## 11) Seguranca e boas praticas

- Nunca versionar `.env` e chave privada.
- Usar usuario de integracao com menor privilegio possivel.
- Restringir IP/rede no firewall do servidor.
- Ativar HTTPS reverso (IIS/Nginx) em ambientes expostos.
- Logs com monitoramento de falhas de autenticacao/API.
- Configurar rotacao de chave/certificado periodica.

## 12) Sugestoes de melhoria

1. Cache por relatorio com TTL curto para reduzir chamadas API.
2. WebSocket/SSE para push de atualizacao em vez de polling.
3. Paginacao/rotacao de registros se volume crescer.
4. Mapeamento amigavel de colunas (label custom) no backend.
5. Healthcheck externo e alerta (Teams/Email) se API falhar.
6. Empacotamento com Docker + NSSM para operacao simplificada.

## Endpoint local

- Health: `GET /api/health`
- Dados dashboard: `GET /api/dashboard`
