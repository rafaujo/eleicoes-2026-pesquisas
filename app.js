const candidates = [
  { key: "lula", name: "Lula", color: "#0b6b52" },
  { key: "flavio", name: "Flávio Bolsonaro", color: "#dc7046" },
  { key: "caiado", name: "Ronaldo Caiado", color: "#477aaa" },
  { key: "zema", name: "Romeu Zema", color: "#8c6bad" },
  { key: "renan", name: "Renan Santos", color: "#b58a17" },
];

// Base inicial de demonstração, transcrita da página de referência fornecida.
// A versão de produção substituirá esta carga por dados revisados do PesqEle
// e pelos relatórios originais dos institutos.
const polls = [
  { id: 1, pollster: "Genial/Quaest", sponsor: "Genial Investimentos", start: "2026-08-10", end: "2026-08-13", field: "10–13 ago", sample: 2004, margin: 2.0, method: "Entrevistas presenciais", lula: 38, flavio: 31, caiado: 4, zema: 2, renan: 4, undecided: 18 },
  { id: 2, pollster: "PoderData/Aya", sponsor: "Aya", start: "2026-08-09", end: "2026-08-12", field: "9–12 ago", sample: 2400, margin: 2.0, method: "Entrevistas telefônicas", lula: 41, flavio: 35, caiado: 4, zema: 3, renan: 4, undecided: 6 },
  { id: 3, pollster: "Gerp", sponsor: "Divulgação própria", start: "2026-08-06", end: "2026-08-10", field: "6–10 ago", sample: 2400, margin: 2.0, method: "Consultar relatório", lula: 38, flavio: 38, caiado: 4, zema: 2, renan: 5, undecided: 11 },
  { id: 4, pollster: "Nexus/BTG Pactual", sponsor: "BTG Pactual", start: "2026-08-07", end: "2026-08-09", field: "7–9 ago", sample: 2001, margin: 2.0, method: "Entrevistas por recrutamento digital", lula: 40, flavio: 35, caiado: 5, zema: 3, renan: 4, undecided: 8 },
  { id: 5, pollster: "CNT/MDA", sponsor: "CNT", start: "2026-08-05", end: "2026-08-09", field: "5–9 ago", sample: 2002, margin: 2.2, method: "Entrevistas presenciais", lula: 42.4, flavio: 28.7, caiado: 4, zema: 3.3, renan: 2.8, undecided: 14 },
  { id: 6, pollster: "Apex/Futura", sponsor: "Apex Partners", start: "2026-08-03", end: "2026-08-07", field: "3–7 ago", sample: 2000, margin: 2.2, method: "Consultar relatório", lula: 36.3, flavio: 32.7, caiado: 7.7, zema: 4.4, renan: 3.8, undecided: 12.2 },
];

const number = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
const integer = new Intl.NumberFormat("pt-BR");
const state = { period: "all", query: "", round: "first" };

const averageList = document.querySelector("#average-list");
const undecidedAverage = document.querySelector("#undecided-average");
const tableBody = document.querySelector("#poll-table-body");
const pollCount = document.querySelector("#poll-count");
const chart = document.querySelector("#trend-chart");
const chartLegend = document.querySelector("#chart-legend");
const dialog = document.querySelector("#poll-dialog");
const dialogContent = document.querySelector("#dialog-content");

function formatPct(value) {
  return `${number.format(value)}%`;
}

function visiblePolls() {
  const latestDate = new Date("2026-08-16T12:00:00");
  return polls.filter((poll) => {
    const matchesSearch = poll.pollster.toLowerCase().includes(state.query.toLowerCase()) || poll.sponsor.toLowerCase().includes(state.query.toLowerCase());
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
        <td><span class="pollster">${poll.pollster}</span><span class="sponsor">${poll.sponsor}</span></td>
        <td>${poll.field}</td>
        <td>${integer.format(poll.sample)}</td>
        <td>± ${number.format(poll.margin)}</td>
        <td class="${leaderKey === "lula" ? "leader" : ""}">${formatPct(poll.lula)}</td>
        <td class="${leaderKey === "flavio" ? "leader" : ""}">${formatPct(poll.flavio)}</td>
        <td>${formatPct(poll.caiado)}</td>
        <td>${formatPct(poll.zema)}</td>
        <td>${formatPct(poll.renan)}</td>
        <td><span class="difference">${diff === 0 ? "Empate" : `${leaderKey === "lula" ? "L" : "F"} +${number.format(diff)}`}</span></td>
        <td><button class="row-button" type="button" data-poll-id="${poll.id}" aria-label="Ver detalhes de ${poll.pollster}">Ver →</button></td>
      </tr>`;
  }).join("");
  pollCount.textContent = `${items.length} ${items.length === 1 ? "pesquisa exibida" : "pesquisas exibidas"}`;
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
  dialogContent.innerHTML = `
    <p class="dialog-eyebrow">FICHA DA PESQUISA</p>
    <h2>${poll.pollster}</h2>
    <div class="detail-grid">
      <div><small>Contratante</small><strong>${poll.sponsor}</strong></div>
      <div><small>Campo</small><strong>${poll.field} de 2026</strong></div>
      <div><small>Amostra</small><strong>${integer.format(poll.sample)} entrevistas</strong></div>
      <div><small>Margem de erro</small><strong>± ${number.format(poll.margin)} p.p.</strong></div>
      <div><small>Tipo</small><strong>Estimulada · nacional</strong></div>
      <div><small>Método</small><strong>${poll.method}</strong></div>
    </div>
    <p class="dialog-note"><strong>Base demonstrativa.</strong> O registro PesqEle, o questionário e o relatório original serão vinculados durante a integração oficial dos dados.</p>`;
  dialog.showModal();
}

function downloadCsv() {
  const items = visiblePolls();
  const headers = ["instituto", "contratante", "inicio", "fim", "amostra", "margem", ...candidates.map((c) => c.key), "brancos_nulos_indecisos"];
  const rows = items.map((poll) => [poll.pollster, poll.sponsor, poll.start, poll.end, poll.sample, poll.margin, ...candidates.map((c) => poll[c.key]), poll.undecided]);
  const escape = (value) => `"${String(value).replaceAll('"', '""')}"`;
  const csv = [headers, ...rows].map((row) => row.map(escape).join(",")).join("\n");
  const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "pulso26-pesquisas.csv";
  link.click();
  URL.revokeObjectURL(url);
}

function render() {
  const items = visiblePolls();
  renderAverage(items);
  renderTable(items);
  renderChart(items);
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
render();
