const TSE_DATASET_URL = "https://dadosabertos.tse.jus.br/dataset/pesquisas-eleitorais-2026";
const PESQELE_URL = "https://pesqele-divulgacao.tse.jus.br/app/pesquisa/listar.xhtml";
const HALF_LIFE_DAYS = 7;

// Cada eleição aponta para sua própria base no catálogo data/elections.json.
let polls = [];
let candidateRegistry = {};
let scenarioCatalog = [];
let electionCatalog = [];
let currentElection = null;

const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const oneDecimal = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const integer = new Intl.NumberFormat("pt-BR");
const currency = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const state = { electionId: "president-br", period: "21", query: "", round: 1, scenarioId: "first-main" };
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
let tseMonitor = null;

const averageList = document.querySelector("#average-list");
const undecidedAverage = document.querySelector("#undecided-average");
const table = document.querySelector(".table-wrap table");
const tableHead = document.querySelector("#poll-table-head");
const tableBody = document.querySelector("#poll-table-body");
const pollCount = document.querySelector("#poll-count");
const chart = document.querySelector("#trend-chart");
const chartLegend = document.querySelector("#chart-legend");
const upcomingSection = document.querySelector("#proximas-pesquisas");
const upcomingList = document.querySelector("#upcoming-list");
const upcomingCount = document.querySelector("#upcoming-count");
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
function resultSourceLabelFor(poll) { return scenarioFor(poll)?.resultSourceLabel || poll.resultSourceLabel; }

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
    const relativeWeightLabel = relativeWeight < 0.01 ? "<0,01" : number.format(relativeWeight);
    const isVerified = Boolean(officialRecord(poll));
    const protocolBadge = isVerified
      ? `<span class="verified-badge" title="Registro conferido no recorte local do PesqEle/TSE">✓ ${poll.protocol}</span>`
      : `<span class="verified-badge protocol-badge" title="Protocolo informado na fonte da pesquisa">REG ${poll.protocol}</span>`;
    return `<tr>
      <td><span class="pollster">${escapeHtml(poll.pollster)}</span><span class="sponsor">${escapeHtml(poll.publication)}</span>${protocolBadge}</td>
      <td>${poll.field}</td><td>${integer.format(poll.sample)}</td><td>± ${number.format(poll.margin)}</td>
      <td><span class="weight-pill" title="Peso relativo à pesquisa de maior peso no recorte">×${relativeWeightLabel}</span></td>
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
  return points.map((point, index) => `${index ? "L" : "M"}${point.x},${point.y}`).join(" ");
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
  const plottedValues = ordered.flatMap((poll) => activeCandidates()
    .map((candidate) => valueFor(poll, candidate.key))
    .filter(Number.isFinite));
  const observedMin = plottedValues.length ? Math.min(...plottedValues) : 0;
  const observedMax = plottedValues.length ? Math.max(...plottedValues) : 50;
  const tickStep = isRunoff ? 5 : 10;
  const minY = isRunoff ? Math.max(0, Math.floor((observedMin - 5) / tickStep) * tickStep) : 0;
  const maxY = Math.max(tickStep, Math.ceil((observedMax + 5) / tickStep) * tickStep);
  const yTicks = Array.from({ length: Math.round((maxY - minY) / tickStep) + 1 }, (_, index) => minY + index * tickStep);
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
  const registrationBadge = official ? "✓ TSE conferido" : `REG ${poll.protocol}`;
  const disclosureLabel = official ? "Divulgação prevista" : "Publicação";
  const disclosureDate = official?.disclosureDate || poll.published;
  const companyLabel = official ? "Empresa realizadora no TSE" : "Instituto";
  const contractorsLabel = official ? "Contratante(s) no TSE" : "Contratante / divulgação";
  const methodologyLabel = official ? "Metodologia registrada no TSE" : "Metodologia informada";
  const metadataNote = official
    ? "O recorte local do PesqEle fornece os metadados do registro, mas não os percentuais deste cenário. Os resultados são conferidos na publicação identificada e ligados ao registro por protocolo, datas e amostra."
    : "O protocolo, as datas, a amostra e os resultados desta ficha foram conferidos na publicação ou no relatório identificado. Use o link do PesqEle para consultar o cadastro oficial.";
  const results = sortCandidatesByValue(activeCandidates(), (candidate) => valueFor(poll, candidate.key))
    .map((candidate) => `<div><small>${candidate.name}</small><strong>${formatPct(valueFor(poll, candidate.key))}</strong></div>`).join("");
  dialogContent.innerHTML = `<p class="dialog-eyebrow">FICHA DA PESQUISA <span class="dialog-verified">${registrationBadge}</span></p>
    <h2>${escapeHtml(poll.pollster)}</h2>
    <p class="dialog-scenario">${scenario?.round || 1}º turno · ${escapeHtml(scenario?.label || "Cenário principal")}</p>
    <div class="dialog-results">${results}</div>
    <div class="detail-grid">
      <div><small>Registro PesqEle</small><strong>${poll.protocol}</strong></div>
      <div><small>${disclosureLabel}</small><strong>${formatDate(disclosureDate)}</strong></div>
      <div><small>Campo</small><strong>${poll.field} de 2026</strong></div>
      <div><small>Amostra</small><strong>${integer.format(poll.sample)} entrevistas</strong></div>
      <div><small>Margem / confiança</small><strong>± ${number.format(poll.margin)} p.p. · ${number.format(poll.confidence)}%</strong></div>
      <div><small>Peso no modelo</small><strong>${number.format(pollWeight(poll))}</strong></div>
      <div class="detail-wide"><small>${companyLabel}</small><strong>${escapeHtml(company)}</strong></div>
      <div class="detail-wide"><small>${contractorsLabel}</small><strong>${official ? contractors : escapeHtml(poll.publication)}</strong></div>
      ${official ? `<div><small>Estatístico responsável</small><strong>${escapeHtml(official.statistician)}</strong></div><div><small>CONRE</small><strong>${escapeHtml(official.conre)}</strong></div><div><small>Custo registrado</small><strong>${currency.format(official.researchCost)}</strong></div><div><small>Registro efetuado</small><strong>${formatDate(official.registeredAt.slice(0, 10))}</strong></div>` : ""}
    </div>
    <details class="method-details"><summary>${methodologyLabel}</summary><p>${escapeHtml(method)}</p></details>
    <div class="source-links"><a href="${resultSourceFor(poll)}" target="_blank" rel="noreferrer">${escapeHtml(resultSourceLabelFor(poll) || "Fonte dos percentuais")} ↗</a><a href="${PESQELE_URL}" target="_blank" rel="noreferrer">Consultar no PesqEle ↗</a></div>
    <p class="dialog-note"><strong>Como ler:</strong> ${metadataNote}</p>`;
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
  link.download = `pulso26-${state.electionId}-${scenario.id}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

function updateStatus() {
  const interviews = polls.reduce((sum, poll) => sum + poll.sample, 0);
  const verified = polls.filter((poll) => officialRecord(poll)).length;
  document.querySelector("#status-label").textContent = tseData
    ? `${verified}/${polls.length} REGISTROS NO PESQELE`
    : `${polls.length} PROTOCOLOS INFORMADOS`;
  document.querySelector("#status-total").textContent = `${polls.length} pesquisas · ${integer.format(interviews)} entrevistas`;
  const latestPublication = polls
    .map((poll) => poll.published || officialRecord(poll)?.disclosureDate || poll.end)
    .filter(Boolean)
    .sort()
    .at(-1);
  document.querySelector("#status-date").textContent = `Resultados incorporados até ${formatDate(latestPublication)}`;

  const monitorDate = tseMonitor?.sourceGeneratedAt?.match(/^\d{4}-\d{2}-\d{2}/)?.[0];
  const legacyMetadataDate = tseData?.generatedAt?.match(/^(\d{2})\/(\d{2})\/(\d{4})/);
  const metadataDate = legacyMetadataDate
    ? `${legacyMetadataDate[3]}-${legacyMetadataDate[2]}-${legacyMetadataDate[1]}`
    : tseData?.generatedAt?.match(/^\d{4}-\d{2}-\d{2}/)?.[0];
  const tseDate = monitorDate || metadataDate;
  document.querySelector("#status-tse-date").textContent = tseDate
    ? `Cadastro do TSE monitorado em ${formatDate(tseDate)}`
    : "Monitoramento do TSE indisponível";
}

function upcomingStatus(item) {
  if (item.disclosureDate > DATA_REFERENCE_DATE) {
    return { label: `Divulgação em ${formatDate(item.disclosureDate)}`, className: "future" };
  }
  if (item.disclosureDate === DATA_REFERENCE_DATE) {
    return { label: "Divulgação prevista hoje", className: "today" };
  }
  return { label: `Aguardando incorporação desde ${formatDate(item.disclosureDate)}`, className: "review" };
}

function renderUpcoming() {
  const items = Object.values(tseMonitor?.pending || {})
    .filter((item) => item?.protocol && item?.disclosureDate)
    .sort((a, b) => a.disclosureDate.localeCompare(b.disclosureDate)
      || (a.fieldEnd || "").localeCompare(b.fieldEnd || "")
      || a.protocol.localeCompare(b.protocol));

  upcomingSection.hidden = items.length === 0;
  upcomingCount.textContent = items.length === 1
    ? "1 pesquisa registrada"
    : `${items.length} pesquisas registradas`;
  upcomingList.innerHTML = items.map((item) => {
    const status = upcomingStatus(item);
    const institute = item.tradeName || item.company || "Instituto não informado";
    const contractor = (item.contractors || []).filter(Boolean).join(" · ") || "Contratante não informado";
    const field = item.fieldStart && item.fieldEnd ? formatField(item.fieldStart, item.fieldEnd) : "—";
    return `<article class="upcoming-card">
      <div class="upcoming-card-header">
        <div><span class="pollster">${escapeHtml(institute)}</span><span class="sponsor">${escapeHtml(contractor)}</span></div>
        <time class="upcoming-date ${status.className}" datetime="${item.disclosureDate}">${status.label}</time>
      </div>
      <dl class="upcoming-details">
        <div><dt>Campo</dt><dd>${field}</dd></div>
        <div><dt>Amostra</dt><dd>${item.sample ? integer.format(item.sample) : "—"}</dd></div>
        <div><dt>Registro</dt><dd>${escapeHtml(item.protocol)}</dd></div>
      </dl>
      <a class="upcoming-link" href="${PESQELE_URL}" target="_blank" rel="noreferrer">Consultar no PesqEle ↗</a>
    </article>`;
  }).join("");
}

function renderElectionChrome() {
  if (!currentElection) return;
  document.querySelector("#hero-eyebrow").innerHTML = `<span></span> ${escapeHtml(currentElection.eyebrow)}`;
  document.querySelector("#titulo-principal").textContent = currentElection.title;
  document.title = `${currentElection.label} · Pulso 26`;
  document.querySelector("#source-heading").textContent = tseData ? "Duas camadas de fonte." : "Fontes rastreáveis.";
  document.querySelector("#source-copy").textContent = tseData
    ? "Cadastro, campo, amostra e metodologia vêm do PesqEle/TSE. Os percentuais vêm do relatório ou da publicação ligada em cada ficha."
    : "Protocolo, campo, amostra, metodologia e percentuais vêm do relatório ou da publicação ligada em cada ficha; a consulta oficial continua disponível no PesqEle.";
  document.querySelector("#principles-copy").textContent = tseData
    ? "Cada número precisa ser rastreável até sua origem. Esta versão combina os metadados oficiais do PesqEle com os relatórios e publicações dos resultados."
    : "Cada número precisa ser rastreável até sua origem. A base paulista liga cada resultado ao protocolo e à publicação ou relatório; o cruzamento automático completo com o PesqEle é o próximo passo.";
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
  document.querySelectorAll("[data-round]").forEach((button) => {
    const round = Number(button.dataset.round);
    button.classList.toggle("selected", round === state.round);
    button.disabled = !scenarioCatalog.some((item) => item.round === round);
  });
  document.querySelector("#polls-title").textContent = `Pesquisas de ${state.round}º turno`;
  document.querySelector("#chart-heading").textContent = scenario?.round === 2 ? `${scenario.label} no tempo` : "Evolução da média ponderada";
  renderAverage(items);
  renderTable(items);
  renderChart(items);
  renderLegend(items);
}

async function loadElection(electionId) {
  const selected = electionCatalog.find((election) => election.id === electionId) || electionCatalog[0];
  if (!selected) throw new Error("Catálogo sem eleições");
  currentElection = selected;
  state.electionId = selected.id;
  state.period = selected.defaultPeriod || "21";
  state.scenarioId = selected.defaultScenario || "first-main";
  state.round = 1;
  state.query = "";
  document.querySelector("#period-select").value = state.period;
  document.querySelector("#poll-search").value = "";
  tseData = null;
  tseMonitor = null;

  const pollsResponse = await fetch(selected.dataFile, { cache: "no-store" });
  if (!pollsResponse.ok) throw new Error(`${selected.dataFile}: HTTP ${pollsResponse.status}`);
  const pollData = await pollsResponse.json();
  if (pollData.schemaVersion !== 2 || !Array.isArray(pollData.polls)
    || !pollData.candidates || !Array.isArray(pollData.scenarios)) {
    throw new Error(`Formato desconhecido em ${selected.dataFile}`);
  }
  polls = pollData.polls;
  candidateRegistry = pollData.candidates;
  scenarioCatalog = pollData.scenarios;

  if (selected.metadataFile) {
    try {
      const metadataResponse = await fetch(selected.metadataFile, { cache: "no-store" });
      if (!metadataResponse.ok) throw new Error(`HTTP ${metadataResponse.status}`);
      tseData = await metadataResponse.json();
    } catch (error) {
      console.warn("Não foi possível carregar o recorte local do TSE.", error);
    }
  }

  if (selected.monitorFile) {
    try {
      const monitorResponse = await fetch(selected.monitorFile, { cache: "no-store" });
      if (!monitorResponse.ok) throw new Error(`HTTP ${monitorResponse.status}`);
      tseMonitor = await monitorResponse.json();
    } catch (error) {
      console.warn("Não foi possível carregar o estado do monitor do TSE.", error);
    }
  }

  polls.forEach((poll) => {
    const official = officialRecord(poll);
    if (!official) return;
    poll.start = official.fieldStart;
    poll.end = official.fieldEnd;
    poll.field = formatField(official.fieldStart, official.fieldEnd);
    poll.sample = official.sample;
  });

  const url = new URL(window.location.href);
  if (selected.id === electionCatalog[0]?.id) url.searchParams.delete("eleicao");
  else url.searchParams.set("eleicao", selected.id);
  window.history.replaceState({}, "", url);
  document.querySelector("#election-select").value = selected.id;
  renderElectionChrome();
  updateStatus();
  renderUpcoming();
  render();
}

async function loadData() {
  try {
    const catalogResponse = await fetch("data/elections.json", { cache: "no-store" });
    if (!catalogResponse.ok) throw new Error(`data/elections.json: HTTP ${catalogResponse.status}`);
    const catalog = await catalogResponse.json();
    if (catalog.schemaVersion !== 1 || !Array.isArray(catalog.elections) || !catalog.elections.length) {
      throw new Error("Formato desconhecido em data/elections.json");
    }
    electionCatalog = catalog.elections;
    const electionSelect = document.querySelector("#election-select");
    const electionGroups = new Map();
    electionCatalog.forEach((election) => {
      const group = election.group || "Eleições";
      if (!electionGroups.has(group)) electionGroups.set(group, []);
      electionGroups.get(group).push(election);
    });
    electionSelect.innerHTML = [...electionGroups.entries()]
      .map(([group, elections]) => `
        <optgroup label="${escapeHtml(group)}">
          ${elections.map((election) => `<option value="${election.id}">${escapeHtml(election.label)} · ${escapeHtml(election.context)}</option>`).join("")}
        </optgroup>
      `)
      .join("");
    const requestedElection = new URLSearchParams(window.location.search).get("eleicao");
    await loadElection(requestedElection || catalog.defaultElection);
  } catch (error) {
    console.error("Não foi possível carregar a base de pesquisas.", error);
    document.querySelector("#status-label").textContent = "BASE DE PESQUISAS INDISPONÍVEL";
    document.querySelector("#status-total").textContent = "Tente recarregar a página";
    render();
  }
}

document.querySelector("#period-select").addEventListener("change", (event) => { state.period = event.target.value; render(); });
document.querySelector("#election-select").addEventListener("change", async (event) => {
  try {
    await loadElection(event.target.value);
  } catch (error) {
    console.error("Não foi possível trocar a eleição.", error);
    document.querySelector("#status-label").textContent = "BASE DE PESQUISAS INDISPONÍVEL";
  }
});
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
