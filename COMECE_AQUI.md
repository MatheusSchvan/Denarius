# Parte 3 de 3 — Tema e relatórios

Esta é a base completa da sequência para apresentar ao professor e continuar desenvolvendo. Inclui tudo das partes 1 e 2. Ainda é um MVP: não lê fotos ou PDF de notas e não consulta o banco online.

## O que entrou

- **Tema:** no topo de qualquer tela, escolha Claro, Escuro ou Sistema. A escolha fica salva no navegador; Claro é o padrão. Sistema acompanha a preferência do computador.
- **Relatórios:** escolha o mês para ver entradas, despesas, resultado, despesas por categoria e comparação de até seis meses com movimentação.
- **Baixar PNG:** salva o relatório com gráficos em uma imagem de 2.000 pixels de largura, pronta para colocar em um slide.
- **CSV do mês:** baixa os lançamentos ativos do período selecionado. Pendências aparecem identificadas na coluna de revisão; ficam fora dos totais dos gráficos.
- **Imprimir / PDF:** abre a impressão do navegador; escolha Salvar como PDF. O relatório usa fundo claro mesmo se o aplicativo estiver no tema escuro.

Continuam disponíveis OFX de conta e cartão, notas XML com conciliação, lançamentos manuais, saldos com data, lixeira, restauração e limpeza com backup. O resultado mensal não é o saldo bancário; a nota detalha uma compra sem somar o gasto novamente.

## Atualizar a parte 2

1. Clique em **Fazer backup** e feche o programa.
2. Extraia este ZIP em uma pasta temporária.
3. Copie o conteúdo de `financeiro-pessoal` para a pasta do seu repositório, substituindo os arquivos do código. Preserve `.git`, `.venv`, `data` e seus backups. Não apague a pasta antiga inteira e não crie outra pasta `financeiro-pessoal` dentro dela.
4. Abra `iniciar.bat`. A interface já está compilada; não precisa instalar Node para usar o ZIP.
5. Confira o tema no topo e a nova tela **Relatórios**. Se o navegador ainda mostrar a versão antiga, pressione Ctrl+F5.

Esta etapa mantém o esquema do banco da parte 2. Se vier direto da parte 1, a migração para o esquema 2 é automática; reimporte o OFX para carregar saldos sem duplicar lançamentos. Não abra uma base atualizada usando o código da parte 1.

## Instalação nova

Instale Python 3.11 ou superior, extraia a pasta inteira e execute `iniciar.bat`. A primeira execução precisa de internet para instalar dependências. Depois disso, o uso é local. No Linux/macOS, use `python3 iniciar.py`.

Para instalar as dependências manualmente, na raiz do projeto:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements.txt
py -3 iniciar.py
```

Em uma base vazia, clique em **Usar dados de exemplo**. São dados fictícios de agosto e setembro de 2026. Nenhum banco pessoal foi incluído neste ZIP.

## Fazer o commit 3

Na pasta do repositório que já contém os commits anteriores:

```powershell
git status
git add .
git commit -m "feat: adicionar tema escuro e exportacao de relatorios"
git push
```

O push pressupõe que o remoto já está configurado. O ZIP não traz `.git` nem cria commits automaticamente. Dados pessoais, bancos e backups devem ficar fora do Git. A pasta `frontend/dist` vem no ZIP para execução, mas é ignorada pelo Git; após clonar o repositório, compile com `npm ci` e `npm run build` dentro de `frontend`.

## Demonstração em poucos passos

Carregue os exemplos, selecione setembro de 2026 e mostre o resumo. Vincule a nota de R$ 252,91 à compra de mesmo valor: as despesas não mudam. Abra Saldos para mostrar a data do valor informado no OFX. Exclua um lançamento sem nota e restaure em Configurações. Alterne o tema, abra Relatórios e baixe um PNG.

A limpeza de todos os lançamentos apaga o histórico de importações e desvincula as notas, permitindo reimportar. A limpeza de toda a base também apaga notas, contas e saldos. Ambas criam backup antes; recuperação em lote é manual, conforme o README. A escolha de tema permanece salva no navegador.
