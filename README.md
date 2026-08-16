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

- painel responsivo com média ponderada por recência e tamanho da amostra;
- recorte móvel de 7, 14, 21 ou 30 dias, com janela padrão de 21 dias;
- cenários de primeiro turno e de segundo turno entre Lula e Flávio Bolsonaro;
- gráfico de evolução;
- filtros por período e busca por instituto/contratante;
- tabela de resultados e ficha metodológica;
- cruzamento de 16 levantamentos com protocolos e metadados oficiais do PesqEle/TSE;
- exportação dos dados filtrados em CSV;
- navegação por teclado, foco visível e suporte a movimento reduzido.

## Estado dos dados

Os 16 levantamentos catalogados possuem protocolo conferido no PesqEle. O arquivo `data/tse-metadata.json` guarda o recorte oficial de cadastro, datas, amostra, empresa realizadora, contratantes, responsável estatístico e metodologia.

Os percentuais de intenção de voto não fazem parte dos CSVs abertos do TSE. Eles são transcritos das publicações ou dos relatórios ligados individualmente em cada ficha e reconciliados com o registro oficial por protocolo, período de campo e amostra.

Fonte oficial de metadados: [Pesquisas Eleitorais 2026 — Dados Abertos do TSE](https://dadosabertos.tse.jus.br/dataset/pesquisas-eleitorais-2026).

## Atualizar o recorte do TSE

O sincronizador usa apenas a biblioteca padrão do Python:

```powershell
python scripts/sync_tse.py
```

Ele consulta o catálogo CKAN do TSE, baixa os ZIPs nacionais de pesquisas e contratantes, valida se os 16 protocolos existem e recria `data/tse-metadata.json`.

## Média ponderada

O modelo considera apenas pesquisas encerradas dentro da janela selecionada. O peso de cada levantamento é:

```text
peso = 0,5 ^ (idade_em_dias / 7) × limite(raiz(amostra / 2.000), 0,75, 1,50)
```

Assim, o componente de recência cai pela metade a cada sete dias e a amostra produz um ajuste moderado. O modelo ainda não atribui notas editoriais aos institutos e não é uma previsão eleitoral.

## Próximas etapas

- automatizar a execução diária do sincronizador;
- normalizar pesquisas, cenários, candidaturas e resultados em banco de dados;
- acrescentar outros cenários de segundo turno e páginas individuais;
- criar painel editorial para revisão e publicação;
- adicionar eleições estaduais.

## Aviso

Pesquisas medem a opinião declarada em um período e possuem incertezas amostrais e não amostrais. A média exibida não é uma previsão do resultado eleitoral.
