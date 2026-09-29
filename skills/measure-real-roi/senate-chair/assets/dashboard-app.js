"use strict";

const boardRoot = document.getElementById("board-root");
const boardMessage = document.getElementById("board-message");
let state = {
  cases: [],
  statuses: [],
  topics: [],
  generated: ""
};

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

function setMessage(message, kind = "success") {
  boardMessage.textContent = message;
  boardMessage.className = `board-message ${kind}`;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store"
    },
    ...options
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `Request failed (${response.status})`);
  }
  return payload;
}

async function loadBoard() {
  try {
    state = await fetchJson("/api/bootstrap");
    renderBoard();
    setMessage("");
  } catch (error) {
    setMessage(error.message, "danger");
  }
}

function topicOptions(selectedTopic) {
  return state.topics
    .map(topic => {
      const selected = topic === selectedTopic ? " selected" : "";
      return `<option value="${escapeHtml(topic)}"${selected}>${escapeHtml(topic)}</option>`;
    })
    .join("");
}

function statusOptions(selectedStatus) {
  return state.statuses
    .map(status => {
      const selected = status === selectedStatus ? " selected" : "";
      return `<option value="${escapeHtml(status)}"${selected}>${escapeHtml(status)}</option>`;
    })
    .join("");
}

function caseBadges(caseData) {
  const badges = [];
  if (caseData.review_flag) {
    badges.push(`<span class="badge review">Review: ${escapeHtml(caseData.review_flag)}</span>`);
  }
  if (caseData.confidential) {
    badges.push('<span class="badge confidential">Confidential</span>');
  }
  if (caseData.status === "Pending" && caseData.pending_unit) {
    badges.push(`<span class="badge pending">Waiting on ${escapeHtml(caseData.pending_unit)}</span>`);
  }
  return badges.length ? `<div class="case-badges">${badges.join("")}</div>` : "";
}

function renderCard(caseData) {
  const article = document.createElement("article");
  article.className = "panel panel-default case-card";
  article.dataset.caseId = caseData.id;

  article.innerHTML = `
    <div class="panel-heading">
      <div class="case-heading">
        <span class="drag-handle" draggable="true" title="Drag to another stage" aria-hidden="true">⋮⋮</span>
        <h3 class="panel-title">${escapeHtml(caseData.id)}</h3>
      </div>
    </div>
    <div class="panel-body">
      <form class="case-form" data-case-id="${escapeHtml(caseData.id)}">
        <label>
          <span>Title</span>
          <input class="form-control" name="title" value="${escapeHtml(caseData.title)}" required>
        </label>
        <label>
          <span>Topic</span>
          <select class="form-control" name="topic">${topicOptions(caseData.topic)}</select>
        </label>
        <label>
          <span>Owner</span>
          <input class="form-control" name="owner" value="${escapeHtml(caseData.owner)}">
        </label>
        <label>
          <span>Next action</span>
          <input class="form-control" name="next_action" value="${escapeHtml(caseData.next_action)}">
        </label>
        <label>
          <span>Status</span>
          <select class="form-control" name="status">${statusOptions(caseData.status)}</select>
        </label>
        <label class="pending-field ${caseData.status === "Pending" ? "" : "hidden"}">
          <span>Pending unit</span>
          <input class="form-control" name="pending_unit" value="${escapeHtml(caseData.pending_unit)}">
        </label>
        <div class="case-meta">
          <span><strong>Next deadline:</strong> ${escapeHtml(caseData.next_deadline || "None")}</span>
          <span><strong>Updated:</strong> ${escapeHtml(caseData.updated || "Unknown")}</span>
        </div>
        ${caseBadges(caseData)}
        <div class="case-actions">
          <button type="submit" class="btn btn-primary btn-sm">Save</button>
        </div>
      </form>
    </div>
  `;

  const form = article.querySelector("form");
  const statusSelect = form.elements.status;
  const pendingField = form.querySelector(".pending-field");
  statusSelect.addEventListener("change", () => {
    pendingField.classList.toggle("hidden", statusSelect.value !== "Pending");
  });

  form.addEventListener("submit", async event => {
    event.preventDefault();
    const changes = {
      title: form.elements.title.value,
      topic: form.elements.topic.value,
      owner: form.elements.owner.value,
      next_action: form.elements.next_action.value,
      status: form.elements.status.value,
      pending_unit: form.elements.pending_unit.value
    };
    await saveCase(caseData.id, changes);
  });

  const dragHandle = article.querySelector(".drag-handle");
  dragHandle.addEventListener("dragstart", event => {
    event.dataTransfer.setData("text/plain", caseData.id);
    event.dataTransfer.effectAllowed = "move";
  });

  return article;
}

function renderColumn(status) {
  const section = document.createElement("section");
  section.className = "col-xs-12 col-sm-6 col-md-3 board-column";
  section.dataset.status = status;

  const cases = state.cases.filter(caseData => caseData.status === status);
  section.innerHTML = `
    <h2>${escapeHtml(status)} <span class="badge count">${cases.length}</span></h2>
    <div class="column-cards"></div>
  `;

  const cardContainer = section.querySelector(".column-cards");
  cases.forEach(caseData => cardContainer.append(renderCard(caseData)));
  if (!cases.length) {
    const empty = document.createElement("p");
    empty.className = "empty-column";
    empty.textContent = "Nothing here.";
    cardContainer.append(empty);
  }

  section.addEventListener("dragover", event => {
    event.preventDefault();
    section.classList.add("drop-target");
  });
  section.addEventListener("dragleave", () => section.classList.remove("drop-target"));
  section.addEventListener("drop", async event => {
    event.preventDefault();
    section.classList.remove("drop-target");
    const caseId = event.dataTransfer.getData("text/plain");
    if (caseId) {
      await moveCase(caseId, status);
    }
  });

  return section;
}

function renderBoard() {
  boardRoot.innerHTML = "";
  state.statuses.forEach(status => boardRoot.append(renderColumn(status)));
}

async function saveCase(caseId, changes) {
  try {
    await fetchJson(`/api/cases/${encodeURIComponent(caseId)}`, {
      method: "PATCH",
      body: JSON.stringify(changes)
    });
    setMessage("Case saved.");
    await loadBoard();
  } catch (error) {
    setMessage(error.message, "danger");
  }
}

async function moveCase(caseId, status) {
  const caseData = state.cases.find(item => item.id === caseId);
  if (!caseData || caseData.status === status) {
    return;
  }

  const changes = { status };
  if (status === "Pending") {
    const pendingUnit = window.prompt("Which unit is this case waiting on?", caseData.pending_unit || "");
    if (pendingUnit === null) {
      return;
    }
    if (!pendingUnit.trim()) {
      setMessage("Pending cases require a pending unit.", "danger");
      return;
    }
    changes.pending_unit = pendingUnit.trim();
  }

  await saveCase(caseId, changes);
}

loadBoard();
