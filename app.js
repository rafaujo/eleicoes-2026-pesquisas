const TSE_DATASET_URL = "https://dadosabertos.tse.jus.br/dataset/pesquisas-eleitorais-2026";
const PESQELE_URL = "https://pesqele-divulgacao.tse.jus.br/app/pesquisa/listar.xhtml";
const HALF_LIFE_DAYS = 7;

// Carregado de data/polls.json. Metadados oficiais são reconciliados com data/tse-metadata.json.
let polls = [];
let candidateRegistry = {};
let scenarioCatalog = [];

const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const oneDecimal = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const integer = new Intl.NumberFormat("pt-BR");
const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const state = { period: "21", query: "", round: 1, scenarioId: "first-main" };
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
function activeScenario() {
  return scenarioCatalog.find((scenario) => scenario.id === state.scenarioId)
    || scenarioCatalog.find((scenario) => scenario.round === state.round)
    || null;
}
function scenarioFor(poll) { return poll.scenarios?.[state.scenarioId] || null; }
function activeCandidates() {
  return (activeScenario()?.candidates || []).map((key) => ({ key, ...candidateRegistry[key] }));
}
function valueFor(poll, key) { return scenarioFor(poll)?.results?.[key]; }
function neutralFor(poll) { return scenarioFor(poll)?.undecided; }
function resultSourceFor(poll) { return scenarioFor(poll)?.resultSource || poll.resultSource; }

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
      && Boolean(poll.scenarios?.[state.scenarioId]);
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
  const scenario = activeScenario();
  document.querySelector("#average-title").textContent = scenario?.round === 2 ? scenario.label : "Retrato do momento";
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
  table.classList.toggle("runoff-table", activeScenario()?.round === 2);
  tableHead.innerHTML = `<tr>
    <th>Pesquisa / divulgação</th><th>Período de campo</th><th>Amostra</th><th>Margem</th><th>Peso</th>
    ${visibleCandidates.map((candidate) => `<th>${candidate.shortName}</th>`).join("")}
    <th>Dif.</th><th><span class="sr-only">Detalhes</span></th>
  </tr>`;
  const maxWeight = items.length ? Math.max(...items.map(pollWeight)) : 1;
  tableBody.innerHTML = items.map((poll) => {
    const ranking = sortCandidatesByValue(visibleCandidates, (candidate) => valueFor(poll, candidate.key));
    const leader = ranking[0];
    const runnerUp = ranking[1];
    const diff = runnerUp ? valueFor(poll, leader.key) - valueFor(poll, runnerUp.key) : 0;
    const relativeWeight = pollWeight(poll) / maxWeight;
    return `<tr>
      <td><span class="pollster">${escapeHtml(poll.pollster)}</span><span class="sponsor">${escapeHtml(poll.publication)}</span><span class="verified-badge" title="Registro verificado no PesqEle/TSE">✓ ${poll.protocol}</span></td>
      <td>${poll.field}</td><td>${integer.format(poll.sample)}</td><td>± ${number.format(poll.margin)}</td>
      <td><span class="weight-pill" title="Peso relativo à pesquisa de maior peso no recorte">×${number.format(relativeWeight)}</span></td>
      ${visibleCandidates.map((candidate) => `<td class="${leader.key === candidate.key ? "leader" : ""}">${formatPct(valueFor(poll, candidate.key))}</td>`).join("")}
      <td><span class="difference">${diff === 0 ? "Empate" : `${leader.shortName} +${number.format(diff)}`}</span></td>
      <td><button class="row-button" type="button" data-poll-id="${poll.id}" aria-label="Ver detalhes de ${escapeHtml(poll.pollster)}">Ver →</button></td>
    </tr>`;
  }).join("");
  const verified = items.filter((poll) => officialRecord(poll)).length;
  const scenarioPolls = polls.filter((poll) => Boolean(poll.scenarios?.[state.scenarioId]));
  const discarded = scenarioPolls.filter((poll) => pollAgeDays(poll) > Number(state.period)).length;
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
  title.textContent = `Evolução da média ponderada — ${activeScenario()?.label || "cenário"}`;
  const desc = svgElement("desc", { id: "chart-description" });
  desc.textContent = "As linhas mostram a média ponderada calculada com as pesquisas disponíveis em cada data. As faixas mostram a margem de erro média ponderada e os pontos, o resultado de cada pesquisa.";
  chart.append(title, desc);

  const ordered = [...items].sort((a, b) => a.end.localeCompare(b.end));
  const pad = { left: 46, right: 22, top: 20, bottom: 42 };
  const width = 760 - pad.left - pad.right;
  const height = 360 - pad.top - pad.bottom;
  const isRunoff = activeScenario()?.round === 2;
  const minY = isRunoff ? 25 : 0;
  const maxY = isRunoff ? 55 : 50;
  const yTicks = isRunoff ? [25, 30, 35, 40, 45, 50, 55] : [0, 10, 20, 30, 40, 50];
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
  const scenario = activeScenario();
  const results = sortCandidatesByValue(activeCandidates(), (candidate) => valueFor(poll, candidate.key))
    .map((candidate) => `<div><small>${candidate.name}</small><strong>${formatPct(valueFor(poll, candidate.key))}</strong></div>`).join("");
  dialogContent.innerHTML = `<p class="dialog-eyebrow">FICHA DA PESQUISA <span class="dialog-verified">✓ TSE verificado</span></p>
    <h2>${escapeHtml(poll.pollster)}</h2>
    <p class="dialog-scenario">${scenario?.round || 1}º turno · ${escapeHtml(scenario?.label || "Cenário principal")}</p>
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
    <div class="source-links"><a href="${resultSourceFor(poll)}" target="_blank" rel="noreferrer">Fonte dos percentuais ↗</a><a href="${PESQELE_URL}" target="_blank" rel="noreferrer">Consultar no PesqEle ↗</a></div>
    <p class="dialog-note"><strong>Como ler:</strong> o TSE fornece os metadados do registro, mas não os percentuais deste cenário no arquivo CSV. Os resultados são conferidos na publicação identificada e ligados ao registro por protocolo, datas e amostra.</p>`;
  dialog.showModal();
}

function downloadCsv() {
  const items = visiblePolls();
  const selectedCandidates = activeCandidates();
  const scenario = activeScenario();
  const headers = ["turno", "cenario", "instituto", "divulgacao", "registro_tse", "inicio", "fim", "amostra", "margem", "confianca", "peso_modelo", ...selectedCandidates.map((candidate) => candidate.key), "brancos_nulos_indecisos", "fonte_resultado", "fonte_tse"];
  const rows = items.map((poll) => [scenario.round, scenario.label, poll.pollster, poll.publication, poll.protocol, poll.start, poll.end, poll.sample, poll.margin, poll.confidence, pollWeight(poll), ...selectedCandidates.map((candidate) => valueFor(poll, candidate.key)), neutralFor(poll), resultSourceFor(poll), TSE_DATASET_URL]);
  const csvEscape = (value) => `"${String(value).replaceAll('"', '""')}"`;
  const csv = [headers, ...rows].map((row) => row.map(csvEscape).join(",")).join("\n");
  const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `pulso26-${scenario.id}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function updateStatus() {
  const interviews = polls.reduce((sum, poll) => sum + poll.sample, 0);
  const verified = polls.filter((poll) => officialRecord(poll)).length;
  document.querySelector("#status-label").textContent = tseData
    ? `${verified}/${polls.length} REGISTROS NO PESQELE`
    : `${polls.length} PESQUISAS CARREGADAS`;
  document.querySelector("#status-total").textContent = `${polls.length} pesquisas · ${integer.format(interviews)} entrevistas`;
  if (tseData?.generatedAt) document.querySelector("#status-date").textContent = `Base TSE gerada em ${tseData.generatedAt.split(" ")[0]}`;
}

function render() {
  const items = visiblePolls();
  const scenario = activeScenario();
  const scenarioSelect = document.querySelector("#scenario-select");
  scenarioSelect.innerHTML = scenarioCatalog
    .filter((item) => item.round === state.round)
    .map((item) => `<option value="${item.id}">${escapeHtml(item.label)}</option>`)
    .join("");
  scenarioSelect.value = state.scenarioId;
  document.querySelectorAll("[data-round]").forEach((button) => button.classList.toggle("selected", Number(button.dataset.round) === state.round));
  document.querySelector("#polls-title").textContent = `Pesquisas de ${state.round}º turno`;
  document.querySelector("#chart-heading").textContent = scenario?.round === 2 ? `${scenario.label} no tempo` : "Evolução da média ponderada";
  renderAverage(items);
  renderTable(items);
  renderChart(items);
  renderLegend(items);
}

async function loadData() {
  try {
    const pollsResponse = await fetch("data/polls.json", { cache: "no-store" });
    if (!pollsResponse.ok) throw new Error(`data/polls.json: HTTP ${pollsResponse.status}`);
    const pollData = await pollsResponse.json();
    if (pollData.schemaVersion !== 2 || !Array.isArray(pollData.polls)
      || !pollData.candidates || !Array.isArray(pollData.scenarios)) {
      throw new Error("Formato desconhecido em data/polls.json");
    }
    polls = pollData.polls;
    candidateRegistry = pollData.candidates;
    scenarioCatalog = pollData.scenarios;

    try {
      const metadataResponse = await fetch("data/tse-metadata.json", { cache: "no-store" });
      if (!metadataResponse.ok) throw new Error(`HTTP ${metadataResponse.status}`);
      tseData = await metadataResponse.json();
    } catch (error) {
      console.warn("Não foi possível carregar o recorte local do TSE.", error);
    }

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
    console.error("Não foi possível carregar a base de pesquisas.", error);
    document.querySelector("#status-label").textContent = "BASE DE PESQUISAS INDISPONÍVEL";
    document.querySelector("#status-total").textContent = "Tente recarregar a página";
    render();
  }
}

document.querySelector("#period-select").addEventListener("change", (event) => { state.period = event.target.value; render(); });
document.querySelector("#scenario-select").addEventListener("change", (event) => {
  state.scenarioId = event.target.value;
  state.round = activeScenario()?.round || state.round;
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
    state.round = Number(button.dataset.round);
    state.scenarioId = scenarioCatalog.find((scenario) => scenario.round === state.round)?.id || state.scenarioId;
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

loadData();
