# Validação da parte 3

Foram executados 30 testes automatizados da API, com bases temporárias. Incluem importação, deduplicação, conciliação, saldos, migração da parte 1, exclusão, restauração e backup. O novo teste verifica que o CSV mensal contém apenas registros ativos daquele mês, mantém o valor de despesas do resumo, rejeita mês inválido e preserva a exportação completa sem filtro.

O TypeScript foi verificado e a interface foi compilada com `npm run build`. O componente SVG do relatório foi renderizado com os dados fictícios de setembro de 2026 e sua imagem foi inspecionada: os totais são R$ 3.850,00 de entradas, R$ 1.985,41 de despesas e R$ 1.864,59 de resultado.

O navegador de teste remoto não conseguiu acessar o servidor local. Portanto, a interação com o seletor de tema, o download PNG pelo navegador e a impressão/PDF ainda precisam da conferência local abaixo. A renderização inspecionada do SVG não substitui esse teste de download.

## Conferência rápida antes da apresentação

1. Abra o aplicativo e alterne Tema entre Claro e Escuro. Recarregue a página e confira se a escolha permaneceu. Sistema deve acompanhar a aparência do computador.
2. Com os exemplos carregados, selecione setembro de 2026. Em Relatórios, compare os três totais com a Visão geral.
3. Clique em Baixar PNG, abra a imagem e confira os gráficos. A imagem deve ter fundo branco, inclusive com o aplicativo no tema escuro.
4. Baixe o CSV do mês e confira que todas as datas pertencem a setembro. A exportação da tela Lançamentos continua abrangendo a base inteira.
5. Use Imprimir / PDF e confira a prévia A4 antes de salvar. Não deve aparecer o menu do aplicativo.

Use os exemplos para essa conferência; não é necessário apagar dados pessoais. O roteiro de apresentação está em `APRESENTACAO.md`.
