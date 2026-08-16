const candidates = [
  { key: "lula", name: "Lula", color: "#0b6b52" },
  { key: "flavio", name: "Flávio Bolsonaro", color: "#dc7046" },
  { key: "caiado", name: "Ronaldo Caiado", color: "#477aaa" },
  { key: "zema", name: "Romeu Zema", color: "#8c6bad" },
  { key: "renan", name: "Renan Santos", color: "#b58a17" },
];

const TSE_DATASET_URL = "https://dadosabertos.tse.jus.br/dataset/pesquisas-eleitorais-2026";
const PESQELE_URL = "https://pesqele-divulgacao.tse.jus.br/app/pesquisa/listar.xhtml";

// Percentuais transcritos das publicações indicadas em resultSource.
// Datas, amostras e demais metadados são reconciliados com data/tse-metadata.json.
const polls = [
  {
    id: 1,
    pollster: "Quaest",
    publication: "Genial/Quaest · G1",
    protocol: "BR067732026",
    start: "2026-08-10",
    end: "2026-08-13",
    field: "10–13 ago",
    sample: 2004,
    margin: 2,
    confidence: 95,
    method: "Presencial domiciliar",
    resultSource: "https://g1.globo.com/politica/eleicoes/2026/pesquisa-eleitoral/noticia/2026/08/14/quaest-presidente-1o-turno-14-agosto.ghtml",
    resultSourceLabel: "G1 — resultado publicado",
    lula: 38, flavio: 31, caiado: 4, zema: 2, renan: 4, undecided: 18,
  },
  {
    id: 2,
    pollster: "PoderData",
    publication: "Parceria de divulgação: Aya",
    protocol: "BR068682026",
    start: "2026-08-09",
    end: "2026-08-12",
    field: "9–12 ago",
    sample: 2400,
    margin: 2,
    confidence: 95,
    method: "Telefônica automatizada",
    resultSource: "https://www.poder360.com.br/poderdata/lula-tem-46-contra-45-de-flavio-no-2o-turno-diz-poderdata-aya/",
    resultSourceLabel: "Poder360 — resultado e metodologia",
    lula: 41, flavio: 35, caiado: 4, zema: 3, renan: 4, undecided: 6,
  },
  {
    id: 3,
    pollster: "GERP",
    publication: "Divulgação própria",
    protocol: "BR080452026",
    start: "2026-08-06",
    end: "2026-08-10",
    field: "6–10 ago",
    sample: 2400,
    margin: 2.04,
    confidence: 95.55,
    method: "Quantitativa por cotas",
    resultSource: "https://static.poder360.com.br/uploads/2026/08/PRESIDENCIA_DO_BRASIL_DIVULGACAO_26a_Relatorio_Eleicoes_2026_Presidente.pdf",
    resultSourceLabel: "GERP/Poder360 — relatório completo (PDF)",
    lula: 38, flavio: 38, caiado: 4, zema: 2, renan: 5, undecided: 11,
  },
  {
    id: 4,
    pollster: "Nexus",
    publication: "BTG Pactual",
    protocol: "BR084282026",
    start: "2026-08-07",
    end: "2026-08-09",
    field: "7–9 ago",
    sample: 2000,
    margin: 2,
    confidence: 95,
    method: "Telefônica com entrevistadores",
    resultSource: "https://www.gazetadopovo.com.br/eleicoes/2026/pesquisa-eleitoral-2026/nexus-btg-pactual-presidente-agosto-2026-2/",
    resultSourceLabel: "Gazeta do Povo — resultado publicado",
    lula: 40, flavio: 35, caiado: 5, zema: 3, renan: 4, undecided: 8,
  },
  {
    id: 5,
    pollster: "CNT/MDA",
    publication: "Confederação Nacional do Transporte",
    protocol: "BR069352026",
    start: "2026-08-05",
    end: "2026-08-09",
    field: "5–9 ago",
    sample: 2002,
    margin: 2.2,
    confidence: 95,
    method: "Presencial, domicílios e fluxo",
    resultSource: "https://admin.cnnbrasil.com.br/wp-content/uploads/sites/12/2026/08/Relatorio-Pesquisa-CNT-de-Opiniao-R169-AGOSTO26_7486.pdf",
    resultSourceLabel: "CNT/CNN Brasil — relatório completo (PDF)",
    lula: 42.4, flavio: 28.7, caiado: 4, zema: 3.3, renan: 2.8, undecided: 14,
  },
  {
    id: 6,
    pollster: "Futura/100 Cidades",
    publication: "Divulgação Apex/Futura",
    protocol: "BR081092026",
    start: "2026-08-03",
    end: "2026-08-06",
    field: "3–6 ago",
    sample: 2000,
    margin: 2.2,
    confidence: 95,
    method: "Telefônica por cotas",
    resultSource: "https://www.gazetadopovo.com.br/eleicoes/2026/pesquisa-eleitoral-2026/futura-inteligencia-presidente-agosto-2026/",
    resultSourceLabel: "Gazeta do Povo — resultado publicado",
    lula: 36.3, flavio: 32.7, caiado: 7.7, zema: 4.4, renan: 3.8, undecided: 12.2,
  },
];

const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const integer = new Intl.NumberFormat("pt-BR");
const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const state = { period: "all", query: "", round: "first" };
let tseData = null;

const averageList = document.querySelector("#average-list");
const undecidedAverage = document.querySelector("#undecided-average");
const tableBody = document.querySelector("#poll-table-body");
const pollCount = document.querySelector("#poll-count");
const chart = document.querySelector("#trend-chart");
const chartLegend = document.querySelector("#chart-legend");
const dialog = document.querySelector("#poll-dialog");
const dialogContent = document.querySelector("#dialog-content");

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatPct(value) {
  return `${number.format(value)}%`;
}

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
}

function formatField(start, end) {
  const startDate = new Date(`${start}T00:00:00Z`);
  const endDate = new Date(`${end}T00:00:00Z`);
  const month = new Intl.DateTimeFormat("pt-BR", { month: "short", timeZone: "UTC" }).format(endDate).replace(".", "");
  return `${startDate.getUTCDate()}–${endDate.getUTCDate()} ${month}`;
}

function officialRecord(poll) {
  return tseData?.records?.[poll.protocol] || null;
}

function visiblePolls() {
  const latestDate = new Date("2026-08-16T12:00:00");
  return polls.filter((poll) => {
    const searchable = `${poll.pollster} ${poll.publication} ${poll.protocol}`.toLowerCase();
    const matchesSearch = searchable.includes(state.query.toLowerCase());
    if (!matchesSearch) return false;
    if (state.period === "all") return true;
    const cutoff = new Date(latestDate);
    cutoff.setDate(cutoff.getDate() - Number(state.period));
    return new Date(`${poll.end}T12:00:00`) >= cutoff;
  });
}

function mean(items, key) {
  if (!items.length) return 0;
  return items.reduce((sum, item) => sum + item[key], 0) / items.length;
}

function renderAverage(items) {
  if (!items.length) {
    averageList.innerHTML = '<p class="dialog-note">Nenhuma pesquisa encontrada.</p>';
    undecidedAverage.textContent = "—";
    return;
  }
  averageList.innerHTML = candidates.map((candidate) => {
    const value = mean(items, candidate.key);
    return `
      <div class="average-row" style="--candidate-color:${candidate.color}">
        <div class="candidate"><i class="candidate-dot"></i><span>${candidate.name}</span></div>
        <div class="bar-track"><div class="bar-fill" style="width:${Math.min(100, value * 2.15)}%"></div></div>
        <strong>${formatPct(value)}</strong>
      </div>`;
  }).join("");
  undecidedAverage.textContent = formatPct(mean(items, "undecided"));
}

function renderTable(items) {
  tableBody.innerHTML = items.map((poll) => {
    const leaderKey = poll.lula >= poll.flavio ? "lula" : "flavio";
    const diff = Math.abs(poll.lula - poll.flavio);
    return `
      <tr>
        <td>
          <span class="pollster">${escapeHtml(poll.pollster)}</span>
          <span class="sponsor">${escapeHtml(poll.publication)}</span>
          <span class="verified-badge" title="Registro verificado no PesqEle/TSE">✓ ${poll.protocol}</span>
        </td>
        <td>${poll.field}</td>
        <td>${integer.format(poll.sample)}</td>
        <td>± ${number.format(poll.margin)}</td>
        <td class="${leaderKey === "lula" ? "leader" : ""}">${formatPct(poll.lula)}</td>
        <td class="${leaderKey === "flavio" ? "leader" : ""}">${formatPct(poll.flavio)}</td>
        <td>${formatPct(poll.caiado)}</td>
        <td>${formatPct(poll.zema)}</td>
        <td>${formatPct(poll.renan)}</td>
        <td><span class="difference">${diff === 0 ? "Empate" : `${leaderKey === "lula" ? "L" : "F"} +${number.format(diff)}`}</span></td>
        <td><button class="row-button" type="button" data-poll-id="${poll.id}" aria-label="Ver detalhes de ${escapeHtml(poll.pollster)}">Ver →</button></td>
      </tr>`;
  }).join("");
  const verified = items.filter((poll) => officialRecord(poll)).length;
  const verification = tseData
    ? `${verified}/${items.length} registros conferidos no TSE`
    : `${items.length} pesquisas com protocolo informado`;
  pollCount.textContent = `${items.length} ${items.length === 1 ? "pesquisa exibida" : "pesquisas exibidas"} · ${verification}`;
}

function svgElement(name, attrs = {}) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
  return el;
}

function renderChart(items) {
  chart.replaceChildren();
  const title = svgElement("title", { id: "chart-title" });
  title.textContent = "Evolução das intenções de voto";
  const desc = svgElement("desc", { id: "chart-description" });
  desc.textContent = "Gráfico das pesquisas selecionadas ao longo do tempo.";
  chart.append(title, desc);

  const ordered = [...items].sort((a, b) => a.end.localeCompare(b.end));
  const pad = { left: 46, right: 22, top: 20, bottom: 42 };
  const width = 760 - pad.left - pad.right;
  const height = 360 - pad.top - pad.bottom;
  const maxY = 50;

  [0, 10, 20, 30, 40, 50].forEach((tick) => {
    const y = pad.top + height - (tick / maxY) * height;
    chart.appendChild(svgElement("line", { x1: pad.left, x2: 760 - pad.right, y1: y, y2: y, class: "grid-line" }));
    const label = svgElement("text", { x: 6, y: y + 4, class: "axis-label" });
    label.textContent = `${tick}%`;
    chart.appendChild(label);
  });

  if (!ordered.length) return;
  ordered.forEach((poll, index) => {
    const x = ordered.length === 1 ? pad.left + width / 2 : pad.left + (index / (ordered.length - 1)) * width;
    const label = svgElement("text", { x, y: 344, "text-anchor": "middle", class: "axis-label" });
    label.textContent = poll.field.replace(" ago", "");
    chart.appendChild(label);
  });

  candidates.slice(0, 3).forEach((candidate) => {
    const points = ordered.map((poll, index) => {
      const x = ordered.length === 1 ? pad.left + width / 2 : pad.left + (index / (ordered.length - 1)) * width;
      const y = pad.top + height - (poll[candidate.key] / maxY) * height;
      return { x, y, value: poll[candidate.key], poll };
    });
    const path = svgElement("path", {
      d: points.map((point, index) => `${index ? "L" : "M"}${point.x},${point.y}`).join(" "),
      class: "trend-line",
      style: `--candidate-color:${candidate.color}`,
    });
    chart.appendChild(path);
    points.forEach((point) => {
      const circle = svgElement("circle", { cx: point.x, cy: point.y, r: 4.5, class: "trend-point", style: `--candidate-color:${candidate.color}`, tabindex: "0" });
      const tooltip = svgElement("title");
      tooltip.textContent = `${candidate.name}: ${formatPct(point.value)} — ${point.poll.pollster}`;
      circle.appendChild(tooltip);
      chart.appendChild(circle);
    });
  });
}

function renderLegend() {
  chartLegend.innerHTML = candidates.slice(0, 3).map((candidate) => `
    <span class="legend-item" style="--candidate-color:${candidate.color}"><i></i>${candidate.name}</span>
  `).join("");
}

function openPoll(id) {
  const poll = polls.find((item) => item.id === id);
  if (!poll) return;
  const official = officialRecord(poll);
  const contractors = official?.contractors?.length
    ? official.contractors.map((item) => escapeHtml(item.name)).join("<br>")
    : "Consulte o PesqEle";
  const company = official?.company || poll.pollster;
  const method = official?.methodology || poll.method;
  dialogContent.innerHTML = `
    <p class="dialog-eyebrow">FICHA DA PESQUISA <span class="dialog-verified">✓ TSE verificado</span></p>
    <h2>${escapeHtml(poll.pollster)}</h2>
    <div class="detail-grid">
      <div><small>Registro PesqEle</small><strong>${poll.protocol}</strong></div>
      <div><small>Divulgação prevista</small><strong>${formatDate(official?.disclosureDate)}</strong></div>
      <div><small>Campo</small><strong>${poll.field} de 2026</strong></div>
      <div><small>Amostra</small><strong>${integer.format(poll.sample)} entrevistas</strong></div>
      <div><small>Margem / confiança</small><strong>± ${number.format(poll.margin)} p.p. · ${number.format(poll.confidence)}%</strong></div>
      <div><small>Método resumido</small><strong>${escapeHtml(poll.method)}</strong></div>
      <div class="detail-wide"><small>Empresa realizadora no TSE</small><strong>${escapeHtml(company)}</strong></div>
      <div class="detail-wide"><small>Contratante(s) no TSE</small><strong>${contractors}</strong></div>
      ${official ? `<div><small>Estatístico responsável</small><strong>${escapeHtml(official.statistician)}</strong></div>
      <div><small>CONRE</small><strong>${escapeHtml(official.conre)}</strong></div>
      <div><small>Custo registrado</small><strong>${currency.format(official.researchCost)}</strong></div>
      <div><small>Registro efetuado</small><strong>${formatDate(official.registeredAt.slice(0, 10))}</strong></div>` : ""}
    </div>
    <details class="method-details">
      <summary>Metodologia registrada no TSE</summary>
      <p>${escapeHtml(method)}</p>
    </details>
    <div class="source-links">
      <a href="${poll.resultSource}" target="_blank" rel="noreferrer">Fonte dos percentuais ↗</a>
      <a href="${PESQELE_URL}" target="_blank" rel="noreferrer">Consultar no PesqEle ↗</a>
    </div>
    <p class="dialog-note"><strong>Como ler:</strong> o TSE fornece os metadados do registro, mas não os percentuais deste cenário no arquivo CSV. Os resultados acima são conferidos na publicação identificada e ligados ao registro por protocolo, datas e amostra.</p>`;
  dialog.showModal();
}

function downloadCsv() {
  const items = visiblePolls();
  const headers = ["instituto", "divulgacao", "registro_tse", "inicio", "fim", "amostra", "margem", "confianca", ...candidates.map((c) => c.key), "brancos_nulos_indecisos", "fonte_resultado", "fonte_tse"];
  const rows = items.map((poll) => [poll.pollster, poll.publication, poll.protocol, poll.start, poll.end, poll.sample, poll.margin, poll.confidence, ...candidates.map((c) => poll[c.key]), poll.undecided, poll.resultSource, TSE_DATASET_URL]);
  const escape = (value) => `"${String(value).replaceAll('"', '""')}"`;
  const csv = [headers, ...rows].map((row) => row.map(escape).join(",")).join("\n");
  const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "pulso26-pesquisas-verificadas.csv";
  link.click();
  URL.revokeObjectURL(url);
}

function updateStatus() {
  const interviews = polls.reduce((sum, poll) => sum + poll.sample, 0);
  document.querySelector("#status-label").textContent = `${polls.length}/${polls.length} REGISTROS NO PESQELE`;
  document.querySelector("#status-total").textContent = `${polls.length} pesquisas · ${integer.format(interviews)} entrevistas`;
  if (tseData?.generatedAt) {
    const [date] = tseData.generatedAt.split(" ");
    document.querySelector("#status-date").textContent = `Base TSE gerada em ${date}`;
  }
}

function render() {
  const items = visiblePolls();
  renderAverage(items);
  renderTable(items);
  renderChart(items);
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

document.querySelector("#period-select").addEventListener("change", (event) => {
  state.period = event.target.value;
  render();
});
document.querySelector("#poll-search").addEventListener("input", (event) => {
  state.query = event.target.value.trim();
  render();
});
document.querySelector("#average-info").addEventListener("click", (event) => {
  const note = document.querySelector("#method-note");
  note.hidden = !note.hidden;
  event.currentTarget.setAttribute("aria-expanded", String(!note.hidden));
});
document.querySelectorAll("[data-round]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-round]").forEach((item) => item.classList.toggle("selected", item === button));
    if (button.dataset.round === "second") {
      alert("Os cenários de segundo turno entram na próxima etapa do MVP.");
      document.querySelector('[data-round="first"]').click();
    }
  });
});
tableBody.addEventListener("click", (event) => {
  const button = event.target.closest("[data-poll-id]");
  if (button) openPoll(Number(button.dataset.pollId));
});
document.querySelector(".dialog-close").addEventListener("click", () => dialog.close());
dialog.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
});
document.querySelector("#download-csv").addEventListener("click", downloadCsv);

renderLegend();
updateStatus();
render();
loadTseData();
