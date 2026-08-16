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
- cruzamento dos seis levantamentos com protocolos e metadados oficiais do PesqEle/TSE;
- exportação dos dados filtrados em CSV;
- navegação por teclado, foco visível e suporte a movimento reduzido.

## Estado dos dados

Os seis levantamentos exibidos possuem protocolo conferido no PesqEle. O arquivo `data/tse-metadata.json` guarda o recorte oficial de cadastro, datas, amostra, empresa realizadora, contratantes, responsável estatístico e metodologia.

Os percentuais de intenção de voto não fazem parte dos CSVs abertos do TSE. Eles são transcritos das publicações ou dos relatórios ligados individualmente em cada ficha e reconciliados com o registro oficial por protocolo, período de campo e amostra.

Fonte oficial de metadados: [Pesquisas Eleitorais 2026 — Dados Abertos do TSE](https://dadosabertos.tse.jus.br/dataset/pesquisas-eleitorais-2026).

## Atualizar o recorte do TSE

O sincronizador usa apenas a biblioteca padrão do Python:

```powershell
python scripts/sync_tse.py
```

Ele consulta o catálogo CKAN do TSE, baixa os ZIPs nacionais de pesquisas e contratantes, valida se os seis protocolos existem e recria `data/tse-metadata.json`.

## Próximas etapas

- automatizar a execução diária do sincronizador;
- normalizar pesquisas, cenários, candidaturas e resultados em banco de dados;
- acrescentar segundo turno e páginas individuais;
- documentar e implementar a média ponderada;
- criar painel editorial para revisão e publicação;
- adicionar eleições estaduais.

## Aviso

Pesquisas medem a opinião declarada em um período e possuem incertezas amostrais e não amostrais. A média exibida não é uma previsão do resultado eleitoral.
