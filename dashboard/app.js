const statusClassByState = {
  running: "badge badge--running",
  completed: "badge badge--completed",
  queued: "badge badge--queued",
  blocked: "badge badge--blocked",
  watching: "badge badge--watching",
};

async function loadDashboard() {
  const app = document.querySelector("#app");

  try {
    const response = await fetch("./status.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`status.json returned ${response.status}`);
    }

    const data = await response.json();
    document.title = `${data.meta.title} - status dashboard`;
    document.querySelector("#hero-meta").append(renderMetaCard("Last updated", data.meta.updatedAt));
    app.replaceChildren(renderDashboard(data));
  } catch (error) {
    app.replaceChildren(renderError(error));
  }
}

function renderDashboard(data) {
  const container = document.createElement("div");
  container.className = "dashboard-grid";

  container.append(
    renderHighlights(data.highlights),
    renderJobs(data.jobs),
    renderResults(data.results),
    renderOperationalNotes(data.operationalNotes),
    renderRefreshInstructions(data.refresh),
    renderSources(data.sources),
  );

  return container;
}

function renderHighlights(highlights) {
  const section = renderPanelSection("Snapshot", "The fast read on current progress.");
  const grid = document.createElement("div");
  grid.className = "stats-grid";

  highlights.forEach((item) => {
    const card = document.createElement("article");
    card.className = "stat-card";
    card.innerHTML = `
      <span class="stat-card__label">${escapeHtml(item.label)}</span>
      <h3 class="stat-card__value">${escapeHtml(item.value)}</h3>
      <p class="stat-card__detail">${escapeHtml(item.detail)}</p>
    `;
    grid.append(card);
  });

  section.querySelector(".panel").append(grid);
  return section;
}

function renderJobs(jobs) {
  const section = renderPanelSection(
    "Live and recent jobs",
    "Training lanes, baseline runs, and the next cap-track push."
  );
  const grid = document.createElement("div");
  grid.className = "jobs-grid";

  jobs.forEach((job) => {
    const card = document.createElement("article");
    card.className = "job-card";
    card.innerHTML = `
      <div class="job-card__topline">
        <div>
          <p>${escapeHtml(job.platform)}</p>
          <h3 class="job-card__title">${escapeHtml(job.name)}</h3>
        </div>
        <span class="${statusClassByState[job.status] || "badge"}">${escapeHtml(job.statusLabel || job.status)}</span>
      </div>
      <p class="job-card__summary">${escapeHtml(job.summary)}</p>
      <p class="job-card__detail"><strong>Model track:</strong> ${escapeHtml(job.model)}</p>
      <div class="job-card__metrics">
        ${job.metrics.map(renderMetricPill).join("")}
      </div>
      ${renderList("Key notes", job.notes, "note-list")}
      ${renderLinks("Sources", job.sources, "source-list")}
    `;
    grid.append(card);
  });

  section.querySelector(".panel").append(grid);
  return section;
}

function renderResults(results) {
  const section = renderPanelSection(
    "Interim results",
    "Practice scores, LoRA eval signals, and honest bare baselines."
  );
  const grid = document.createElement("div");
  grid.className = "results-grid";

  results.forEach((item) => {
    const card = document.createElement("article");
    card.className = "result-card";
    card.innerHTML = `
      <h3 class="result-card__title">${escapeHtml(item.name)}</h3>
      <div class="result-card__score">${escapeHtml(item.score)}</div>
      <p class="result-card__detail">${escapeHtml(item.detail)}</p>
    `;
    grid.append(card);
  });

  section.querySelector(".panel").append(grid);
  return section;
}

function renderOperationalNotes(items) {
  const section = renderPanelSection(
    "Ops notes",
    "GPU shape, image limits, and cost guardrails worth remembering."
  );
  const grid = document.createElement("div");
  grid.className = "ops-grid";

  items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "ops-card";
    card.innerHTML = `
      <h3 class="ops-card__title">${escapeHtml(item.label)}</h3>
      <p class="ops-card__detail">${escapeHtml(item.value)}</p>
    `;
    grid.append(card);
  });

  section.querySelector(".panel").append(grid);
  return section;
}

function renderRefreshInstructions(refresh) {
  const section = renderPanelSection(
    "How to refresh",
    "Keep the page current by updating a single JSON file and pushing to main."
  );
  const card = document.createElement("article");
  card.className = "refresh-card";
  card.innerHTML = `
    <h3>${escapeHtml(refresh.title)}</h3>
    <p>${escapeHtml(refresh.summary)}</p>
    <ol class="refresh-list">
      ${refresh.steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}
    </ol>
  `;
  section.querySelector(".panel").append(card);
  return section;
}

function renderSources(sources) {
  const section = renderPanelSection(
    "Source files",
    "Everything on this page is grounded in tracked repo notes, not hidden dashboards."
  );
  const grid = document.createElement("div");
  grid.className = "results-grid";

  sources.forEach((item) => {
    const card = document.createElement("article");
    card.className = "source-card";
    card.innerHTML = `
      <h3 class="source-card__title">${renderSourceTitle(item)}</h3>
      <p class="source-card__detail">${escapeHtml(item.detail)}</p>
    `;
    grid.append(card);
  });

  section.querySelector(".panel").append(grid);
  return section;
}

function renderPanelSection(title, caption) {
  const section = document.createElement("section");
  section.innerHTML = `
    <div class="section-header">
      <div>
        <h2 class="section-title">${escapeHtml(title)}</h2>
        <p class="section-caption">${escapeHtml(caption)}</p>
      </div>
    </div>
    <div class="panel"></div>
  `;
  return section;
}

function renderMetaCard(label, value) {
  const card = document.createElement("div");
  card.className = "meta-card";
  card.innerHTML = `
    <span class="meta-card__label">${escapeHtml(label)}</span>
    <span class="meta-card__value">${escapeHtml(value)}</span>
  `;
  return card;
}

function renderMetricPill(metric) {
  return `
    <div class="metric-pill">
      <span class="metric-pill__label">${escapeHtml(metric.label)}</span>
      <span class="metric-pill__value">${escapeHtml(metric.value)}</span>
    </div>
  `;
}

function renderList(title, items, className) {
  if (!items?.length) {
    return "";
  }

  return `
    <p class="job-card__detail"><strong>${escapeHtml(title)}:</strong></p>
    <ul class="${className}">
      ${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
    </ul>
  `;
}

function renderLinks(title, items, className) {
  if (!items?.length) {
    return "";
  }

  return `
    <p class="job-card__detail"><strong>${escapeHtml(title)}:</strong></p>
    <ul class="${className}">
      ${items
        .map(
          (item) =>
            `<li>${item.href ? `<a href="${escapeAttribute(item.href)}">${escapeHtml(item.label)}</a>` : escapeHtml(item.label)}</li>`
        )
        .join("")}
    </ul>
  `;
}

function renderError(error) {
  const card = document.createElement("section");
  card.className = "loading-card";
  card.innerHTML = `
    <div class="loading-card__spinner" aria-hidden="true"></div>
    <div>
      <p class="loading-card__title">Dashboard data could not be loaded</p>
      <p class="loading-card__detail">${escapeHtml(error.message)}</p>
    </div>
  `;
  return card;
}

function renderSourceTitle(item) {
  if (item.href) {
    return `<a href="${escapeAttribute(item.href)}">${escapeHtml(item.label)}</a>`;
  }

  return escapeHtml(item.label);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}

loadDashboard();
