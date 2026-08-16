const candidates = [
  { key: "lula", name: "Lula", color: "#c83f49" },
  { key: "flavio", name: "Flávio Bolsonaro", color: "#356ea8" },
  { key: "caiado", name: "Ronaldo Caiado", color: "#238b57" },
  { key: "zema", name: "Romeu Zema", color: "#e07a35" },
  { key: "renan", name: "Renan Santos", color: "#c79a18" },
];

const TSE_DATASET_URL = "https://dadosabertos.tse.jus.br/dataset/pesquisas-eleitorais-2026";
const PESQELE_URL = "https://pesqele-divulgacao.tse.jus.br/app/pesquisa/listar.xhtml";
const HALF_LIFE_DAYS = 7;

// Percentuais transcritos das publicações indicadas em resultSource.
// Datas, amostras e demais metadados são reconciliados com data/tse-metadata.json.
const polls = [
  {
    id: 1, pollster: "Quaest", publication: "Genial/Quaest · G1", protocol: "BR067732026",
    start: "2026-08-10", end: "2026-08-13", field: "10–13 ago", sample: 2004, margin: 2, confidence: 95,
    method: "Presencial domiciliar",
    resultSource: "https://g1.globo.com/politica/eleicoes/2026/pesquisa-eleitoral/noticia/2026/08/14/quaest-presidente-1o-turno-14-agosto.ghtml",
    resultSourceLabel: "G1 — resultado publicado",
    lula: 38, flavio: 31, caiado: 4, zema: 2, renan: 4, undecided: 18,
    runoff: { lula: 43, flavio: 40, undecided: 17 },
  },
  {
    id: 2, pollster: "PoderData", publication: "Parceria de divulgação: Aya", protocol: "BR068682026",
    start: "2026-08-09", end: "2026-08-12", field: "9–12 ago", sample: 2400, margin: 2, confidence: 95,
    method: "Telefônica automatizada",
    resultSource: "https://www.poder360.com.br/poderdata/lula-tem-46-contra-45-de-flavio-no-2o-turno-diz-poderdata-aya/",
    resultSourceLabel: "Poder360 — resultado e metodologia",
    lula: 41, flavio: 35, caiado: 4, zema: 3, renan: 4, undecided: 6,
    runoff: { lula: 46, flavio: 45, undecided: 9 },
  },
  {
    id: 3, pollster: "GERP", publication: "Divulgação própria", protocol: "BR080452026",
    start: "2026-08-06", end: "2026-08-10", field: "6–10 ago", sample: 2400, margin: 2.04, confidence: 95.55,
    method: "Quantitativa por cotas",
    resultSource: "https://static.poder360.com.br/uploads/2026/08/PRESIDENCIA_DO_BRASIL_DIVULGACAO_26a_Relatorio_Eleicoes_2026_Presidente.pdf",
    resultSourceLabel: "GERP/Poder360 — relatório completo (PDF)",
    lula: 38, flavio: 38, caiado: 4, zema: 2, renan: 5, undecided: 11,
    runoff: { lula: 43, flavio: 45, undecided: 12 },
  },
  {
    id: 4, pollster: "Nexus", publication: "BTG Pactual", protocol: "BR084282026",
    start: "2026-08-07", end: "2026-08-09", field: "7–9 ago", sample: 2000, margin: 2, confidence: 95,
    method: "Telefônica com entrevistadores",
    resultSource: "https://www.gazetadopovo.com.br/eleicoes/2026/pesquisa-eleitoral-2026/nexus-btg-pactual-presidente-agosto-2026-2/",
    resultSourceLabel: "Gazeta do Povo — resultado publicado",
    lula: 40, flavio: 35, caiado: 5, zema: 3, renan: 4, undecided: 8,
    runoff: { lula: 47, flavio: 44, undecided: 9 },
  },
  {
    id: 5, pollster: "CNT/MDA", publication: "Confederação Nacional do Transporte", protocol: "BR069352026",
    start: "2026-08-05", end: "2026-08-09", field: "5–9 ago", sample: 2002, margin: 2.2, confidence: 95,
    method: "Presencial, domicílios e fluxo",
    resultSource: "https://admin.cnnbrasil.com.br/wp-content/uploads/sites/12/2026/08/Relatorio-Pesquisa-CNT-de-Opiniao-R169-AGOSTO26_7486.pdf",
    resultSourceLabel: "CNT/CNN Brasil — relatório completo (PDF)",
    lula: 42.4, flavio: 28.7, caiado: 4, zema: 3.3, renan: 2.8, undecided: 14,
    runoff: { lula: 48, flavio: 39.1, undecided: 12.9 },
  },
  {
    id: 6, pollster: "Futura/100 Cidades", publication: "Divulgação Apex/Futura", protocol: "BR081092026",
    start: "2026-08-03", end: "2026-08-06", field: "3–6 ago", sample: 2000, margin: 2.2, confidence: 95,
    method: "Telefônica por cotas",
    resultSource: "https://www.gazetadopovo.com.br/eleicoes/2026/pesquisa-eleitoral-2026/futura-inteligencia-presidente-agosto-2026/",
    resultSourceLabel: "Gazeta do Povo — resultado publicado",
    lula: 36.3, flavio: 32.7, caiado: 7.7, zema: 4.4, renan: 3.8, undecided: 12.2,
    runoff: { lula: 46.5, flavio: 44, undecided: 9.5 },
  },
  {
    id: 7, pollster: "Palver", publication: "Divulgação CartaCapital", protocol: "BR065962026",
    start: "2026-08-03", end: "2026-08-09", field: "3–9 ago", sample: 5000, margin: 3, confidence: 95,
    method: "Entrevistas digitais",
    resultSource: "https://www.cartacapital.com.br/politica/as-intencoes-de-voto-de-lula-e-flavio-bolsonaro-em-pesquisa-de-estreia-da-palver/",
    resultSourceLabel: "CartaCapital — resultado publicado",
    lula: 44, flavio: 40, caiado: 2, zema: 1, renan: 10, undecided: 1,
    runoff: { lula: 46, flavio: 46, undecided: 8 },
  },
  {
    id: 8, pollster: "Meio/Ideia", publication: "Canal Meio", protocol: "BR045792026",
    start: "2026-07-31", end: "2026-08-03", field: "31 jul–3 ago", sample: 1500, margin: 2.5, confidence: 95,
    method: "Entrevistas por telefone",
    resultSource: "https://www.gazetadopovo.com.br/eleicoes/2026/pesquisa-eleitoral-2026/meio-ideia-presidente-agosto-2026/",
    resultSourceLabel: "Gazeta do Povo — resultado publicado",
    lula: 43, flavio: 35, caiado: 5.7, zema: 2.6, renan: 4.7, undecided: 6,
    runoff: { lula: 48.5, flavio: 43, undecided: 8.5 },
  },
  {
    id: 9, pollster: "Quaest", publication: "Genial/Quaest", protocol: "BR065912026",
    start: "2026-07-31", end: "2026-08-03", field: "31 jul–3 ago", sample: 2004, margin: 2, confidence: 95,
    method: "Presencial domiciliar",
    resultSource: "https://www.gazetadopovo.com.br/eleicoes/2026/pesquisa-eleitoral-2026/genial-quaest-presidente-agosto-2026/",
    resultSourceLabel: "Gazeta do Povo — resultado publicado",
    lula: 39, flavio: 30, caiado: 4, zema: 2, renan: 4, undecided: 18,
    runoff: { lula: 44, flavio: 39, undecided: 17 },
  },
  {
    id: 10, pollster: "Nexus", publication: "BTG Pactual", protocol: "BR028742026",
    start: "2026-07-31", end: "2026-08-02", field: "31 jul–2 ago", sample: 2000, margin: 2, confidence: 95,
    method: "Telefônica com entrevistadores",
    resultSource: "https://www.gazetadopovo.com.br/eleicoes/2026/pesquisa-eleitoral-2026/nexus-btg-pactual-presidente-agosto-2026/",
    resultSourceLabel: "Gazeta do Povo — resultado publicado",
    lula: 41, flavio: 37, caiado: 5, zema: 3, renan: 4, undecided: 7,
    runoff: { lula: 46, flavio: 45, undecided: 10 },
  },
  {
    id: 11, pollster: "Vox Brasil", publication: "Poder360", protocol: "BR010842026",
    start: "2026-07-26", end: "2026-07-28", field: "26–28 jul", sample: 2100, margin: 2.15, confidence: 95,
    method: "Presencial domiciliar",
    resultSource: "https://www.poder360.com.br/poder-eleicoes-2026/lula-tem-475-contra-411-de-flavio-no-2o-turno-diz-pesquisa/",
    resultSourceLabel: "Poder360 — resultado publicado",
    lula: 40.5, flavio: 31.2, caiado: 5.5, zema: 3.2, renan: 3, undecided: 11.9,
    runoff: { lula: 47.5, flavio: 41.1, undecided: 11.4 },
  },
  {
    id: 12, pollster: "PoderData", publication: "Poder360", protocol: "BR078452026",
    start: "2026-07-26", end: "2026-07-29", field: "26–29 jul", sample: 2400, margin: 2, confidence: 95,
    method: "Telefônica automatizada",
    resultSource: "https://www.gazetadopovo.com.br/eleicoes/2026/pesquisa-eleitoral-2026/poderdata-presidente-pesquisa-julho-2026/",
    resultSourceLabel: "Gazeta do Povo — resultado publicado",
    lula: 41, flavio: 35, caiado: 5, zema: 3, renan: 4, undecided: 9,
    runoff: { lula: 46, flavio: 43, undecided: 11 },
  },
  {
    id: 13, pollster: "Alfa Inteligência", publication: "TMC", protocol: "BR044882026",
    start: "2026-07-23", end: "2026-07-28", field: "23–28 jul", sample: 2700, margin: 1.8, confidence: 95,
    method: "Entrevistas presenciais",
    resultSource: "https://noticias.uol.com.br/ultimas-noticias/agencia-estado/2026/07/31/lula-lidera-no-1-e-no-2-turno-mostra-pesquisa-que-traz-disputa-mais-apertada-contra-caiado.htm",
    resultSourceLabel: "UOL/Estadão Conteúdo — resultado publicado",
    lula: 43, flavio: 29, caiado: 7, zema: 6, renan: 3, undecided: 10,
    runoff: { lula: 48, flavio: 41, undecided: 11 },
  },
  {
    id: 14, pollster: "AtlasIntel", publication: "Bloomberg", protocol: "BR086022026",
    start: "2026-07-22", end: "2026-07-27", field: "22–27 jul", sample: 5000, margin: 1, confidence: 95,
    method: "Recrutamento digital aleatório",
    resultSource: "https://www.gazetadopovo.com.br/eleicoes/2026/pesquisa-eleitoral-2026/atlasintel-presidente-julho-2026-2/",
    resultSourceLabel: "Gazeta do Povo — resultado publicado",
    lula: 44.9, flavio: 35.8, caiado: 3.1, zema: 2.8, renan: 7.8, undecided: 1.6,
    runoff: { lula: 49.2, flavio: 42.9, undecided: 7.9 },
  },
  {
    id: 15, pollster: "Nexus", publication: "BTG Pactual", protocol: "BR014892026",
    start: "2026-07-24", end: "2026-07-26", field: "24–26 jul", sample: 2000, margin: 2, confidence: 95,
    method: "Telefônica com entrevistadores",
    resultSource: "https://www.gazetadopovo.com.br/eleicoes/2026/pesquisa-eleitoral-2026/nexus-btg-pactual-presidente-julho-2026-2/",
    resultSourceLabel: "Gazeta do Povo — resultado publicado",
    lula: 42, flavio: 33, caiado: 6, zema: 3, renan: 5, undecided: 8,
    runoff: { lula: 47, flavio: 43, undecided: 10 },
  },
  {
    id: 16, pollster: "Datafolha", publication: "Folha de S.Paulo", protocol: "BR011662026",
    start: "2026-07-22", end: "2026-07-24", field: "22–24 jul", sample: 2004, margin: 2, confidence: 95,
    method: "Presencial em pontos de fluxo",
    resultSource: "https://g1.globo.com/politica/eleicoes/2026/pesquisa-eleitoral/noticia/2026/07/24/datafolha-2o-turno-lula-tem-48percent-e-flavio-bolsonaro-43percent.ghtml",
    resultSourceLabel: "G1 — resultado publicado",
    lula: 40, flavio: 32, caiado: 4, zema: 3, renan: 3, undecided: 11,
    runoff: { lula: 48, flavio: 43, undecided: 10 },
  },
  {
    id: 17, pollster: "PoderData", publication: "Parceria de divulgação: Aya", protocol: "BR000592026",
    start: "2026-07-12", end: "2026-07-15", field: "12–15 jul", sample: 2400, margin: 2, confidence: 95,
    method: "Telefônica automatizada",
    resultSource: "https://jovempan.com.br/politica/poderdata-aya-lula-marca-40-e-flavio-34-no-1o-turno-2o-tem-empate-tecnico/",
    resultSourceLabel: "Jovem Pan — resultado publicado",
    lula: 40, flavio: 34, caiado: 4, zema: 4, renan: 6, undecided: 10,
    runoff: { lula: 45, flavio: 43, undecided: 12 },
  },
  {
    id: 18, pollster: "Quaest", publication: "Genial/Quaest", protocol: "BR071812026",
    start: "2026-07-10", end: "2026-07-13", field: "10–13 jul", sample: 2004, margin: 2, confidence: 95,
    method: "Presencial domiciliar",
    resultSource: "https://www.poder360.com.br/poder-eleicoes/lula-tem-45-contra-37-de-flavio-no-2o-turno-diz-quaest/",
    resultSourceLabel: "Poder360 — resultado publicado",
    lula: 40, flavio: 28, caiado: 4, zema: 2, renan: 3, undecided: 19,
    runoff: { lula: 45, flavio: 37, undecided: 18 },
  },
  {
    id: 19, pollster: "Nexus", publication: "BTG Pactual", protocol: "BR079812026",
    start: "2026-07-10", end: "2026-07-12", field: "10–12 jul", sample: 2000, margin: 2, confidence: 95,
    method: "Telefônica com entrevistadores",
    resultSource: "https://www.gazetadopovo.com.br/eleicoes/2026/pesquisa-eleitoral-2026/nexus-btg-pactual-presidente-julho-2026/",
    resultSourceLabel: "Gazeta do Povo — resultado publicado",
    lula: 40, flavio: 34, caiado: 5, zema: 4, renan: 4, undecided: 9,
    runoff: { lula: 47, flavio: 44, undecided: 9 },
  },
  {
    id: 20, pollster: "Futura/100 Cidades", publication: "Apex/Futura", protocol: "BR072942026",
    start: "2026-07-07", end: "2026-07-11", field: "7–11 jul", sample: 2000, margin: 2.2, confidence: 95,
    method: "Telefônica por cotas",
    resultSource: "https://www.poder360.com.br/poder-eleicoes/lula-e-flavio-empatam-no-2o-turno-diz-futura-apex/",
    resultSourceLabel: "Poder360 — resultado publicado",
    lula: 40.1, flavio: 36.8, caiado: 5, zema: 3.7, renan: 2.6, undecided: 8.7,
    runoff: { lula: 46.3, flavio: 46.1, undecided: 7.6 },
  },
  {
    id: 21, pollster: "GERP", publication: "Divulgação própria", protocol: "BR030672026",
    start: "2026-07-03", end: "2026-07-07", field: "3–7 jul", sample: 2000, margin: 2.2, confidence: 95,
    method: "Quantitativa por cotas",
    resultSource: "https://www.poder360.com.br/poder-eleicoes/flavio-tem-45-e-lula-42-em-eventual-2o-turno-diz-pesquisa/",
    resultSourceLabel: "Poder360 — resultado publicado",
    lula: 36, flavio: 36, caiado: 4, zema: 2, renan: 2, undecided: 17,
    runoff: { lula: 42, flavio: 45, undecided: 13 },
  },
  {
    id: 22, pollster: "AtlasIntel", publication: "Bloomberg", protocol: "BR045822026",
    start: "2026-06-25", end: "2026-06-30", field: "25–30 jun", sample: 5000, margin: 1, confidence: 95,
    method: "Recrutamento digital aleatório",
    resultSource: "https://www.gazetadopovo.com.br/eleicoes/2026/pesquisa-eleitoral-2026/atlasintel-presidente-julho-2026/",
    resultSourceLabel: "Gazeta do Povo — resultado publicado",
    lula: 46.3, flavio: 36.6, caiado: 2.9, zema: 2, renan: 7.8, undecided: 1.2,
    runoff: { lula: 48.8, flavio: 42.3, undecided: 8.9 },
  },
  {
    id: 23, pollster: "Nexus", publication: "BTG Pactual", protocol: "BR085212026",
    start: "2026-06-26", end: "2026-06-28", field: "26–28 jun", sample: 2000, margin: 2, confidence: 95,
    method: "Telefônica com entrevistadores",
    resultSource: "https://pt.wikipedia.org/wiki/Pesquisas_de_opini%C3%A3o_para_a_elei%C3%A7%C3%A3o_presidencial_no_Brasil_em_2026",
    resultSourceLabel: "Wikipédia — catálogo e fontes da pesquisa",
    lula: 42, flavio: 35, caiado: 5, zema: 3, renan: 4, undecided: 8,
    runoff: { lula: 47, flavio: 44, undecided: 9 },
  },
  {
    id: 24, pollster: "Vox Brasil", publication: "Poder360", protocol: "BR066302026",
    start: "2026-06-23", end: "2026-06-25", field: "23–25 jun", sample: 2100, margin: 2.15, confidence: 95,
    method: "Presencial domiciliar",
    resultSource: "https://www.poder360.com.br/poder-pesquisas/flavio-e-lula-empatam-no-2o-turno-diz-pesquisa-2/",
    resultSourceLabel: "Poder360 — resultado publicado",
    lula: 38.3, flavio: 32.2, caiado: 5.1, zema: 3.8, renan: 2.5, undecided: 14.3,
    runoff: { lula: 45.3, flavio: 42.8, undecided: 11.9 },
  },
  {
    id: 25, pollster: "PoderData", publication: "Parceria de divulgação: Aya", protocol: "BR057222026",
    start: "2026-06-21", end: "2026-06-24", field: "21–24 jun", sample: 2400, margin: 2, confidence: 95,
    method: "Telefônica automatizada",
    resultSource: "https://pt.wikipedia.org/wiki/Pesquisas_de_opini%C3%A3o_para_a_elei%C3%A7%C3%A3o_presidencial_no_Brasil_em_2026",
    resultSourceLabel: "Wikipédia — catálogo e fontes da pesquisa",
    lula: 40, flavio: 36, caiado: 4, zema: 3, renan: 4, undecided: 8,
    runoff: { lula: 46, flavio: 43, undecided: 11 },
  },
  {
    id: 26, pollster: "Indexa", publication: "Divulgação Congresso em Foco", protocol: "BR089442026",
    start: "2026-06-18", end: "2026-06-20", field: "18–20 jun", sample: 2000, margin: 2.2, confidence: 95,
    method: "Entrevistas telefônicas",
    resultSource: "https://www.congressoemfoco.com.br/amp/noticia/119896/lula-vence-flavio-por-47-a-40-no-2-turno-aponta-pesquisa-indexa",
    resultSourceLabel: "Congresso em Foco — resultado e metodologia",
    lula: 42, flavio: 31, caiado: 5, zema: 3, renan: 3, undecided: 14,
    runoff: { lula: 47, flavio: 40, undecided: 13 },
  },
  {
    id: 27, pollster: "Datafolha", publication: "Folha de S.Paulo", protocol: "BR099562026",
    start: "2026-06-17", end: "2026-06-19", field: "17–19 jun", sample: 2004, margin: 2, confidence: 95,
    method: "Presencial em pontos de fluxo",
    resultSource: "https://g1.globo.com/politica/eleicoes/2026/pesquisa-eleitoral/noticia/2026/06/20/datafolha-lula-tem-41percent-e-flavio-bolsonaro-31percent-das-intencoes-de-voto-no-1o-turno.ghtml",
    resultSourceLabel: "G1 — resultado publicado",
    lula: 41, flavio: 31, caiado: 3, zema: 2, renan: 3, undecided: 11,
    runoff: { lula: 47, flavio: 43, undecided: 9 },
  },
  {
    id: 28, pollster: "CNT/MDA", publication: "Confederação Nacional do Transporte", protocol: "BR042562026",
    start: "2026-06-10", end: "2026-06-14", field: "10–14 jun", sample: 2002, margin: 2.2, confidence: 95,
    method: "Presencial, domicílios e fluxo",
    resultSource: "https://www.poder360.com.br/poder-pesquisas/cnt-42-dizem-votar-em-lula-mas-so-21-se-veem-como-de-esquerda/",
    resultSourceLabel: "Poder360 — resultado publicado",
    lula: 41.8, flavio: 28.2, caiado: 4, zema: 2.8, renan: 2, undecided: 14.9,
    runoff: { lula: 49.3, flavio: 36.8, undecided: 13.9 },
  },
  {
    id: 29, pollster: "Nexus", publication: "BTG Pactual", protocol: "BR066452026",
    start: "2026-06-12", end: "2026-06-14", field: "12–14 jun", sample: 2000, margin: 2, confidence: 95,
    method: "Telefônica com entrevistadores",
    resultSource: "https://www.poder360.com.br/poder-eleicoes/lula-tem-49-contra-43-de-flavio-no-2o-turno-diz-nexus/",
    resultSourceLabel: "Poder360 — resultado publicado",
    lula: 42, flavio: 33, caiado: 4, zema: 2, renan: 4, undecided: 8,
    runoff: { lula: 49, flavio: 43, undecided: 9 },
  },
  {
    id: 30, pollster: "Futura/100 Cidades", publication: "Apex/Futura", protocol: "BR014612026",
    start: "2026-06-08", end: "2026-06-12", field: "8–12 jun", sample: 2000, margin: 2.2, confidence: 95,
    method: "Telefônica por cotas",
    resultSource: "https://www.poder360.com.br/poder-pesquisas/lula-tem-481-e-flavio-429-em-eventual-2o-turno-diz-pesquisa/",
    resultSourceLabel: "Poder360 — resultado publicado",
    lula: 41.6, flavio: 34.1, caiado: 4.5, zema: 3.5, renan: 2.3, undecided: 10,
    runoff: { lula: 48.1, flavio: 42.9, undecided: 10 },
  },
  {
    id: 31, pollster: "Alfa Inteligência", publication: "Divulgação CNN Brasil", protocol: "BR034962026",
    start: "2026-06-05", end: "2026-06-10", field: "5–10 jun", sample: 1400, margin: 2.6, confidence: 95,
    method: "Entrevistas presenciais",
    resultSource: "https://pt.wikipedia.org/wiki/Pesquisas_de_opini%C3%A3o_para_a_elei%C3%A7%C3%A3o_presidencial_no_Brasil_em_2026",
    resultSourceLabel: "Wikipédia — catálogo e fontes da pesquisa",
    lula: 40, flavio: 31, caiado: 7, zema: 7, renan: 2, undecided: 8,
    runoff: { lula: 44, flavio: 41, undecided: 15 },
  },
  {
    id: 32, pollster: "Quaest", publication: "Genial/Quaest", protocol: "BR076612026",
    start: "2026-06-05", end: "2026-06-08", field: "5–8 jun", sample: 2004, margin: 2, confidence: 95,
    method: "Presencial domiciliar",
    resultSource: "https://www.poder360.com.br/poder-eleicoes/lula-tem-44-contra-38-de-flavio-diz-quaest/",
    resultSourceLabel: "Poder360 — resultado publicado",
    lula: 39, flavio: 29, caiado: 3, zema: 2, renan: 3, undecided: 19,
    runoff: { lula: 44, flavio: 38, undecided: 18 },
  },
  {
    id: 33, pollster: "GERP", publication: "Divulgação própria", protocol: "BR017922026",
    start: "2026-06-01", end: "2026-06-05", field: "1–5 jun", sample: 2000, margin: 2.24, confidence: 95.55,
    method: "Quantitativa por cotas",
    resultSource: "https://www.poder360.com.br/poder-eleicoes/flavio-bolsonaro-vence-lula-no-2o-turno-diz-pesquisa-gerp/",
    resultSourceLabel: "Poder360 — resultado publicado",
    lula: 34, flavio: 35, caiado: 2, zema: 2, renan: 4, undecided: 19,
    runoff: { lula: 39.1, flavio: 44.7, undecided: 16.2 },
  },
];

const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const oneDecimal = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const integer = new Intl.NumberFormat("pt-BR");
const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const state = { period: "21", query: "", round: "first" };
const brazilDateParts = Object.fromEntries(
  new Intl.DateTimeFormat("en", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date()).map((part) => [part.type, part.value]),
);
const DATA_REFERENCE_DATE = `${brazilDateParts.year}-${brazilDateParts.month}-${brazilDateParts.day}`;

let tseData = null;

const averageList = document.querySelector("#average-list");
const undecidedAverage = document.querySelector("#undecided-average");
const table = document.querySelector(".table-wrap table");
const tableHead = document.querySelector("#poll-table-head");
const tableBody = document.querySelector("#poll-table-body");
const pollCount = document.querySelector("#poll-count");
const chart = document.querySelector("#trend-chart");
const chartLegend = document.querySelector("#chart-legend");
const dialog = document.querySelector("#poll-dialog");
const dialogContent = document.querySelector("#dialog-content");

function escapeHtml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function formatPct(value) { return `${number.format(value)}%`; }
function formatAveragePct(value) { return `${oneDecimal.format(value)}%`; }

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
}

function formatField(start, end) {
  const startDate = new Date(`${start}T00:00:00Z`);
  const endDate = new Date(`${end}T00:00:00Z`);
  const monthFormatter = new Intl.DateTimeFormat("pt-BR", { month: "short", timeZone: "UTC" });
  const startMonth = monthFormatter.format(startDate).replace(".", "");
  const endMonth = monthFormatter.format(endDate).replace(".", "");
  return startMonth === endMonth
    ? `${startDate.getUTCDate()}–${endDate.getUTCDate()} ${endMonth}`
    : `${startDate.getUTCDate()} ${startMonth}–${endDate.getUTCDate()} ${endMonth}`;
}

function officialRecord(poll) { return tseData?.records?.[poll.protocol] || null; }
function activeCandidates() { return state.round === "second" ? candidates.slice(0, 2) : candidates; }
function valueFor(poll, key) { return state.round === "second" ? poll.runoff?.[key] : poll[key]; }
function neutralFor(poll) { return state.round === "second" ? poll.runoff?.undecided : poll.undecided; }

function sortCandidatesByValue(items, valueGetter) {
  return items
    .map((candidate, index) => ({ candidate, index, value: valueGetter(candidate) }))
    .sort((a, b) => (b.value - a.value) || (a.index - b.index))
    .map(({ candidate }) => candidate);
}

function pollAgeDays(poll) {
  const reference = new Date(`${DATA_REFERENCE_DATE}T12:00:00Z`);
  const end = new Date(`${poll.end}T12:00:00Z`);
  return Math.max(0, (reference - end) / 86400000);
}

function pollWeightAt(poll, referenceTime) {
  const endTime = Date.parse(`${poll.end}T12:00:00Z`);
  const ageDays = Math.max(0, (referenceTime - endTime) / 86400000);
  const recency = Math.pow(0.5, ageDays / HALF_LIFE_DAYS);
  const sample = Math.min(1.5, Math.max(0.75, Math.sqrt(poll.sample / 2000)));
  return recency * sample;
}

function pollWeight(poll) {
  return pollWeightAt(poll, Date.parse(`${DATA_REFERENCE_DATE}T12:00:00Z`));
}

function visiblePolls() {
  const windowDays = Number(state.period);
  return polls.filter((poll) => {
    const searchable = `${poll.pollster} ${poll.publication} ${poll.protocol}`.toLowerCase();
    return searchable.includes(state.query.toLowerCase())
      && pollAgeDays(poll) <= windowDays
      && (state.round === "first" || Boolean(poll.runoff));
  });
}

function weightedMeanAt(items, getter, referenceTime) {
  if (!items.length) return 0;
  const valid = items.filter((item) => Number.isFinite(getter(item)));
  const denominator = valid.reduce((sum, item) => sum + pollWeightAt(item, referenceTime), 0);
  return denominator
    ? valid.reduce((sum, item) => sum + getter(item) * pollWeightAt(item, referenceTime), 0) / denominator
    : 0;
}

function weightedMean(items, getter) {
  return weightedMeanAt(items, getter, Date.parse(`${DATA_REFERENCE_DATE}T12:00:00Z`));
}

function rankedCandidates(items) {
  return sortCandidatesByValue(
    activeCandidates(),
    (candidate) => weightedMean(items, (poll) => valueFor(poll, candidate.key)),
  );
}

function renderAverage(items) {
  document.querySelector("#average-title").textContent = state.round === "second" ? "Lula × Flávio Bolsonaro" : "Retrato do momento";
  document.querySelector("#method-note").innerHTML = `Entram apenas pesquisas encerradas nos últimos <strong>${state.period} dias</strong>. O peso cai pela metade a cada <strong>${HALF_LIFE_DAYS} dias</strong> e recebe um ajuste moderado pela raiz da amostra, limitado entre 0,75 e 1,50. Não há nota editorial por instituto.`;
  if (!items.length) {
    averageList.innerHTML = '<p class="dialog-note">Nenhuma pesquisa encontrada.</p>';
    undecidedAverage.textContent = "—";
    return;
  }
  averageList.innerHTML = rankedCandidates(items).map((candidate) => {
    const value = weightedMean(items, (poll) => valueFor(poll, candidate.key));
    return `<div class="average-row" style="--candidate-color:${candidate.color}">
      <div class="candidate"><i class="candidate-dot"></i><span>${candidate.name}</span></div>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.min(100, value * 2.05)}%"></div></div>
      <strong>${formatAveragePct(value)}</strong>
    </div>`;
  }).join("");
  undecidedAverage.textContent = formatAveragePct(weightedMean(items, neutralFor));
}

function renderTable(items) {
  const visibleCandidates = activeCandidates();
  table.classList.toggle("runoff-table", state.round === "second");
  tableHead.innerHTML = `<tr>
    <th>Pesquisa / divulgação</th><th>Período de campo</th><th>Amostra</th><th>Margem</th><th>Peso</th>
    ${visibleCandidates.map((candidate) => `<th>${({ flavio: "Flávio", caiado: "Caiado", zema: "Zema", renan: "Renan" })[candidate.key] || candidate.name}</th>`).join("")}
    <th>Dif.</th><th><span class="sr-only">Detalhes</span></th>
  </tr>`;
  const maxWeight = items.length ? Math.max(...items.map(pollWeight)) : 1;
  tableBody.innerHTML = items.map((poll) => {
    const lula = valueFor(poll, "lula");
    const flavio = valueFor(poll, "flavio");
    const leaderKey = lula >= flavio ? "lula" : "flavio";
    const diff = Math.abs(lula - flavio);
    const relativeWeight = pollWeight(poll) / maxWeight;
    return `<tr>
      <td><span class="pollster">${escapeHtml(poll.pollster)}</span><span class="sponsor">${escapeHtml(poll.publication)}</span><span class="verified-badge" title="Registro verificado no PesqEle/TSE">✓ ${poll.protocol}</span></td>
      <td>${poll.field}</td><td>${integer.format(poll.sample)}</td><td>± ${number.format(poll.margin)}</td>
      <td><span class="weight-pill" title="Peso relativo à pesquisa de maior peso no recorte">×${number.format(relativeWeight)}</span></td>
      ${visibleCandidates.map((candidate) => `<td class="${leaderKey === candidate.key ? "leader" : ""}">${formatPct(valueFor(poll, candidate.key))}</td>`).join("")}
      <td><span class="difference">${diff === 0 ? "Empate" : `${leaderKey === "lula" ? "L" : "F"} +${number.format(diff)}`}</span></td>
      <td><button class="row-button" type="button" data-poll-id="${poll.id}" aria-label="Ver detalhes de ${escapeHtml(poll.pollster)}">Ver →</button></td>
    </tr>`;
  }).join("");
  const verified = items.filter((poll) => officialRecord(poll)).length;
  const discarded = polls.length - polls.filter((poll) => pollAgeDays(poll) <= Number(state.period)).length;
  const verification = tseData ? `${verified}/${items.length} registros conferidos no TSE` : `${items.length} pesquisas com protocolo informado`;
  pollCount.textContent = `${items.length} ${items.length === 1 ? "pesquisa no recorte" : "pesquisas no recorte"} · ${discarded} fora da janela · ${verification}`;
}

function svgElement(name, attrs = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

function smoothPath(points) {
  if (!points.length) return "";
  if (points.length === 1) return `M${points[0].x},${points[0].y}`;
  if (points.length === 2) return `M${points[0].x},${points[0].y} L${points[1].x},${points[1].y}`;
  let path = `M${points[0].x},${points[0].y}`;
  for (let index = 0; index < points.length - 1; index += 1) {
    const before = points[Math.max(0, index - 1)];
    const current = points[index];
    const next = points[index + 1];
    const after = points[Math.min(points.length - 1, index + 2)];
    const control1 = { x: current.x + (next.x - before.x) / 6, y: current.y + (next.y - before.y) / 6 };
    const control2 = { x: next.x - (after.x - current.x) / 6, y: next.y - (after.y - current.y) / 6 };
    path += ` C${control1.x},${control1.y} ${control2.x},${control2.y} ${next.x},${next.y}`;
  }
  return path;
}

function uncertaintyAreaPath(points, yFor, minY, maxY) {
  if (!points.length) return "";
  const upper = points.map((point) => ({
    x: point.x,
    y: yFor(Math.min(maxY, point.value + point.uncertainty)),
  }));
  const lower = [...points].reverse().map((point) => ({
    x: point.x,
    y: yFor(Math.max(minY, point.value - point.uncertainty)),
  }));
  return `${smoothPath(upper)} ${smoothPath(lower).replace(/^M/, "L")} Z`;
}

function weightedTrend(items, candidateKey) {
  const dates = [...new Set(items.map((poll) => poll.end))].sort();
  return dates.map((date) => {
    const referenceTime = Date.parse(`${date}T12:00:00Z`);
    const available = items.filter((poll) => Date.parse(`${poll.end}T12:00:00Z`) <= referenceTime);
    return {
      date,
      value: weightedMeanAt(available, (poll) => valueFor(poll, candidateKey), referenceTime),
      uncertainty: weightedMeanAt(available, (poll) => poll.margin, referenceTime),
    };
  });
}

function renderChart(items) {
  chart.replaceChildren();
  const title = svgElement("title", { id: "chart-title" });
  title.textContent = state.round === "second" ? "Evolução da média ponderada no segundo turno" : "Evolução da média ponderada no primeiro turno";
  const desc = svgElement("desc", { id: "chart-description" });
  desc.textContent = "As linhas mostram a média ponderada calculada com as pesquisas disponíveis em cada data. As faixas mostram a margem de erro média ponderada e os pontos, o resultado de cada pesquisa.";
  chart.append(title, desc);

  const ordered = [...items].sort((a, b) => a.end.localeCompare(b.end));
  const pad = { left: 46, right: 22, top: 20, bottom: 42 };
  const width = 760 - pad.left - pad.right;
  const height = 360 - pad.top - pad.bottom;
  const minY = state.round === "second" ? 30 : 0;
  const maxY = state.round === "second" ? 55 : 50;
  const yTicks = state.round === "second" ? [30, 35, 40, 45, 50, 55] : [0, 10, 20, 30, 40, 50];
  const yFor = (value) => pad.top + height - ((value - minY) / (maxY - minY)) * height;
  yTicks.forEach((tick) => {
    const y = yFor(tick);
    chart.appendChild(svgElement("line", { x1: pad.left, x2: 760 - pad.right, y1: y, y2: y, class: "grid-line" }));
    const label = svgElement("text", { x: 6, y: y + 4, class: "axis-label" });
    label.textContent = `${tick}%`;
    chart.appendChild(label);
  });
  if (!ordered.length) return;

  const timestamps = ordered.map((poll) => Date.parse(`${poll.end}T12:00:00Z`));
  const minTime = Math.min(...timestamps);
  const maxTime = Math.max(...timestamps);
  const xForTime = (time) => minTime === maxTime ? pad.left + width / 2 : pad.left + ((time - minTime) / (maxTime - minTime)) * width;
  const xForPoll = (poll) => xForTime(Date.parse(`${poll.end}T12:00:00Z`));
  const xTickTimes = [...new Set([minTime, minTime + (maxTime - minTime) / 3, minTime + (maxTime - minTime) * 2 / 3, maxTime])];
  xTickTimes.forEach((time) => {
    const label = svgElement("text", { x: xForTime(time), y: 344, "text-anchor": "middle", class: "axis-label" });
    label.textContent = formatDate(new Date(time).toISOString().slice(0, 10)).slice(0, 5);
    chart.appendChild(label);
  });

  const chartCandidates = rankedCandidates(items);
  const trendSeries = chartCandidates.map((candidate) => ({
    candidate,
    points: weightedTrend(ordered, candidate.key).map((point) => ({
      ...point,
      x: xForTime(Date.parse(`${point.date}T12:00:00Z`)),
      y: yFor(point.value),
    })),
  }));

  trendSeries.forEach(({ candidate, points }) => {
    chart.appendChild(svgElement("path", {
      d: uncertaintyAreaPath(points, yFor, minY, maxY),
      class: "uncertainty-band",
      style: `--candidate-color:${candidate.color}`,
    }));
  });

  chartCandidates.forEach((candidate) => {
    ordered.forEach((poll) => {
      const value = valueFor(poll, candidate.key);
      const circle = svgElement("circle", {
        cx: xForPoll(poll), cy: yFor(value), r: 3.2, class: "poll-point",
        style: `--candidate-color:${candidate.color}`, tabindex: "0",
      });
      const tooltip = svgElement("title");
      tooltip.textContent = `${candidate.name}: ${formatPct(value)} — ${poll.pollster}, ${poll.field}`;
      circle.appendChild(tooltip);
      chart.appendChild(circle);
    });
  });

  trendSeries.forEach(({ candidate, points }) => {
    chart.appendChild(svgElement("path", {
      d: smoothPath(points), class: "average-trend-line", style: `--candidate-color:${candidate.color}`,
    }));
    const endpoint = points.at(-1);
    if (endpoint) {
      const circle = svgElement("circle", { cx: endpoint.x, cy: endpoint.y, r: 4.2, class: "average-endpoint", style: `--candidate-color:${candidate.color}`, tabindex: "0" });
      const tooltip = svgElement("title");
      tooltip.textContent = `${candidate.name}: média ponderada de ${formatPct(endpoint.value)} ± ${formatPct(endpoint.uncertainty)} em ${formatDate(endpoint.date)}`;
      circle.appendChild(tooltip);
      chart.appendChild(circle);
    }
  });
}

function renderLegend(items) {
  chartLegend.innerHTML = rankedCandidates(items).map((candidate) => `<span class="legend-item" style="--candidate-color:${candidate.color}"><i></i>${candidate.name}</span>`).join("");
}

function openPoll(id) {
  const poll = polls.find((item) => item.id === id);
  if (!poll) return;
  const official = officialRecord(poll);
  const contractors = official?.contractors?.length ? official.contractors.map((item) => escapeHtml(item.name)).join("<br>") : "Consulte o PesqEle";
  const company = official?.company || poll.pollster;
  const method = official?.methodology || poll.method;
  const results = sortCandidatesByValue(activeCandidates(), (candidate) => valueFor(poll, candidate.key))
    .map((candidate) => `<div><small>${candidate.name}</small><strong>${formatPct(valueFor(poll, candidate.key))}</strong></div>`).join("");
  dialogContent.innerHTML = `<p class="dialog-eyebrow">FICHA DA PESQUISA <span class="dialog-verified">✓ TSE verificado</span></p>
    <h2>${escapeHtml(poll.pollster)}</h2>
    <p class="dialog-scenario">${state.round === "second" ? "2º turno · Lula × Flávio Bolsonaro" : "1º turno · cenário principal"}</p>
    <div class="dialog-results">${results}</div>
    <div class="detail-grid">
      <div><small>Registro PesqEle</small><strong>${poll.protocol}</strong></div>
      <div><small>Divulgação prevista</small><strong>${formatDate(official?.disclosureDate)}</strong></div>
      <div><small>Campo</small><strong>${poll.field} de 2026</strong></div>
      <div><small>Amostra</small><strong>${integer.format(poll.sample)} entrevistas</strong></div>
      <div><small>Margem / confiança</small><strong>± ${number.format(poll.margin)} p.p. · ${number.format(poll.confidence)}%</strong></div>
      <div><small>Peso no modelo</small><strong>${number.format(pollWeight(poll))}</strong></div>
      <div class="detail-wide"><small>Empresa realizadora no TSE</small><strong>${escapeHtml(company)}</strong></div>
      <div class="detail-wide"><small>Contratante(s) no TSE</small><strong>${contractors}</strong></div>
      ${official ? `<div><small>Estatístico responsável</small><strong>${escapeHtml(official.statistician)}</strong></div><div><small>CONRE</small><strong>${escapeHtml(official.conre)}</strong></div><div><small>Custo registrado</small><strong>${currency.format(official.researchCost)}</strong></div><div><small>Registro efetuado</small><strong>${formatDate(official.registeredAt.slice(0, 10))}</strong></div>` : ""}
    </div>
    <details class="method-details"><summary>Metodologia registrada no TSE</summary><p>${escapeHtml(method)}</p></details>
    <div class="source-links"><a href="${poll.resultSource}" target="_blank" rel="noreferrer">Fonte dos percentuais ↗</a><a href="${PESQELE_URL}" target="_blank" rel="noreferrer">Consultar no PesqEle ↗</a></div>
    <p class="dialog-note"><strong>Como ler:</strong> o TSE fornece os metadados do registro, mas não os percentuais deste cenário no arquivo CSV. Os resultados são conferidos na publicação identificada e ligados ao registro por protocolo, datas e amostra.</p>`;
  dialog.showModal();
}

function downloadCsv() {
  const items = visiblePolls();
  const selectedCandidates = activeCandidates();
  const headers = ["turno", "cenario", "instituto", "divulgacao", "registro_tse", "inicio", "fim", "amostra", "margem", "confianca", "peso_modelo", ...selectedCandidates.map((candidate) => candidate.key), "brancos_nulos_indecisos", "fonte_resultado", "fonte_tse"];
  const rows = items.map((poll) => [state.round === "second" ? 2 : 1, state.round === "second" ? "Lula x Flavio Bolsonaro" : "principal", poll.pollster, poll.publication, poll.protocol, poll.start, poll.end, poll.sample, poll.margin, poll.confidence, pollWeight(poll), ...selectedCandidates.map((candidate) => valueFor(poll, candidate.key)), neutralFor(poll), poll.resultSource, TSE_DATASET_URL]);
  const csvEscape = (value) => `"${String(value).replaceAll('"', '""')}"`;
  const csv = [headers, ...rows].map((row) => row.map(csvEscape).join(",")).join("\n");
  const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `pulso26-${state.round === "second" ? "segundo-turno" : "primeiro-turno"}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function updateStatus() {
  const interviews = polls.reduce((sum, poll) => sum + poll.sample, 0);
  document.querySelector("#status-label").textContent = `${polls.length}/${polls.length} REGISTROS NO PESQELE`;
  document.querySelector("#status-total").textContent = `${polls.length} pesquisas · ${integer.format(interviews)} entrevistas`;
  if (tseData?.generatedAt) document.querySelector("#status-date").textContent = `Base TSE gerada em ${tseData.generatedAt.split(" ")[0]}`;
}

function render() {
  const items = visiblePolls();
  document.querySelector("#scenario-select").value = state.round === "second" ? "runoff" : "main";
  document.querySelector("#polls-title").textContent = state.round === "second" ? "Pesquisas de segundo turno" : "Pesquisas de primeiro turno";
  document.querySelector("#chart-heading").textContent = state.round === "second" ? "Média Lula × Flávio no tempo" : "Evolução da média ponderada";
  renderAverage(items);
  renderTable(items);
  renderChart(items);
  renderLegend(items);
}

async function loadTseData() {
  try {
    const response = await fetch("data/tse-metadata.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    tseData = await response.json();
    polls.forEach((poll) => {
      const official = officialRecord(poll);
      if (!official) return;
      poll.start = official.fieldStart;
      poll.end = official.fieldEnd;
      poll.field = formatField(official.fieldStart, official.fieldEnd);
      poll.sample = official.sample;
    });
    updateStatus();
    render();
  } catch (error) {
    console.warn("Não foi possível carregar o recorte local do TSE.", error);
    document.querySelector("#status-label").textContent = "METADADOS TSE INDISPONÍVEIS";
  }
}

document.querySelector("#period-select").addEventListener("change", (event) => { state.period = event.target.value; render(); });
document.querySelector("#scenario-select").addEventListener("change", (event) => {
  state.round = event.target.value === "runoff" ? "second" : "first";
  document.querySelectorAll("[data-round]").forEach((button) => button.classList.toggle("selected", button.dataset.round === state.round));
  render();
});
document.querySelector("#poll-search").addEventListener("input", (event) => { state.query = event.target.value.trim(); render(); });
document.querySelector("#average-info").addEventListener("click", (event) => {
  const note = document.querySelector("#method-note");
  note.hidden = !note.hidden;
  event.currentTarget.setAttribute("aria-expanded", String(!note.hidden));
});
document.querySelectorAll("[data-round]").forEach((button) => {
  button.addEventListener("click", () => {
    state.round = button.dataset.round;
    document.querySelectorAll("[data-round]").forEach((item) => item.classList.toggle("selected", item === button));
    render();
  });
});
tableBody.addEventListener("click", (event) => {
  const button = event.target.closest("[data-poll-id]");
  if (button) openPoll(Number(button.dataset.pollId));
});
document.querySelector(".dialog-close").addEventListener("click", () => dialog.close());
dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
document.querySelector("#download-csv").addEventListener("click", downloadCsv);

updateStatus();
render();
loadTseData();
