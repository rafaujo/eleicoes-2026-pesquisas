# Pulso 26

Central independente e transparente de pesquisas eleitorais brasileiras para as eleições de 2026.

O MVP começa pela disputa presidencial e foi estruturado para incorporar pesquisas de governador e senador por UF posteriormente.

## Executar localmente

Este protótipo não possui dependências. Na pasta do projeto, inicie qualquer servidor HTTP estático:

```powershell
python -m http.server 4173
```

Depois acesse `http://localhost:4173`.

## O que já funciona

- painel responsivo com média simples das pesquisas visíveis;
- gráfico de evolução;
- filtros por período e busca por instituto/contratante;
- tabela de resultados e ficha metodológica;
- exportação dos dados filtrados em CSV;
- navegação por teclado, foco visível e suporte a movimento reduzido.

## Estado dos dados

Os números presentes no protótipo formam uma **base de demonstração**, transcrita da página de referência indicada no início do projeto. Antes da publicação editorial, cada levantamento deve ser validado contra:

1. o registro no PesqEle/TSE;
2. o questionário registrado;
3. o relatório ou release original do instituto.

Fonte oficial de metadados: [Pesquisas Eleitorais 2026 — Dados Abertos do TSE](https://dadosabertos.tse.jus.br/dataset/pesquisas-eleitorais-2026).

## Próximas etapas

- importar diariamente os metadados do TSE;
- normalizar pesquisas, cenários, candidaturas e resultados em banco de dados;
- acrescentar segundo turno e páginas individuais;
- documentar e implementar a média ponderada;
- criar painel editorial para revisão e publicação;
- adicionar eleições estaduais.

## Aviso

Pesquisas medem a opinião declarada em um período e possuem incertezas amostrais e não amostrais. A média exibida não é uma previsão do resultado eleitoral.
