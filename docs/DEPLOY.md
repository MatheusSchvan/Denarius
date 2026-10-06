# Publicar uma demonstração online

Esta configuração publica o MVP como uma demonstração **com os dados fictícios do projeto**. Ela mantém as telas e operações de importação, edição, exclusão e relatórios, protegidas por um usuário e uma senha compartilhados. Os dados da demo são carregados automaticamente na primeira inicialização.

O modo local continua independente: `iniciar.bat` usa a base pessoal no seu computador. A publicação usa uma base SQLite separada em `/tmp/financeiro-demo`; o Docker não inclui seu diretório `data/`, bancos pessoais, backups ou `.env`.

## Antes de publicar

O repositório precisa conter `Dockerfile`, `.dockerignore`, `render.yaml`, `backend/`, `frontend/` e `exemplos/` na **raiz**. Se os arquivos vieram de um ZIP, copie o conteúdo da pasta `financeiro-pessoal` para a raiz do seu repositório atual, preservando `.git`. Não aninhe uma segunda pasta `financeiro-pessoal`.

Não coloque extratos pessoais nem arquivos do banco no repositório. O `.gitignore` evita adicionar `data/`, `.venv/` e `node_modules/` por acidente. Confira `git status` antes de fazer o commit.

```powershell
git status
git add .
git commit -m "chore: preparar demonstracao online com Docker"
git push
```

## Publicar no Render

1. Entre em [Render](https://dashboard.render.com/) e conecte o repositório que contém `render.yaml` na raiz.
2. Crie uma **Blueprint** a partir desse repositório. O arquivo configura um Web Service Docker no plano gratuito, com `/api/health` como verificação de inicialização.
3. Quando o Render pedir `FINANCEIRO_DEMO_PASSWORD`, informe uma senha exclusiva com **pelo menos 14 caracteres**. O usuário inicial é `demo`. A senha fica como variável privada no Render e não deve ir para o Git.
4. Aguarde o build e abra o endereço `https://...onrender.com` mostrado no painel. O navegador solicitará usuário e senha.
5. Confirme que aparecem os 24 lançamentos fictícios, a nota de exemplo e o mês de setembro de 2026. Teste uma operação de edição e a tela de relatórios.

O Render fornece `RENDER_EXTERNAL_HOSTNAME` automaticamente. O backend usa esse nome para aceitar requisições feitas pelo endereço HTTPS do serviço e recusa origens diferentes. A senha também protege os arquivos da interface e as rotas da API, exceto `/api/health`, que é usada pelo monitoramento. Sem senha configurada, a demo **falha na inicialização**.

Essa é uma instalação **de demonstração com dados compartilhados**: quem receber a senha verá as mesmas alterações. Evite importar OFX ou notas pessoais. A faixa no topo do aplicativo lembra que os dados são temporários.

### Persistência no plano gratuito

No plano gratuito do Render, o armazenamento da instância é temporário. O serviço pode dormir após um período sem acessos e levar algum tempo para acordar. Reinícios, novos deploys ou suspensões apagam as alterações feitas na base SQLite; na inicialização seguinte, os exemplos são carregados de novo. Use o aplicativo local para dados pessoais e permanentes. Um sistema online persistente exigiria uma estrutura própria para armazenamento, contas de usuários e rotinas de backup.

Os termos e limites do plano podem mudar; confira a [documentação do plano gratuito](https://render.com/docs/free). A [referência de Blueprints](https://render.com/docs/blueprint-spec) explica o formato do `render.yaml`.

## Testar o contêiner no próprio computador

Se tiver Docker instalado, execute na raiz do projeto. A senha abaixo serve apenas para um teste local; use outra senha na publicação.

```powershell
docker build -t financeiro-demo .
docker run --rm -p 127.0.0.1:10000:10000 -e FINANCEIRO_DEMO_MODE=1 -e FINANCEIRO_DEMO_USER=demo -e FINANCEIRO_DEMO_PASSWORD=exemplo-local-123456 -e RENDER_EXTERNAL_HOSTNAME=localhost -e FINANCEIRO_DATA_DIR=/tmp/financeiro-demo financeiro-demo
```

Abra `http://localhost:10000` e informe o usuário `demo` e a senha do comando. O banco desse teste fica no contêiner e desaparece quando ele é removido. O login HTTP Basic só deve ser usado por HTTPS na publicação; no exemplo acima, a porta fica restrita ao seu próprio computador.

## Ajustes e manutenção

- Para trocar a senha online, altere `FINANCEIRO_DEMO_PASSWORD` nas variáveis do serviço Render e reinicie o serviço. O navegador pode manter credenciais anteriores até fechar a janela.
- Para recomeçar a apresentação, faça um novo deploy ou reinicie a instância: como os dados do plano gratuito são temporários, os exemplos voltam na próxima inicialização. Também é possível limpar os dados pela interface e depois carregar os exemplos novamente.
- Ao atualizar o código, faça commit e push. A Blueprint acompanha os commits da branch conectada. Confira o resultado em **Deploys** no painel.
- Se o domínio personalizado for usado no futuro, ajuste também a lista de hosts/origens aceitos pelo backend; o pacote inicial cobre o domínio padrão `onrender.com`.

Esta entrega prepara os arquivos e valida o modo de demonstração. A criação do serviço precisa da sua conta e do repositório conectado no Render.
