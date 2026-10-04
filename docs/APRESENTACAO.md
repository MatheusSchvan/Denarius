# Roteiro de apresentação

Tempo sugerido: de 5 a 7 minutos. Abra o aplicativo e confira a instalação antes da aula. A instalação inicial precisa de internet; a demonstração depois disso é local.

## 1. O problema

“Eu queria juntar os extratos em um lugar só, mas também entender as compras de mercado. No extrato aparece uma despesa de R$ 252,91. Na nota aparecem os produtos. A proposta é unir essas informações sem contar o gasto duas vezes.”

## 2. O que já existe

Mostre as telas: visão geral, lançamentos, importações, notas de compra, saldos, configurações e relatórios. Explique que esta versão trabalha com arquivos exportados pelo usuário. Ela não acessa a conta bancária.

Se a base estiver vazia, clique em **Usar dados de exemplo**. São 24 lançamentos fictícios e uma nota de mercado. Selecione **setembro de 2026**.

## 3. Importação e duplicidade

Abra **Importações**, selecione `conta-exemplo.ofx` e `cartao-exemplo.ofx`, na pasta `exemplos`, e confira a prévia. Como os exemplos já foram carregados, todos os registros aparecerão como existentes. Confirme e mostre o histórico com zero novos lançamentos.

“O banco costuma exportar períodos sobrepostos. Por isso, o sistema precisa reconhecer que a mesma transação já foi importada. Quando o arquivo não tem um identificador confiável, o sistema pede revisão.”

## 4. Consulta e classificação

Abra **Lançamentos**. Pesquise `PIX CARLA`. Edite a categoria para `Compras` e adicione uma observação curta. Salve e mostre a alteração.

Os filtros permitem separar mês, banco, categoria e pendências. O cadastro manual serve para movimentos que não estão no extrato, como uma compra paga em dinheiro.

## 5. A parte principal: a nota

Antes de vincular, anote ou mostre o valor de despesas no resumo. Na base de exemplo, setembro tem:

| Medida | Valor |
| --- | ---: |
| Entradas | R$ 3.850,00 |
| Despesas | R$ 1.985,41 |
| Resultado | R$ 1.864,59 |

Abra **Notas de compra** e clique em **Conferir** na nota do Mercado Bom Dia. Mostre os 12 produtos, escolha a compra de R$ 252,91 do dia 09/09/2026 e confirme o vínculo. Classifique um sabonete como `Higiene` ou um detergente como `Limpeza`.

Volte à visão geral. A despesa continua em R$ 1.985,41. Esse é o principal critério do projeto: a nota explica o gasto, sem criar outro lançamento.

Se você cadastrou movimentos manuais antes desse passo, os totais serão diferentes dos da tabela. O importante é comparar imediatamente antes e depois do vínculo.

## 6. Como foi construído

Antes de explicar o código, abra **Saldos**: a conta de exemplo informa **R$ 4.295,98**, com referência em **15/09/2026**. Esse valor vem do extrato; é diferente do resultado mensal. O cartão aparece separado do total de contas.

Em **Lançamentos**, exclua um movimento sem nota vinculada. Abra **Configurações** e restaure pela lixeira. A limpeza de todos os lançamentos fica nessa mesma tela e cria um backup antes de apagar. Demonstre a limpeza apenas no final, usando a base fictícia.

“A interface foi feita em React com TypeScript. O backend usa Python e FastAPI, e os dados ficam em SQLite. Separei a leitura de OFX, a importação e a leitura das notas para poder evoluir cada parte. Os valores monetários são armazenados em centavos, e há testes para duplicidade e conciliação.”

Não precisa explicar todos os arquivos. Se o professor perguntar sobre o banco, mostre o diagrama em `ARQUITETURA.md` e as tabelas de lançamentos, notas, itens e importações.

## 7. O que fica para depois

Antes de encerrar, alterne **Tema → Escuro** no topo. Abra **Relatórios**, selecione setembro de 2026 e mostre que as despesas são as mesmas da visão geral. Clique em **Baixar PNG** para levar o gráfico ao slide. O botão **CSV do mês** exporta os lançamentos; **Imprimir / PDF** permite salvar o relatório como PDF pela impressão do navegador.

“O recorte desta versão foi validar a importação e o vínculo da nota. A leitura de fotos ainda não está pronta. Depois entram OCR com revisão, relatórios por produto e histórico de preços. Também quero melhorar os lançamentos manuais e testar com extratos de outros bancos.”

Caso perguntem sobre pagamentos de cartão: a classificação de fatura como transferência é manual neste MVP. O sistema ainda não reconhece sozinho a relação entre o débito na conta e a fatura do cartão.

## Se precisar repetir do zero

Use uma pasta nova para os dados de demonstração, como descrito no README. Não apague o banco que contém seus dados. Em uma base vazia, você pode importar os dois OFX pela tela, importar o XML e fazer todo o fluxo sem usar o botão de exemplos.
