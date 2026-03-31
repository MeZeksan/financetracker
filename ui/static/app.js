const toast = document.getElementById("toast");

let cachedCategories = [];

function fmtPeriodHuman(ym) {
  if (!ym || typeof ym !== "string") return "—";
  const parts = ym.split("-");
  if (parts.length < 2) return String(ym);
  const y = Number(parts[0]);
  const mo = Number(parts[1]);
  if (!y || !mo) return String(ym);
  const d = new Date(y, mo - 1, 1);
  return d.toLocaleDateString("ru-RU", { month: "long", year: "numeric" });
}

function updateBudgetPeriodSelectFromApi(periods) {
  const sel = document.getElementById("budget-period-filter");
  if (!sel) return;
  const prev = sel.value;
  sel.innerHTML =
    '<option value="__current__">Текущий месяц</option><option value="__all__">Все месяцы</option>';
  (periods || []).forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p;
    opt.textContent = `${fmtPeriodHuman(p)} (${p})`;
    sel.appendChild(opt);
  });
  if ([...sel.options].some((o) => o.value === prev)) {
    sel.value = prev;
  }
}

function budgetsQueryString() {
  const sel = document.getElementById("budget-period-filter");
  const v = sel ? sel.value : "__all__";
  if (v === "__all__") return "?all_periods=true";
  if (v && v !== "__current__") return `?period=${encodeURIComponent(v)}`;
  return "";
}

function renderBudgetsList(data) {
  const list = Array.isArray(data) ? data : data ? [data] : [];
  const sel = document.getElementById("budget-period-filter");
  const mode = sel ? sel.value : "__all__";
  if (!list.length) {
    let msg = "Бюджетов нет.";
    if (mode === "__current__") {
      msg =
        "За текущий календарный месяц бюджетов нет (часто так бывает с демо-данными за прошлые годы). Выберите «Все месяцы» или конкретный месяц в списке.";
    } else if (mode !== "__all__" && mode) {
      msg = "Нет бюджетов за выбранный месяц.";
    }
    panelSet("budgets-output", panelEmpty(msg));
    return;
  }
  const sorted = [...list].sort((a, b) => {
    const pa = a.period || "";
    const pb = b.period || "";
    if (pa !== pb) return pb.localeCompare(pa);
    return String(a.category_name || "").localeCompare(String(b.category_name || ""), "ru");
  });
  const cards = sorted
    .map((b) => {
      const pctRaw = Number(b.percentage_used) || 0;
      const pctBar = Math.min(100, Math.max(0, pctRaw));
      const over = pctRaw > 100;
      return `<div class="budget-card">
        <div class="budget-head">
          <strong>${escapeHtml(b.category_name || "Категория")}</strong>
          <span class="period-badge" title="Период бюджета">${escapeHtml(fmtPeriodHuman(b.period))}<span class="period-ym">${escapeHtml(b.period || "")}</span></span>
        </div>
        <div class="progress-outer" title="${escapeHtml(String(pctRaw))}%">
          <div class="progress-inner ${over ? "over" : pctBar > 85 ? "warn" : ""}" style="width:${Math.min(100, pctBar)}%"></div>
        </div>
        <ul class="kv-list">
          <li><span>Лимит</span><span>${fmtMoney(b.limit_amount)}</span></li>
          <li><span>Потрачено</span><span>${fmtMoney(b.spent_amount)}</span></li>
          <li><span>Осталось</span><span class="${Number(b.remaining_amount) < 0 ? "negative" : ""}">${fmtMoney(b.remaining_amount)}</span></li>
          <li><span>Использовано</span><span>${escapeHtml(String(b.percentage_used))}%</span></li>
        </ul>
        <div class="budget-actions">
          <div class="budget-row">
            <input type="number" class="budget-topup-input" step="0.01" min="0.01" placeholder="Сумма">
            <button type="button" class="btn-budget budget-topup-btn" data-budget-id="${escapeHtml(String(b.id))}">Пополнить лимит</button>
          </div>
          <div class="budget-row">
            <input type="number" class="budget-spend-input" step="0.01" min="0.01" placeholder="Расход">
            <input type="date" class="budget-spend-date" title="В пределах периода бюджета (можно не указывать)">
            <input type="text" class="budget-spend-desc" placeholder="Описание">
            <button type="button" class="btn-budget budget-spend-btn" data-budget-id="${escapeHtml(String(b.id))}">Списать</button>
          </div>
        </div>
      </div>`;
    })
    .join("");
  panelSet("budgets-output", `<div class="budget-grid">${cards}</div>`);
}

async function refreshBudgetPeriodOptions() {
  try {
    const periods = await api("/budgets/periods");
    if (Array.isArray(periods)) {
      updateBudgetPeriodSelectFromApi(periods);
    }
  } catch (e) {
    console.warn("Budget periods list unavailable:", e);
  }
}

async function fetchAndRenderBudgets() {
  const path = `/budgets/status${budgetsQueryString()}`;
  const data = await api(path);
  renderBudgetsList(data);
}

function apiBaseUrl() {
  if (typeof window.__FINANCETRACKER_API_BASE__ === "string" && window.__FINANCETRACKER_API_BASE__.trim()) {
    return window.__FINANCETRACKER_API_BASE__.trim().replace(/\/$/, "");
  }
  const meta = document.querySelector('meta[name="financetracker-api-base"]');
  if (meta && meta.content && meta.content.trim()) {
    return meta.content.trim().replace(/\/$/, "");
  }
  const port = window.location.port;
  const proto = window.location.protocol || "http:";
  const host = window.location.hostname || "127.0.0.1";
  if (port === "8000") {
    return "";
  }
  if (proto === "file:") {
    return "http://127.0.0.1:8000";
  }
  return `${proto}//${host}:8000`;
}

function apiUrl(path) {
  const base = apiBaseUrl();
  if (!path.startsWith("/")) {
    path = `/${path}`;
  }
  return base ? `${base}${path}` : path;
}

function notify(message, isError = false) {
  toast.textContent = message;
  toast.style.display = "block";
  toast.style.background = isError ? "#991b1b" : "#111827";
  setTimeout(() => {
    toast.style.display = "none";
  }, 2500);
}

function escapeHtml(s) {
  if (s == null) return "";
  const t = String(s);
  return t
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtMoney(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 2,
  }).format(Number(n));
}

function fmtDate(s) {
  if (s == null || s === "") return "—";
  const d = String(s).slice(0, 10);
  if (!d) return "—";
  try {
    const [y, m, day] = d.split("-");
    if (y && m && day) return `${day}.${m}.${y}`;
  } catch (_) {}
  return escapeHtml(String(s));
}

function fmtDateTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return escapeHtml(String(iso));
    return d.toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
  } catch (_) {
    return escapeHtml(String(iso));
  }
}

function panelSet(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

function panelEmpty(text) {
  return `<p class="panel-empty">${escapeHtml(text)}</p>`;
}

function syncCategorySelects() {
  const txnType = document.getElementById("transaction-type");
  const type = txnType ? txnType.value : "expense";
  const txnSel = document.getElementById("transaction-category");
  const budgetSel = document.getElementById("budget-category");
  if (!txnSel || !budgetSel) return;

  const forTxn = cachedCategories.filter((c) => c.type === type);
  const forBudget = cachedCategories.filter((c) => c.type === "expense");

  const fill = (select, list, placeholder) => {
    const prev = select.value;
    select.innerHTML = `<option value="">${escapeHtml(placeholder)}</option>`;
    list.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = String(c.id);
      opt.textContent = `${c.name} (№${c.id})`;
      select.appendChild(opt);
    });
    if (prev && [...select.options].some((o) => o.value === prev)) {
      select.value = prev;
    }
  };

  fill(
    txnSel,
    forTxn,
    forTxn.length ? "Выберите категорию" : "Нет категорий этого типа — добавьте или загрузите"
  );
  fill(
    budgetSel,
    forBudget,
    forBudget.length ? "Выберите категорию расхода" : "Нет категорий расхода"
  );
}

function syncGoalContributeSelect(goals) {
  const sel = document.getElementById("goal-contribute-select");
  if (!sel) return;
  const prev = sel.value;
  sel.innerHTML = '<option value="">Выберите цель</option>';
  (goals || []).forEach((g) => {
    const opt = document.createElement("option");
    opt.value = String(g.id);
    opt.textContent = `${g.name} (№${g.id})`;
    sel.appendChild(opt);
  });
  if (prev && [...sel.options].some((o) => o.value === prev)) sel.value = prev;
}

function renderUserProfile(data) {
  if (!data || data.email == null) {
    panelSet("summary-output", panelEmpty("Войдите, чтобы увидеть профиль и сводку."));
    return;
  }
  panelSet(
    "summary-output",
    `<div class="profile-card">
      <div class="profile-avatar">${escapeHtml((data.full_name || "?").slice(0, 1).toUpperCase())}</div>
      <div class="profile-meta">
        <strong>${escapeHtml(data.full_name || "")}</strong>
        <span class="muted">${escapeHtml(data.email)}</span>
        <span class="muted small">ID: ${escapeHtml(String(data.id))}</span>
      </div>
    </div>
    <p class="hint">Нажмите «Обновить сводку», чтобы увидеть цифры по операциям.</p>`
  );
}

function renderSummary(data) {
  if (!data || typeof data !== "object") {
    panelSet("summary-output", panelEmpty("Нет данных."));
    return;
  }
  const bal = Number(data.balance);
  const balClass = bal >= 0 ? "positive" : "negative";
  panelSet(
    "summary-output",
    `<div class="stat-grid">
      <div class="stat-card income">
        <span class="stat-label">Доходы</span>
        <span class="stat-value">${fmtMoney(data.total_income)}</span>
        <span class="stat-sub">${escapeHtml(String(data.income_count ?? 0))} операций</span>
      </div>
      <div class="stat-card expense">
        <span class="stat-label">Расходы</span>
        <span class="stat-value">${fmtMoney(data.total_expense)}</span>
        <span class="stat-sub">${escapeHtml(String(data.expense_count ?? 0))} операций</span>
      </div>
      <div class="stat-card balance ${balClass}">
        <span class="stat-label">Баланс</span>
        <span class="stat-value">${fmtMoney(data.balance)}</span>
        <span class="stat-sub">Всего операций: ${escapeHtml(String(data.total_transactions ?? "—"))}</span>
      </div>
    </div>`
  );
}

function renderCategories(data) {
  const list = Array.isArray(data) ? data : data ? [data] : [];
  if (!list.length) {
    panelSet("categories-output", panelEmpty("Категорий пока нет. Добавьте или загрузите список."));
    return;
  }
  const rows = list
    .map(
      (c) => `<tr>
      <td><span class="badge ${c.type === "income" ? "badge-in" : "badge-out"}">${c.type === "income" ? "Доход" : "Расход"}</span></td>
      <td><strong>${escapeHtml(c.name)}</strong></td>
      <td class="num">№${escapeHtml(String(c.id))}</td>
    </tr>`
    )
    .join("");
  panelSet(
    "categories-output",
    `<div class="table-wrap"><table class="data-table">
      <thead><tr><th>Тип</th><th>Название</th><th>ID</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`
  );
}

function renderTransactions(data) {
  const list = Array.isArray(data) ? data : data ? [data] : [];
  if (!list.length) {
    panelSet("transactions-output", panelEmpty("Транзакций нет."));
    return;
  }
  const rows = list
    .map((t) => {
      const isIn = t.type === "income";
      const sign = isIn ? "+" : "−";
      const amt = fmtMoney(Math.abs(Number(t.amount)));
      return `<tr>
        <td>${fmtDate(t.transaction_date)}</td>
        <td><span class="badge ${isIn ? "badge-in" : "badge-out"}">${isIn ? "Доход" : "Расход"}</span></td>
        <td><strong>${escapeHtml(t.category_name || "—")}</strong></td>
        <td class="num ${isIn ? "amount-in" : "amount-out"}">${sign} ${amt}</td>
        <td class="desc">${escapeHtml(t.description || "—")}</td>
      </tr>`;
    })
    .join("");
  panelSet(
    "transactions-output",
    `<div class="table-wrap"><table class="data-table">
      <thead><tr><th>Дата</th><th>Тип</th><th>Категория</th><th>Сумма</th><th>Описание</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`
  );
}

function renderGoals(data) {
  const list = Array.isArray(data) ? data : data ? [data] : [];
  syncGoalContributeSelect(list);
  if (!list.length) {
    panelSet("goals-output", panelEmpty("Целей нет."));
    return;
  }
  const cards = list
    .map((g) => {
      const pct = Math.min(100, Math.max(0, Number(g.progress_percentage) || 0));
      return `<div class="goal-card">
        <div class="goal-head">
          <strong>${escapeHtml(g.name)}</strong>
          <span class="muted">№${escapeHtml(String(g.id))}</span>
        </div>
        <div class="progress-outer"><div class="progress-inner" style="width:${pct}%"></div></div>
        <ul class="kv-list">
          <li><span>Накоплено</span><span>${fmtMoney(g.current_amount)}</span></li>
          <li><span>Цель</span><span>${fmtMoney(g.target_amount)}</span></li>
          <li><span>Осталось</span><span>${fmtMoney(g.remaining_amount)}</span></li>
          <li><span>Прогресс</span><span>${escapeHtml(String(g.progress_percentage))}%</span></li>
          <li><span>Срок</span><span>${g.target_date ? fmtDate(g.target_date) : "—"}</span></li>
        </ul>
      </div>`;
    })
    .join("");
  panelSet("goals-output", `<div class="goal-grid">${cards}</div>`);
}

function renderForecasts(list) {
  if (!list || !list.length) {
    return panelEmpty("Прогнозов пока нет. Запустите анализ или добавьте транзакции.");
  }
  const rows = list
    .map(
      (f) => `<tr>
      <td>${escapeHtml(f.period)}</td>
      <td class="num">${fmtMoney(f.forecasted_balance)}</td>
      <td class="muted small">${fmtDateTime(f.created_at)}</td>
    </tr>`
    )
    .join("");
  return `<h3 class="subsection-title">Прогноз баланса</h3>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Период</th><th>Прогноз баланса</th><th>Создано</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
}

function renderAnomalies(list) {
  if (!list || !list.length) {
    return panelEmpty("Аномалий не найдено.");
  }
  const rows = list
    .map(
      (a) => `<tr>
      <td class="num">${escapeHtml(String(a.anomaly_score?.toFixed?.(2) ?? a.anomaly_score))}</td>
      <td>${fmtDate(a.transaction_date)}</td>
      <td class="num">${fmtMoney(a.amount)}</td>
      <td>${escapeHtml(a.category_name || "—")}</td>
      <td><span class="badge ${a.transaction_type === "income" ? "badge-in" : "badge-out"}">${a.transaction_type === "income" ? "Доход" : "Расход"}</span></td>
      <td class="desc">${escapeHtml(a.reason || a.description || "—")}</td>
    </tr>`
    )
    .join("");
  return `<h3 class="subsection-title">Подозрительные операции</h3>
    <div class="table-wrap"><table class="data-table">
      <thead><tr><th>Оценка</th><th>Дата</th><th>Сумма</th><th>Категория</th><th>Тип</th><th>Причина / описание</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div>`;
}

function recTypeLabel(t) {
  const m = { INCREASE: "Увеличить лимит", DECREASE: "Уменьшить лимит", CREATE: "Задать лимит" };
  return m[t] || escapeHtml(String(t || "—"));
}

function renderRecommendations(list) {
  if (!list || !list.length) {
    return panelEmpty("Рекомендаций нет. Запустите анализ.");
  }
  const cards = list
    .map((r) => {
      return `<div class="rec-card">
        <div class="rec-head">
          <span class="badge badge-rec">${recTypeLabel(r.recommendation_type)}</span>
          <strong>${escapeHtml(r.category_name || "Категория")}</strong>
        </div>
        <ul class="kv-list">
          <li><span>Текущий лимит</span><span>${r.current_limit != null ? fmtMoney(r.current_limit) : "—"}</span></li>
          <li><span>Предлагаемый</span><span>${r.proposed_limit != null ? fmtMoney(r.proposed_limit) : "—"}</span></li>
        </ul>
        <p class="rec-text">${escapeHtml(r.justification || "")}</p>
      </div>`;
    })
    .join("");
  return `<h3 class="subsection-title">Рекомендации по бюджету</h3><div class="rec-grid">${cards}</div>`;
}

function renderAnalyzeAll(data) {
  if (!data || typeof data !== "object") {
    panelSet("analytics-output", panelEmpty("Нет результата."));
    return;
  }
  const ad = data.anomaly_detection || {};
  const fc = data.forecast || {};
  const rec = data.recommendations || {};
  const anomaliesBlock =
    ad.anomalies && ad.anomalies.length
      ? `<h3 class="subsection-title">Аномалии (${escapeHtml(String(ad.detected))} из ${escapeHtml(String(ad.total_analyzed))})</h3>
         <p class="hint">${escapeHtml(ad.message || "")}</p>
         <div class="table-wrap"><table class="data-table">
         <thead><tr><th>Оценка</th><th>Дата</th><th>Сумма</th><th>Категория</th><th>Тип</th><th>Комментарий</th></tr></thead><tbody>
         ${ad.anomalies
           .map(
             (a) => `<tr>
           <td class="num">${escapeHtml(String(a.anomaly_score))}</td>
           <td>${fmtDate(a.transaction_date)}</td>
           <td class="num">${fmtMoney(a.amount)}</td>
           <td>${escapeHtml(a.category_name)}</td>
           <td>${escapeHtml(a.transaction_type)}</td>
           <td class="desc">${escapeHtml(a.reason || a.description || "—")}</td>
         </tr>`
           )
           .join("")}
         </tbody></table></div>`
      : `<p class="hint">${escapeHtml(ad.message || "Аномалий не найдено.")}</p>`;

  const forecastBlock =
    fc.forecasts && fc.forecasts.length
      ? `<h3 class="subsection-title">Прогноз</h3>
         <p class="hint">${escapeHtml(fc.message || "")}</p>
         <ul class="kv-list flat">
           <li><span>Средний доход / мес</span><span>${fmtMoney(fc.avg_monthly_income)}</span></li>
           <li><span>Средний расход / мес</span><span>${fmtMoney(fc.avg_monthly_expense)}</span></li>
           <li><span>Тренд / мес</span><span>${fmtMoney(fc.monthly_trend)}</span></li>
         </ul>
         <div class="table-wrap"><table class="data-table"><thead><tr><th>Период</th><th>Баланс (прогноз)</th></tr></thead><tbody>
         ${fc.forecasts.map((p) => `<tr><td>${escapeHtml(p.period)}</td><td class="num">${fmtMoney(p.forecasted_balance)}</td></tr>`).join("")}
         </tbody></table></div>`
      : `<p class="hint">${escapeHtml(fc.message || "Прогноз недоступен.")}</p>`;

  const recBlock =
    rec.items && rec.items.length
      ? `<h3 class="subsection-title">Рекомендации (${escapeHtml(String(rec.recommendations_created))})</h3>
         <p class="hint">${escapeHtml(rec.message || "")}</p>
         <div class="rec-grid">${rec.items
           .map(
             (r) => `<div class="rec-card">
           <div class="rec-head"><span class="badge badge-rec">${recTypeLabel(r.recommendation_type)}</span><strong>${escapeHtml(r.category_name)}</strong></div>
           <ul class="kv-list"><li><span>Лимит</span><span>${r.current_limit != null ? fmtMoney(r.current_limit) : "—"} → ${r.proposed_limit != null ? fmtMoney(r.proposed_limit) : "—"}</span></li></ul>
           <p class="rec-text">${escapeHtml(r.justification || "")}</p>
         </div>`
           )
           .join("")}</div>`
      : `<p class="hint">${escapeHtml(rec.message || "Рекомендаций нет.")}</p>`;

  panelSet("analytics-output", `<div class="analyze-section">${anomaliesBlock}</div><div class="analyze-section">${forecastBlock}</div><div class="analyze-section">${recBlock}</div>`);
}

function renderAnalyticsPayload(data) {
  if (data && data.anomaly_detection && data.forecast && data.recommendations) {
    renderAnalyzeAll(data);
    return;
  }
  if (Array.isArray(data) && data.length && data[0].forecasted_balance != null && data[0].period) {
    panelSet("analytics-output", renderForecasts(data));
    return;
  }
  if (Array.isArray(data) && data.length && data[0].transaction_id != null) {
    panelSet("analytics-output", renderAnomalies(data));
    return;
  }
  if (Array.isArray(data) && data.length && data[0].recommendation_type != null) {
    panelSet("analytics-output", renderRecommendations(data));
    return;
  }
  panelSet(
    "analytics-output",
    `<pre class="fallback-json">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`
  );
}

async function api(path, options = {}) {
  const url = apiUrl(path);
  const { headers: optionHeaders, ...fetchRest } = options;
  const headers = {};
  if (options.body != null) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(url, {
    credentials: "include",
    ...fetchRest,
    headers: { ...headers, ...(optionHeaders || {}) },
  });

  let resData = null;
  try {
    resData = await response.json();
  } catch (_) {
    resData = null;
  }

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    if (resData && resData.detail !== undefined && resData.detail !== null) {
      detail = typeof resData.detail === "string" ? resData.detail : JSON.stringify(resData.detail);
    }
    throw new Error(detail);
  }
  return resData;
}

function formToObject(form) {
  const fd = new FormData(form);
  const obj = {};
  for (const [key, value] of fd.entries()) {
    if (value !== "") {
      obj[key] = value;
    }
  }
  return obj;
}

async function loadCurrentUser() {
  const userInfo = document.getElementById("user-info");
  try {
    const me = await api("/auth/me");
    userInfo.textContent = `${me.full_name} (${me.email})`;
    renderUserProfile(me);
  } catch (_) {
    userInfo.textContent = "Не авторизован";
    panelSet("summary-output", panelEmpty("Войдите, чтобы увидеть профиль и сводку."));
  }
}

function bindFormsNoNativeSubmit() {
  document.querySelectorAll("form").forEach((form) => {
    form.setAttribute("action", "javascript:void(0)");
    form.setAttribute("method", "post");
    form.addEventListener(
      "submit",
      (e) => {
        e.preventDefault();
      },
      { capture: true }
    );
  });
}

function init() {
  bindFormsNoNativeSubmit();

  const txnType = document.getElementById("transaction-type");
  if (txnType) {
    txnType.addEventListener("change", () => syncCategorySelects());
  }

  document.getElementById("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const payload = formToObject(e.target);
      const data = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await loadCurrentUser();
      notify("Вход выполнен");
      renderUserProfile(data);
    } catch (err) {
      notify(`Ошибка входа: ${err.message}`, true);
    }
  });

  document.getElementById("register-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const payload = formToObject(e.target);
      const data = await api("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await loadCurrentUser();
      notify("Регистрация выполнена");
      renderUserProfile(data);
    } catch (err) {
      notify(`Ошибка регистрации: ${err.message}`, true);
    }
  });

  document.getElementById("logout-btn").addEventListener("click", async () => {
    try {
      await api("/auth/logout", { method: "POST" });
      await loadCurrentUser();
      notify("Выход выполнен");
    } catch (err) {
      notify(`Ошибка выхода: ${err.message}`, true);
    }
  });

  document.getElementById("refresh-summary-btn").addEventListener("click", async () => {
    try {
      const data = await api("/analytics/summary");
      renderSummary(data);
      notify("Сводка обновлена");
    } catch (err) {
      notify(`Ошибка загрузки сводки: ${err.message}`, true);
    }
  });

  document.getElementById("category-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api("/transactions/categories", {
        method: "POST",
        body: JSON.stringify(formToObject(e.target)),
      });
      notify("Категория добавлена");
      const all = await api("/transactions/categories");
      cachedCategories = all;
      renderCategories(all);
      syncCategorySelects();
    } catch (err) {
      notify(`Ошибка добавления категории: ${err.message}`, true);
    }
  });

  document.getElementById("load-categories-btn").addEventListener("click", async () => {
    try {
      const data = await api("/transactions/categories");
      cachedCategories = data;
      renderCategories(data);
      syncCategorySelects();
      notify("Категории загружены");
    } catch (err) {
      notify(`Ошибка загрузки категорий: ${err.message}`, true);
    }
  });

  document.getElementById("transaction-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const raw = formToObject(e.target);
      raw.amount = Number(raw.amount);
      raw.category_id = Number(raw.category_id);
      const path = raw.type === "income" ? "/transactions/income" : "/transactions/expense";
      await api(path, { method: "POST", body: JSON.stringify(raw) });
      notify("Транзакция добавлена");
      const history = await api("/transactions/history");
      renderTransactions(history);
    } catch (err) {
      notify(`Ошибка добавления транзакции: ${err.message}`, true);
    }
  });

  document.getElementById("load-transactions-btn").addEventListener("click", async () => {
    try {
      const data = await api("/transactions/history");
      renderTransactions(data);
      notify("История загружена");
    } catch (err) {
      notify(`Ошибка загрузки истории: ${err.message}`, true);
    }
  });

  document.getElementById("budget-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const raw = formToObject(e.target);
      raw.category_id = Number(raw.category_id);
      raw.limit_amount = Number(raw.limit_amount);
      await api("/budgets/", { method: "POST", body: JSON.stringify(raw) });
      notify("Бюджет сохранён");
      await refreshBudgetPeriodOptions();
      await fetchAndRenderBudgets();
    } catch (err) {
      notify(`Ошибка создания бюджета: ${err.message}`, true);
    }
  });

  document.getElementById("load-budgets-btn").addEventListener("click", async () => {
    try {
      await refreshBudgetPeriodOptions();
      await fetchAndRenderBudgets();
      notify("Бюджеты загружены");
    } catch (err) {
      notify(`Ошибка загрузки бюджетов: ${err.message}`, true);
    }
  });

  const budgetFilter = document.getElementById("budget-period-filter");
  if (budgetFilter) {
    budgetFilter.addEventListener("change", async () => {
      try {
        await fetchAndRenderBudgets();
      } catch (err) {
        notify(`Ошибка: ${err.message}`, true);
      }
    });
  }

  const budgetsOut = document.getElementById("budgets-output");
  if (budgetsOut) {
    budgetsOut.addEventListener("click", async (e) => {
      const topBtn = e.target.closest(".budget-topup-btn");
      const spendBtn = e.target.closest(".budget-spend-btn");
      const card = e.target.closest(".budget-card");
      if (topBtn && card) {
        e.preventDefault();
        const id = topBtn.getAttribute("data-budget-id");
        const input = card.querySelector(".budget-topup-input");
        const amt = Number(input && input.value);
        if (!input || !amt || amt <= 0 || Number.isNaN(amt)) {
          notify("Укажите сумму пополнения лимита", true);
          return;
        }
        try {
          await api(`/budgets/${id}/top-up`, {
            method: "POST",
            body: JSON.stringify({ amount: amt }),
          });
          input.value = "";
          await fetchAndRenderBudgets();
          notify("Лимит увеличен");
        } catch (err) {
          notify(err.message, true);
        }
      }
      if (spendBtn && card) {
        e.preventDefault();
        const id = spendBtn.getAttribute("data-budget-id");
        const amtIn = card.querySelector(".budget-spend-input");
        const amt = Number(amtIn && amtIn.value);
        if (!amtIn || !amt || amt <= 0 || Number.isNaN(amt)) {
          notify("Укажите сумму расхода", true);
          return;
        }
        const descEl = card.querySelector(".budget-spend-desc");
        const dateEl = card.querySelector(".budget-spend-date");
        const payload = { amount: amt };
        const dateVal = dateEl && dateEl.value.trim();
        if (dateVal) payload.transaction_date = dateVal;
        const descVal = descEl && descEl.value.trim();
        if (descVal) payload.description = descVal;
        try {
          await api(`/budgets/${id}/spend`, {
            method: "POST",
            body: JSON.stringify(payload),
          });
          amtIn.value = "";
          if (dateEl) dateEl.value = "";
          if (descEl) descEl.value = "";
          await fetchAndRenderBudgets();
          notify("Расход учтён по бюджету");
        } catch (err) {
          notify(err.message, true);
        }
      }
    });
  }

  document.getElementById("goal-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const raw = formToObject(e.target);
      raw.target_amount = Number(raw.target_amount);
      await api("/goals/", { method: "POST", body: JSON.stringify(raw) });
      notify("Цель создана");
      const goals = await api("/goals/progress");
      renderGoals(goals);
    } catch (err) {
      notify(`Ошибка создания цели: ${err.message}`, true);
    }
  });

  document.getElementById("goal-contribute-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const raw = formToObject(e.target);
      const goalId = Number(raw.goal_id);
      const payload = { amount: Number(raw.amount) };
      await api(`/goals/${goalId}/contribute`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      notify("Цель пополнена");
      const goals = await api("/goals/progress");
      renderGoals(goals);
    } catch (err) {
      notify(`Ошибка пополнения цели: ${err.message}`, true);
    }
  });

  document.getElementById("load-goals-btn").addEventListener("click", async () => {
    try {
      const data = await api("/goals/progress");
      renderGoals(data);
      notify("Цели загружены");
    } catch (err) {
      notify(`Ошибка загрузки целей: ${err.message}`, true);
    }
  });

  document.getElementById("run-analysis-btn").addEventListener("click", async () => {
    try {
      const data = await api("/analytics/analyze", { method: "POST" });
      renderAnalyticsPayload(data);
      notify("AI-анализ выполнен");
    } catch (err) {
      notify(`Ошибка AI-анализа: ${err.message}`, true);
    }
  });

  document.getElementById("load-forecasts-btn").addEventListener("click", async () => {
    try {
      renderAnalyticsPayload(await api("/analytics/forecasts"));
    } catch (err) {
      notify(`Ошибка загрузки прогнозов: ${err.message}`, true);
    }
  });

  document.getElementById("load-anomalies-btn").addEventListener("click", async () => {
    try {
      renderAnalyticsPayload(await api("/analytics/anomalies"));
    } catch (err) {
      notify(`Ошибка загрузки аномалий: ${err.message}`, true);
    }
  });

  document.getElementById("load-recommendations-btn").addEventListener("click", async () => {
    try {
      renderAnalyticsPayload(await api("/analytics/recommendations"));
    } catch (err) {
      notify(`Ошибка загрузки рекомендаций: ${err.message}`, true);
    }
  });

  loadCurrentUser();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
