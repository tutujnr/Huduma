/* ── Huduma Global — Main JS ─────────────────────────── */

const EXAMPLES = [
  "Send KES 15,000 to my mother in Kisumu urgently",
  "Verify my land title deed for the plot in Karen",
  "Hire a cleaner for my Westlands apartment this Friday",
  "I need a driver to pick up my father from JKIA tomorrow at 6am",
  "Can a lawyer verify a business agreement for me in Nairobi?",
];

let allTasks = [];

/* ── DOM refs ─────────────────────────── */
const textarea = document.getElementById("requestInput");
const submitBtn = document.getElementById("submitBtn");
const loadingOverlay = document.getElementById("loadingOverlay");
const resultPanel = document.getElementById("resultPanel");
const tasksBody = document.getElementById("tasksBody");
const taskCount = document.getElementById("taskCount");
const statTotal = document.getElementById("statTotal");
const statPending = document.getElementById("statPending");
const statHigh = document.getElementById("statHigh");

/* ── Bootstrap ─────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  buildExamples();
  loadTasks();
});

function buildExamples() {
  const wrap = document.getElementById("examples");
  EXAMPLES.forEach(ex => {
    const chip = document.createElement("span");
    chip.className = "example-chip";
    chip.textContent = ex;
    chip.onclick = () => { textarea.value = ex; textarea.focus(); };
    wrap.appendChild(chip);
  });
}

/* ── Submit request ─────────────────────────── */
submitBtn.addEventListener("click", submitRequest);
textarea.addEventListener("keydown", e => {
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submitRequest();
});

async function submitRequest() {
  const text = textarea.value.trim();
  if (!text) { showToast("Please describe your request first.", "error"); return; }

  setLoading(true);
  resultPanel.classList.remove("visible");

  try {
    const res = await fetch("/api/submit/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request: text }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Server error");

    renderResult(data);
    showToast(`Task ${data.task_code} created successfully ✓`, "success");
    loadTasks();
  } catch (err) {
    showToast("Error: " + err.message, "error");
  } finally {
    setLoading(false);
  }
}

/* ── Render result ─────────────────────────── */
function renderResult(d) {
  document.getElementById("resTaskCode").textContent = d.task_code;
  document.getElementById("resIntent").textContent = formatIntent(d.intent);
  document.getElementById("resTeam").textContent = d.assigned_team + " Team";
  document.getElementById("resRiskScore").textContent = d.risk_score + "/100";
  document.getElementById("resRiskBadge").textContent = d.risk_level;
  document.getElementById("resRiskBadge").className = "risk-badge " + d.risk_level;
  document.getElementById("resStatus").textContent = d.status;

  // Entities
  const entWrap = document.getElementById("resEntities");
  entWrap.innerHTML = "";
  const ents = d.entities || {};
  Object.entries(ents).forEach(([k, v]) => {
    if (!v || v === "null") return;
    const chip = document.createElement("span");
    chip.className = "entity-chip";
    chip.innerHTML = `<span class="ek">${k}:</span><span class="ev">${v}</span>`;
    entWrap.appendChild(chip);
  });

  // Steps
  const stepsWrap = document.getElementById("resSteps");
  stepsWrap.innerHTML = "";
  (d.steps || []).forEach(s => {
    const item = document.createElement("div");
    item.className = "step-item";
    item.innerHTML = `<span class="step-num">${s.number}</span><span class="step-text">${s.description}</span>`;
    stepsWrap.appendChild(item);
  });

  // Messages
  const msgs = d.messages || {};
  window._currentMsgs = msgs;
  switchMsgTab("whatsapp");

  resultPanel.classList.add("visible");
  resultPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function switchMsgTab(tab) {
  document.querySelectorAll(".msg-tab").forEach(t => t.classList.remove("active"));
  document.querySelector(`.msg-tab[data-tab="${tab}"]`).classList.add("active");

  const msgs = window._currentMsgs || {};
  const subjectEl = document.getElementById("msgSubject");
  const bodyEl = document.getElementById("msgBody");

  if (tab === "email") {
    const e = msgs.email || {};
    subjectEl.textContent = e.subject ? "Subject: " + e.subject : "";
    subjectEl.style.display = e.subject ? "block" : "none";
    bodyEl.textContent = e.body || "";
  } else {
    subjectEl.style.display = "none";
    bodyEl.textContent = msgs[tab] || "";
  }
}

/* ── Load dashboard tasks ─────────────────────────── */
async function loadTasks() {
  try {
    const res = await fetch("/api/tasks/");
    const data = await res.json();
    allTasks = data.tasks || [];
    renderTasks(allTasks);
    updateStats(allTasks);
  } catch (e) {
    console.error("Failed to load tasks", e);
  }
}

function updateStats(tasks) {
  statTotal.textContent = tasks.length;
  statPending.textContent = tasks.filter(t => t.status === "Pending").length;
  statHigh.textContent = tasks.filter(t => t.risk_level === "High").length;
  taskCount.textContent = tasks.length;
}

function renderTasks(tasks) {
  if (!tasks.length) {
    tasksBody.innerHTML = `<tr><td colspan="8">
      <div class="empty-state">
        <div class="empty-icon">📋</div>
        <p>No tasks yet — submit a request above to get started.</p>
      </div>
    </td></tr>`;
    return;
  }

  tasksBody.innerHTML = "";
  tasks.forEach(task => {
    const tr = document.createElement("tr");
    tr.id = `row-${task.id}`;
    const statusClass = task.status.replace(" ", "-");
    tr.innerHTML = `
      <td class="code-cell">${task.task_code}</td>
      <td><span class="intent-pill">${formatIntent(task.intent)}</span></td>
      <td>
        <span class="status-badge ${statusClass}">${task.status}</span>
      </td>
      <td>
        <span class="risk-num ${task.risk_level}">${task.risk_score}</span>
        <span style="font-size:0.72rem;color:var(--text3);margin-left:4px;">${task.risk_level}</span>
      </td>
      <td><span class="team-badge">${task.assigned_team}</span></td>
      <td style="color:var(--text2);font-size:0.8rem;">${formatDate(task.created_at)}</td>
      <td>
        <select class="status-select" onchange="updateStatus(${task.id}, this.value)" data-task="${task.id}">
          <option ${task.status === 'Pending' ? 'selected' : ''}>Pending</option>
          <option ${task.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
          <option ${task.status === 'Completed' ? 'selected' : ''}>Completed</option>
        </select>
      </td>
      <td>
        <button class="expand-btn" onclick="toggleExpand(${task.id}, this)">Details</button>
      </td>
    `;
    tasksBody.appendChild(tr);
  });
}

/* ── Expand row ─────────────────────────── */
function toggleExpand(taskId, btn) {
  const existingExp = document.getElementById(`exp-${taskId}`);
  if (existingExp) {
    existingExp.remove();
    btn.textContent = "Details";
    return;
  }

  btn.textContent = "Close";
  const task = allTasks.find(t => t.id === taskId);
  if (!task) return;

  const tr = document.createElement("tr");
  tr.id = `exp-${taskId}`;
  tr.className = "expanded-row";

  const stepsHtml = (task.steps || []).map(s =>
    `<div class="step-item"><span class="step-num">${s.number}</span><span class="step-text">${s.description}</span></div>`
  ).join("");

  const entsHtml = Object.entries(task.entities || {}).filter(([,v]) => v && v !== "null").map(([k,v]) =>
    `<span class="entity-chip"><span class="ek">${k}:</span><span class="ev">${v}</span></span>`
  ).join("");

  const msgs = task.messages || {};
  const wa = msgs.whatsapp ? msgs.whatsapp.body : "—";
  const email = msgs.email ? msgs.email.body : "—";
  const emailSubj = msgs.email ? msgs.email.subject : "";
  const sms = msgs.sms ? msgs.sms.body : "—";

  tr.innerHTML = `<td colspan="8">
    <div class="expanded-content">
      <div>
        <div class="mini-section-title">Request</div>
        <p style="font-size:0.85rem;color:var(--text2);margin-bottom:16px;">${task.original_request}</p>
        <div class="mini-section-title">Extracted Entities</div>
        <div class="entities-grid" style="margin-bottom:16px;">${entsHtml || '<span style="color:var(--text3);font-size:0.82rem;">None extracted</span>'}</div>
        <div class="mini-section-title">Fulfilment Steps</div>
        <div class="steps-list">${stepsHtml}</div>
      </div>
      <div>
        <div class="mini-section-title">Confirmation Messages</div>
        <div style="margin-bottom:8px;">
          <div style="font-size:0.72rem;color:var(--text3);margin-bottom:4px;">📱 WhatsApp</div>
          <div class="msg-content" style="font-size:0.82rem;">${wa}</div>
        </div>
        <div style="margin-bottom:8px;">
          <div style="font-size:0.72rem;color:var(--text3);margin-bottom:4px;">📧 Email${emailSubj ? ' — ' + emailSubj : ''}</div>
          <div class="msg-content" style="font-size:0.82rem;max-height:120px;overflow-y:auto;">${email}</div>
        </div>
        <div>
          <div style="font-size:0.72rem;color:var(--text3);margin-bottom:4px;">💬 SMS</div>
          <div class="msg-content" style="font-size:0.82rem;">${sms}</div>
        </div>
      </div>
    </div>
  </td>`;

  const parentRow = document.getElementById(`row-${taskId}`);
  parentRow.after(tr);
}

/* ── Status update ─────────────────────────── */
async function updateStatus(taskId, newStatus) {
  try {
    const res = await fetch(`/api/tasks/${taskId}/status/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Update failed");

    // Update badge in row
    const row = document.getElementById(`row-${taskId}`);
    if (row) {
      const badge = row.querySelector(".status-badge");
      badge.className = "status-badge " + newStatus.replace(" ", "-");
      badge.textContent = newStatus;
    }

    // Update in allTasks
    const task = allTasks.find(t => t.id === taskId);
    if (task) task.status = newStatus;
    updateStats(allTasks);

    showToast(`Status updated to "${newStatus}"`, "success");
  } catch (err) {
    showToast("Error: " + err.message, "error");
  }
}

/* ── Helpers ─────────────────────────────── */
function setLoading(on) {
  loadingOverlay.classList.toggle("visible", on);
  submitBtn.disabled = on;
  submitBtn.textContent = on ? "Processing…" : "Submit Request";
}

function formatIntent(intent) {
  const map = {
    send_money: "Send Money",
    hire_service: "Hire Service",
    verify_document: "Verify Document",
    get_airport_transfer: "Airport Transfer",
    check_status: "Check Status",
  };
  return map[intent] || intent;
}

function formatDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("en-KE", { day: "numeric", month: "short", year: "numeric" })
    + " " + d.toLocaleTimeString("en-KE", { hour: "2-digit", minute: "2-digit" });
}

let toastTimer;
function showToast(msg, type = "success") {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.className = `toast ${type} show`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 4000);
}
