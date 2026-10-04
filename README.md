# Financeiro pessoal

**Parte 3/3.** Comece por [COMECE_AQUI.md](COMECE_AQUI.md) para instalar ou atualizar. Esta etapa acrescenta tema claro/escuro/sistema, relatório mensal com gráficos, download PNG, CSV por mês e impressão/PDF. Mantém saldos, exclusão, lixeira e backup da parte 2. O esquema do banco permanece na versão 2; bases da parte 1 são migradas automaticamente.

Um aplicativo local para juntar extratos bancários e entender melhor os gastos do mês.

A ideia começou com uma limitação do extrato: ele mostra quanto foi gasto no mercado, mas não mostra o que foi comprado. O projeto importa o OFX para registrar a movimentação e usa a nota fiscal para detalhar essa mesma compra. Vincular uma nota não cria uma segunda despesa.

Esta é uma primeira versão para demonstração e continuidade do projeto. Os exemplos são fictícios.

## Rodar no Windows

1. Instale **Python 3.11 ou mais recente**, pela distribuição oficial. Na instalação, marque a opção de adicionar o Python ao PATH.
2. Extraia **a pasta inteira** do ZIP para uma pasta comum, como `Documentos/financeiro-pessoal`. Não execute de dentro do ZIP.
3. Abra `iniciar.bat` com dois cliques.
4. Na primeira execução, aguarde a instalação das dependências. Essa etapa precisa de internet.
5. O navegador abre em **http://127.0.0.1:8765**. Se não abrir sozinho, digite esse endereço.

Mantenha a janela do programa aberta enquanto usa o sistema. Para encerrar, pressione `Ctrl+C` nela. Depois da primeira instalação, o uso normal funciona sem internet.

**Não precisa instalar Node para usar o ZIP entregue.** A interface compilada já está em `frontend/dist`. O código-fonte também está incluído.

No Linux ou macOS, execute `python3 iniciar.py` na pasta do projeto. Algumas distribuições Linux exigem o pacote `python3-venv`.

## Demonstração rápida

Na primeira tela, clique em **Usar dados de exemplo**. O aplicativo carrega 24 movimentos de agosto e setembro de 2026 e uma nota de mercado com 12 produtos. O botão só funciona em uma base vazia, para evitar misturar exemplos com dados pessoais.

Selecione **setembro de 2026**. Abra **Notas de compra**, confira a nota do Mercado Bom Dia e vincule à compra de **R$ 252,91**, em **09/09/2026**. Volte ao resumo: o total de despesas permanece igual.

Para mostrar o importador funcionando, use os arquivos de `exemplos/`. Reimporte os dois OFX: a tela deve informar que os 24 lançamentos já existem, sem criar novos.

O roteiro com os passos da apresentação está em [docs/APRESENTACAO.md](docs/APRESENTACAO.md).

## O que funciona nesta versão

| Área | Funcionalidade |
| --- | --- |
| Visão geral | Entradas, despesas, resultado do mês, categorias, comparação mensal e pendências |
| Lançamentos | Busca, filtros de mês/categoria/banco, revisão, classificação e observação |
| Cadastro manual | Entrada, despesa, transferência, investimento ou ajuste |
| Importações | OFX de conta e cartão, seleção de vários arquivos, prévia e histórico |
| Duplicidade | Identificador bancário por conta e revisão de coincidências sem identificador |
| Notas | Leitura de XML de NF-e/NFC-e, itens, classificação dos produtos e vínculo reversível com a compra |
| Dados | SQLite local, exportação CSV e download de backup |
| Saldos | Contábil e disponível do OFX, data de referência e registro manual |
| Configurações | Lixeira, restauração individual e limpeza com backup automático |
| Aparência | Tema claro, escuro ou do sistema, com preferência salva no navegador |
| Relatórios | Resumo mensal e gráficos, PNG, CSV do mês e impressão para PDF |

O resumo usa a categoria do **lançamento**. As categorias dos **produtos** ficam no detalhamento da nota, prontas para um relatório específico em uma próxima versão.

## Regras principais

- Os valores são armazenados em **centavos inteiros**. A conta de R$ 0,10 + R$ 0,20 resulta em 30 centavos.
- A identidade bancária combina instituição, tipo de origem, agência, conta e `FITID`. O identificador da conta é guardado como hash no cadastro dos lançamentos; o arquivo original permanece no banco local.
- Reimportar o mesmo arquivo, mesmo renomeado, não duplica os movimentos. Extratos sobrepostos acrescentam apenas os identificadores novos.
- Se o mesmo `FITID` vier com dados diferentes, o arquivo é rejeitado para conferência. Ele não sobrescreve um lançamento existente.
- Sem `FITID`, registros coincidentes entram como **possível duplicata** e ficam fora do resumo até a decisão do usuário. A decisão é entre confirmar como outro movimento ou descartar a cópia.
- A nota pode ser vinculada a uma despesa confirmada com **valor exatamente igual** e data a **até três dias**. A sugestão usa valor e data; conferir o estabelecimento é parte da confirmação.
- O MVP permite uma nota por lançamento. A soma dos itens precisa fechar com o total para o vínculo ser liberado.
- Transferências, investimentos e ajustes ficam fora de receitas e despesas. **O pagamento de uma fatura precisa ser classificado manualmente como transferência quando as compras do cartão já estiverem importadas.** A classificação automática não resolve essa relação.
- O “resultado do mês” é entradas menos despesas dos registros presentes. **Não é o saldo bancário.**

## Organização do código

- `backend/app/main.py`: API, validações de entrada e operações do aplicativo.
- `backend/app/ofx.py`: leitura e normalização dos extratos.
- `backend/app/imports.py`: prévia, deduplicação e gravação dos lotes.
- `backend/app/receipts.py`: extração dos itens da nota XML.
- `backend/app/domain.py`: centavos, datas, categorias e regras iniciais.
- `backend/app/db.py` e `schema.sql`: conexão e criação versionada do banco.
- `backend/app/migration_002.sql`: atualização da base para armazenar contas e saldos.
- `backend/app/management.py`: saldos, lixeira e limpeza com backup.
- `backend/tests/`: testes das regras financeiras e dos fluxos da API.
- `frontend/src/pages/`: as sete telas em React e TypeScript, incluindo `Reports.tsx` para gráficos e exportação.
- `frontend/src/theme.ts` e `themes.css`: preferência de tema, modo escuro e impressão.
- `frontend/src/api.ts`: acesso à API e formatação.
- `frontend/src/styles.css`: estilo da interface, sem framework visual.
- `exemplos/`: dois OFX e um XML didático.
- `data/`: banco gerado na primeira execução.

Os detalhes de arquitetura estão em [docs/ARQUITETURA.md](docs/ARQUITETURA.md). Não há serviços externos de IA, telemetria nem integração bancária.

## Desenvolver

Para alterar a interface, use **Node 22.12+** ou **24+** e Python 3.11+. Os comandos abaixo são executados a partir da pasta do projeto.

Primeiro prepare o backend:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements-dev.txt
```

Em um terminal:

```powershell
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

Em outro:

```powershell
cd frontend
npm ci
npm run dev
```

Abra `http://127.0.0.1:5173`. O Vite encaminha `/api` para o backend. Para atualizar a interface usada pelo iniciador, execute `npm run build` dentro de `frontend` e reinicie o aplicativo.

No Linux/macOS, troque `.venv\Scripts\python` por `.venv/bin/python` e ajuste as barras dos caminhos.

## Testar

Na raiz do projeto:

```powershell
.venv\Scripts\python -m pytest -q
```

Os testes criam bases temporárias e não usam o banco pessoal. Cobrem reimportação, sobreposição de OFX, identidade por conta, conflitos de `FITID`, registros sem identificador, importação simultânea, centavos, validações, notas, dupla contagem, backup e exportação CSV.

Para verificar os tipos e compilar a interface:

```powershell
cd frontend
npm run build
```

## Backup e dados

Os dados ficam em `data/financeiro.sqlite3`, incluindo os arquivos originais importados. **Fazer backup**, no menu, baixa uma cópia consistente desse banco. O CSV serve para consultar os lançamentos e não substitui o backup completo.

Para restaurar: encerre o aplicativo, guarde uma cópia do banco atual, copie o backup para `data/` com o nome `financeiro.sqlite3` e inicie novamente. A restauração por tela fica para uma próxima versão.

Para experimentar sem misturar com sua base, use outra pasta de dados. No PowerShell:

```powershell
$env:FINANCEIRO_DATA_DIR = "$PWD\data-demonstracao"
py -3 iniciar.py
```

Fechar esse terminal encerra a configuração temporária. O banco é local e não tem criptografia própria; proteja o acesso ao computador e às cópias de backup.

## Limites e próximos passos

Esta entrega lê o subconjunto usual de OFX 1.x/2.x de contas e cartões em BRL. Os testes usam exemplos controlados; ainda é necessário validar os adaptadores com extratos reais dos bancos desejados. OFX de investimentos, correções bancárias e conversão cambial não são suportados.

A nota é lida pelo XML, sem consulta à SEFAZ ou verificação da assinatura fiscal. Fotos, PDF, QR Code e OCR ainda não estão implementados. Documentos com diferença entre itens e total são sinalizados e não podem ser conciliados nesta versão. Não há divisão de pagamento nem vínculo de várias notas na mesma compra.

Por enquanto, a edição de lançamentos ajusta tipo, categoria e observação. Data, descrição e valor permanecem como cadastrados; a edição completa de registros manuais e um histórico de alterações são uma próxima melhoria. Já há saldo reportado e cadastro manual de saldo, mas não há parcelamento, tela de investimentos ou regras criadas pelo usuário. A conciliação entre saldo e movimentações incompletas permanece futura.

O programa é para uma pessoa, no próprio computador. Não foi preparado para publicar na internet. A sequência sugerida para continuar é:

1. Validar OFX reais e separar adaptadores quando houver diferenças entre bancos.
2. Melhorar a edição manual e criar regras de classificação pela interface.
3. Adicionar parcelas, investimentos e conciliação entre saldo e movimentos.
4. Criar relatórios por produto e histórico de preços.
5. Implementar leitura de imagem/PDF com revisão dos resultados.

## Referências técnicas

- [FastAPI: envio de arquivos](https://fastapi.tiangolo.com/tutorial/request-files/)
- [Vite: configuração e execução](https://vite.dev/guide/)
- [Python: SQLite](https://docs.python.org/3/library/sqlite3.html)
