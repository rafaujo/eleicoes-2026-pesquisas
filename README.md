# Pulso 26

Central independente e transparente de pesquisas eleitorais brasileiras para as eleições de 2026.

O projeto cobre a disputa presidencial e os governos de São Paulo e Minas Gerais.

## Executar localmente

Este protótipo não possui dependências. Na pasta do projeto, inicie qualquer servidor HTTP estático:

```powershell
python -m http.server 4173
```

Depois acesse `http://localhost:4173`.

## O que já funciona

- painel responsivo com média ponderada por recência e tamanho da amostra;
- seletor agrupado entre Brasil e eleições estaduais, com URL compartilhável por eleição;
- recorte móvel de 7, 14, 21, 30, 60, 90 ou 180 dias, com janela padrão própria por eleição;
- seletor dinâmico de cenários, com primeiro turno e segundo turno entre Lula e Flávio Bolsonaro, Ronaldo Caiado ou Romeu Zema;
- gráfico de evolução com pontos por pesquisa, linhas da média ponderada e faixas de incerteza;
- filtros por período e busca por instituto/contratante;
- tabela de resultados e ficha metodológica;
- 33 levantamentos presidenciais com protocolos e metadados oficiais do PesqEle/TSE;
- seis levantamentos paulistas: três com a lista consolidada de 1º turno e seis no confronto Tarcísio × Haddad;
- dois levantamentos mineiros, com cenário atual de 1º turno e confrontos de 2º turno mantidos em séries comparáveis;
- exportação dos dados filtrados em CSV;
- navegação por teclado, foco visível e suporte a movimento reduzido.

## Estado dos dados

Os 33 levantamentos presidenciais catalogados possuem protocolo conferido no PesqEle. O arquivo `data/tse-metadata.json` guarda o recorte oficial de cadastro, datas, amostra, empresa realizadora, contratantes, responsável estatístico e metodologia.

Os percentuais de intenção de voto não fazem parte dos CSVs abertos do TSE. Eles ficam em `data/polls.json`, transcritos das publicações ou dos relatórios ligados individualmente em cada ficha e reconciliados com o registro oficial por protocolo, período de campo e amostra.

O arquivo `data/elections.json` lista as eleições disponíveis e aponta para uma base independente por cargo e território. Cada base tem seu próprio cadastro de candidatos e catálogo de cenários; cada pesquisa informa somente os cenários que realmente publicou. Assim, o site pode crescer para outras UFs sem misturar listas de candidatos ou preencher lacunas com estimativas.

Em São Paulo, `data/polls-sp-governor.json` separa a lista consolidada de cinco candidaturas do 1º turno do confronto Tarcísio × Haddad. O primeiro recorte começa em julho, quando os institutos passaram a usar a mesma lista; o segundo tem série desde abril.

Em Minas Gerais, `data/polls-mg-governor.json` usa a lista mais recente de candidaturas no cenário principal e mantém cada confronto de 2º turno como uma série independente. Listas antigas incompatíveis não entram na média do cenário atual.

## Cadastrar uma pesquisa

Copie `data/poll-template.json` para um arquivo de trabalho, preencha os percentuais e a fonte e execute. Para uma base estadual, informe também `--database`:

```powershell
python scripts/add_poll.py work/nova-pesquisa.json
python scripts/add_poll.py work/nova-pesquisa-sp.json --database data/polls-sp-governor.json
python scripts/add_poll.py work/nova-pesquisa-mg.json --database data/polls-mg-governor.json
python scripts/sync_tse.py
python scripts/validate_data.py
```

O utilitário atribui o próximo ID, rejeita protocolos duplicados, valida candidatos e cenários contra o catálogo e mantém a base em ordem cronológica. Para corrigir uma pesquisa já cadastrada, use `--replace`; o ID original será preservado. Uma fonte específica pode ser informada dentro de um cenário quando ela for diferente da publicação principal da pesquisa.

Fonte oficial de metadados: [Pesquisas Eleitorais 2026 — Dados Abertos do TSE](https://dadosabertos.tse.jus.br/dataset/pesquisas-eleitorais-2026).

## Atualizar o recorte do TSE

O sincronizador usa apenas a biblioteca padrão do Python. Ele consulta o catálogo CKAN do TSE, baixa os ZIPs nacionais de pesquisas e contratantes e executa estas tarefas:

- lê em `data/elections.json` quais cargos e territórios devem ser acompanhados;
- atualiza o arquivo de metadados de cada eleição para os protocolos que já possuem resultados curados no site;
- compara os registros do TSE com o monitor independente de cada eleição;
- ignora registros comprovadamente fora do território da série, mantendo a justificativa e a fonte em `data/elections.json`;
- coloca protocolos novos em filas editoriais separadas por eleição.

```powershell
python scripts/sync_tse.py
```

Para validar os arquivos sem acessar a rede:

```powershell
python -m unittest discover -s tests -v
python scripts/validate_data.py
node --check app.js
```

## Atualização e publicação automáticas

O workflow `.github/workflows/update-polls.yml` roda todos os dias às 07h17 e 16h17 no horário de Brasília e também pode ser iniciado manualmente na aba **Actions** do GitHub. O monitor automático cobre todas as eleições cadastradas, hoje presidencial, São Paulo e Minas Gerais.

Em cada execução ele:

1. baixa a versão diária do conjunto oficial do TSE;
2. atualiza metadados alterados e detecta protocolos novos em cada eleição;
3. executa os testes e as validações de consistência;
4. cria um commit na `main` somente quando os arquivos realmente mudaram;
5. abre ou atualiza uma issue separada por eleição com os protocolos que ainda precisam de fonte de resultados;
6. solicita uma nova publicação do GitHub Pages após o commit.

O TSE disponibiliza cadastro, período, amostra, metodologia e contratantes, mas não os percentuais dos cenários no CSV. Por isso, um protocolo novo entra primeiro na fila editorial. Depois que os percentuais forem conferidos em uma publicação ou relatório e adicionados à base indicada em `data/elections.json`, a próxima sincronização incorpora os metadados oficiais, remove a pendência e republica o site.

O workflow `.github/workflows/validate.yml` também valida todo pull request e todo push feito manualmente na `main`.

## Média ponderada

O modelo considera apenas pesquisas encerradas dentro da janela selecionada. O peso de cada levantamento é:

```text
peso = 0,5 ^ (idade_em_dias / 7) × limite(raiz(amostra / 2.000), 0,75, 1,50)
```

Assim, o componente de recência cai pela metade a cada sete dias e a amostra produz um ajuste moderado. O modelo ainda não atribui notas editoriais aos institutos e não é uma previsão eleitoral.

No gráfico, cada ponto representa o percentual publicado por uma pesquisa. A linha é recalculada em cada data usando somente os levantamentos já disponíveis naquele momento; seu ponto final coincide com a média exibida no card de resumo.

A faixa ao redor de cada linha usa, em cada data, a média ponderada das margens de erro declaradas pelas pesquisas disponíveis. Ela serve como referência visual da incerteza amostral típica do recorte: não é um intervalo de confiança estatístico da média e não incorpora erros não amostrais nem incerteza do modelo.

## Próximas etapas

- ampliar a cobertura estadual e o monitoramento para outras UFs usando o catálogo;
- acrescentar novos cenários à medida que forem publicados e páginas individuais;
- criar painel editorial para revisão e publicação;

## Aviso

Pesquisas medem a opinião declarada em um período e possuem incertezas amostrais e não amostrais. A média exibida não é uma previsão do resultado eleitoral.
