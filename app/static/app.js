var columnMap = {
  "ATENDIMENTO TRANSPORTADORA": { rowsId: "rows-1", counterId: "counter-1" },
  "ATENDIMENTO NO CLIENTE": { rowsId: "rows-2", counterId: "counter-2" },
  "ATENDIMENTOS DO DIA": { rowsId: "rows-3", counterId: "counter-3" }
};

var refreshSeconds = 30;
var countdownValue = refreshSeconds;
var countdownTimer = null;
var refreshTimer = null;

function getQueryParam(name) {
  var escaped = name.replace(/[\[\]]/g, "\\$&");
  var regex = new RegExp("[?&]" + escaped + "=([^&#]*)");
  var results = regex.exec(window.location.search);
  if (!results || !results[1]) {
    return "";
  }
  return decodeURIComponent(results[1].replace(/\+/g, " "));
}

function resolveTvProfile(value) {
  var normalized = String(value || "").trim().toLowerCase();
  if (!normalized) {
    return "";
  }

  if (normalized === "32" || normalized === "small" || normalized === "tv-32") {
    return "tv-32";
  }
  if (normalized === "43" || normalized === "medium" || normalized === "tv-43") {
    return "tv-43";
  }
  if (normalized === "55" || normalized === "large" || normalized === "tv-55") {
    return "tv-55";
  }

  return "";
}

function detectAutoTvProfile() {
  var width = Math.max(window.innerWidth || 0, (window.screen && window.screen.width) || 0);
  if (width <= 1366) {
    return "tv-32";
  }
  if (width <= 1920) {
    return "tv-43";
  }
  return "tv-55";
}

function applyTvProfile() {
  var body = document.body;
  var queryProfile = resolveTvProfile(getQueryParam("tv") || getQueryParam("perfil"));
  var savedProfile = "";
  var finalProfile = "";

  try {
    savedProfile = resolveTvProfile(window.localStorage.getItem("tvProfile"));
  } catch (error) {
    savedProfile = "";
  }

  finalProfile = queryProfile || savedProfile || detectAutoTvProfile();

  body.className = body.className
    .replace(/\btv-32\b/g, "")
    .replace(/\btv-43\b/g, "")
    .replace(/\btv-55\b/g, "")
    .replace(/\s{2,}/g, " ")
    .trim();

  if (body.className) {
    body.className += " " + finalProfile;
  } else {
    body.className = finalProfile;
  }

  try {
    window.localStorage.setItem("tvProfile", finalProfile);
  } catch (error) {
    // Ignora erro de persistencia em navegadores sem localStorage.
  }
}

function formatDateTime(isoString) {
  if (!isoString) {
    return "--";
  }
  var date = new Date(isoString);
  return date.toLocaleString("pt-BR");
}

function formatCountdown(totalSeconds) {
  var safe = Math.max(0, Number(totalSeconds || 0));
  var mm = String(Math.floor(safe / 60));
  var ss = String(safe % 60);
  mm = mm.length < 2 ? "0" + mm : mm;
  ss = ss.length < 2 ? "0" + ss : ss;
  return mm + ":" + ss;
}

function parseNumericValue(value) {
  if (typeof value === "number") {
    return value;
  }
  if (value == null) {
    return NaN;
  }

  var normalized = String(value).trim().replace(/\./g, "").replace(",", ".");
  var parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : NaN;
}

function computeChamadosCount(rows) {
  if (!rows.length) {
    return 0;
  }

  var hasRecordCountInAllRows = rows.every(function (row) {
    return Object.prototype.hasOwnProperty.call(row, "Record Count");
  });
  if (!hasRecordCountInAllRows) {
    return rows.length;
  }

  var sum = rows.reduce(function (acc, row) {
    var count = parseNumericValue(row["Record Count"]);
    return acc + (Number.isFinite(count) ? count : 0);
  }, 0);

  return sum;
}

function resetColumns() {
  Object.keys(columnMap).forEach(function (key) {
    var rowsId = columnMap[key].rowsId;
    var counterId = columnMap[key].counterId;
    var rowsContainer = document.getElementById(rowsId);
    stopAutoScroll(rowsContainer);
    rowsContainer.innerHTML = "";
    document.getElementById(counterId).textContent = "0 Chamados";
  });
}

function stopAutoScroll(container) {
  if (!container) {
    return;
  }

  if (container.__autoScrollIntervalId) {
    clearInterval(container.__autoScrollIntervalId);
  }

  container.__autoScrollIntervalId = null;
  container.classList.remove("auto-scroll");
  container.scrollTop = 0;
}

// Inicia rolagem suave automática (sobe e desce em loop) para leitura contínua na TV.
function startAutoScroll(container) {
  if (!container) {
    return;
  }

  stopAutoScroll(container);

  var maxScroll = Math.max(0, container.scrollHeight - container.clientHeight);
  if (maxScroll <= 0) {
    return;
  }

  container.classList.add("auto-scroll");

  var state = {
    pauseTicksLeft: 0,
    tickMs: 50,
    shouldResetToTop: false,
    // Velocidade base da rolagem em pixels por segundo.
    speedPxPerSecond: 16
  };

  var stepPx = (state.speedPxPerSecond * state.tickMs) / 1000;
  container.__autoScrollIntervalId = setInterval(function () {
    var liveMaxScroll = Math.max(0, container.scrollHeight - container.clientHeight);
    if (liveMaxScroll <= 0) {
      stopAutoScroll(container);
      return;
    }

    if (state.pauseTicksLeft > 0) {
      state.pauseTicksLeft -= 1;
      return;
    }

    if (state.shouldResetToTop) {
      container.scrollTop = 0;
      state.shouldResetToTop = false;
      return;
    }

    var nextScroll = container.scrollTop + stepPx;
    if (nextScroll >= liveMaxScroll) {
      // Chegou ao final: fixa no último item, pausa e só depois volta ao topo.
      container.scrollTop = liveMaxScroll;
      state.shouldResetToTop = true;
      state.pauseTicksLeft = Math.round(1200 / state.tickMs);
    } else {
      container.scrollTop = nextScroll;
    }
  }, state.tickMs);
}

// Ativa auto-scroll apenas na coluna "ATENDIMENTOS DO DIA" com 6+ chamados e overflow real.
function updateAutoScroll(columnTitle, container, rowCount) {
  if (columnTitle !== "ATENDIMENTOS DO DIA" || rowCount < 5) {
    stopAutoScroll(container);
    return;
  }

  setTimeout(function () {
    var hasOverflow = container.scrollHeight > container.clientHeight;
    if (!hasOverflow) {
      stopAutoScroll(container);
      return;
    }
    startAutoScroll(container);
  }, 120);
}

function normalizeText(value) {
  var text = String(value || "")
    .trim()
    .toLowerCase();

  if (typeof text.normalize === "function") {
    text = text.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  return text;
}

function getFieldValueByCandidates(row, candidates) {
  var keys = Object.keys(row || {});
  for (var i = 0; i < candidates.length; i += 1) {
    var candidate = candidates[i];
    var normalizedCandidate = normalizeText(candidate);
    var matchedKey = null;

    for (var j = 0; j < keys.length; j += 1) {
      if (normalizeText(keys[j]) === normalizedCandidate) {
        matchedKey = keys[j];
        break;
      }
    }

    if (matchedKey && row[matchedKey] != null && String(row[matchedKey]).trim() !== "") {
      return row[matchedKey];
    }
  }
  return "-";
}

function formatPriorityEmoji(value) {
  var normalized = normalizeText(value);
  var result = { element: null, text: "-" };
  if (["alta", "high", "urgent", "urgente"].includes(normalized)) {
    result.text = "Alta";
    return result;
  }
  if (["medio", "médio", "media", "média", "medium", "normal"].includes(normalized)) {
    result.text = "Média";
    return result;
  }
  if (["baixa", "low"].includes(normalized)) {
    result.text = "Baixa";
    return result;
  }
  result.text = value || "-";
  return result;
}

function getRowDisplayFields(columnTitle, row) {
  var sharedSchema = [
    { label: "Nº", candidates: ["Case Number"] },
    { label: "Oportunidade", candidates: ["Nome da oportunidade", "Nome da Oportunidade"] },
    { label: "Data", candidates: ["Data agendada", "Data Agendada"] },
    { label: "Endereço", candidates: ["Endereço", "Endereco", "EndereÃ§o"] },
    { label: "Prioridade", candidates: ["Priority"] }
  ];

  var diaSchema = [
    { label: "Nº", candidates: ["Case Number"] },
    { label: "Tipo", candidates: ["Type"] },
    { label: "Oportunidade", candidates: ["Nome da oportunidade", "Nome da Oportunidade"] },
    { label: "Produtos", candidates: ["Oportunidade Aprovada: Produtos", "Produtos"] },
    { label: "Data", candidates: ["Data agendada", "Data Agendada"] },
    { label: "Prioridade", candidates: ["Priority"] }
  ];

  var schema = columnTitle === "ATENDIMENTOS DO DIA" ? diaSchema : sharedSchema;

  return schema.map(function (field) {
    var rawValue = getFieldValueByCandidates(row, field.candidates);
    // Para prioridade, mostra '-' se vazio
    if (field.label === "Prioridade") {
      var val = (rawValue != null && String(rawValue).trim() !== "") ? rawValue : "-";
      return { key: field.label, value: val };
    }
    return { key: field.label, value: rawValue != null ? rawValue : "-" };
  });
}

function renderRows(columnTitle, rows) {
  var mapping = columnMap[columnTitle];
  if (!mapping) return;

  var container = document.getElementById(mapping.rowsId);
  var counter = document.getElementById(mapping.counterId);

  var chamadosCount = computeChamadosCount(rows);
  counter.textContent = chamadosCount + " Chamados";

  if (!rows.length || chamadosCount < 1) {
    stopAutoScroll(container);
    container.innerHTML = "";
    return;
  }

  var fragment = document.createDocumentFragment();
  rows.forEach(function (row) {
    var item = document.createElement("article");
    item.className = "row-item";

    var displayFields = getRowDisplayFields(columnTitle, row);
    var preferredTopOrder = ["Nº", "Oportunidade", "Prioridade"];
    var fieldsByKey = {};
    var idx;
    for (idx = 0; idx < displayFields.length; idx += 1) {
      fieldsByKey[displayFields[idx].key] = displayFields[idx].value;
    }

    var topFields = [];
    for (idx = 0; idx < preferredTopOrder.length; idx += 1) {
      var key = preferredTopOrder[idx];
      if (Object.prototype.hasOwnProperty.call(fieldsByKey, key)) {
        topFields.push({ key: key, value: fieldsByKey[key] });
      }
    }

    if (topFields.length) {
      var topLine = document.createElement("div");
      topLine.className = "row-line row-line-top";

      topFields.forEach(function (entry) {
        var group = document.createElement("span");
        group.className = "row-inline-field";

        var keySpan = document.createElement("span");
        keySpan.className = "row-key";
        keySpan.textContent = entry.key + ":";

        var valueSpan = document.createElement("span");
          if (entry.key === "Prioridade") {
            var priority = entry.value;
            valueSpan.textContent = priority && priority.text ? priority.text : (priority || "-");
          } else {
            valueSpan.textContent = entry.value != null ? entry.value : "";
          }

        group.appendChild(keySpan);
        group.appendChild(valueSpan);
        topLine.appendChild(group);
      });

      item.appendChild(topLine);
    }

    displayFields
      .filter(function (field) { return preferredTopOrder.indexOf(field.key) === -1; })
      .forEach(function (field) {
      var line = document.createElement("div");
      line.className = "row-line";
      var keySpan = document.createElement("span");
      keySpan.className = "row-key";
      keySpan.textContent = field.key + ":";

      var valueSpan = document.createElement("span");
      valueSpan.textContent = field.value != null ? field.value : "";

      line.appendChild(keySpan);
      line.appendChild(valueSpan);
      item.appendChild(line);
    });

    fragment.appendChild(item);
  });

  container.innerHTML = "";
  container.appendChild(fragment);
  updateAutoScroll(columnTitle, container, rows.length);
}

function setApiErrors(errors) {
  var el = document.getElementById("apiErrors");
  if (!el) {
    return;
  }
  if (!errors || !errors.length) {
    el.textContent = "";
    return;
  }
  el.textContent = errors.map(function (e) {
    return "[" + e.title + "] " + e.error;
  }).join(" | ");
}

function setSalesforceStatus(payload) {
  var statusEl = document.getElementById("sfStatus");
  if (!statusEl) {
    return;
  }
  statusEl.classList.remove("status-error");
  statusEl.classList.remove("status-warning");

  if (payload.salesforceStatus === "unavailable") {
    statusEl.classList.add("status-error");
    statusEl.textContent = payload.message || "Salesforce indisponivel";
    return;
  }

  if (payload.salesforceStatus === "degraded") {
    statusEl.classList.add("status-warning");
    statusEl.textContent = payload.message || payload.error || "Salesforce com falhas parciais";
    return;
  }

  statusEl.textContent = "Salesforce online";
}

function setLastUpdate(value) {
  var lastEl = document.getElementById("lastUpdate");
  if (!lastEl) {
    return;
  }
  lastEl.textContent = "Ultima atualizacao: " + (value || "--");
}

function requestDashboard(onSuccess, onError) {
  if (window.fetch) {
    window.fetch("/api/dashboard", { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("Falha HTTP " + response.status);
        }
        return response.json();
      })
      .then(onSuccess)
      .catch(onError);
    return;
  }

  var xhr = new XMLHttpRequest();
  xhr.open("GET", "/api/dashboard", true);
  xhr.setRequestHeader("Cache-Control", "no-cache");
  xhr.onreadystatechange = function () {
    if (xhr.readyState !== 4) {
      return;
    }
    if (xhr.status < 200 || xhr.status >= 300) {
      onError(new Error("Falha HTTP " + xhr.status));
      return;
    }
    try {
      onSuccess(JSON.parse(xhr.responseText));
    } catch (err) {
      onError(new Error("Resposta JSON invalida"));
    }
  };
  xhr.onerror = function () {
    onError(new Error("Erro de rede"));
  };
  xhr.send();
}

function fetchDashboard(done) {
  requestDashboard(function (payload) {
    var columns;

    refreshSeconds = payload.refreshSeconds || payload.refresh_seconds || refreshSeconds;
    countdownValue = refreshSeconds;

    resetColumns();
    columns = payload.columns || [
      { title: "ATENDIMENTO TRANSPORTADORA", rows: payload.transportadora || [] },
      { title: "ATENDIMENTO NO CLIENTE", rows: payload.cliente || [] },
      { title: "ATENDIMENTOS DO DIA", rows: payload.dia || [] }
    ];

    columns.forEach(function (column) {
      renderRows(column.title, column.rows || []);
    });

    setLastUpdate(formatDateTime(payload.generatedAt) || payload.last_update || "--");
    setSalesforceStatus(payload);
    setApiErrors(payload.errors || []);

    if (typeof done === "function") {
      done();
    }
  }, function (error) {
    var statusEl = document.getElementById("sfStatus");
    var apiErrorsEl = document.getElementById("apiErrors");

    if (statusEl) {
      statusEl.classList.add("status-error");
      statusEl.textContent = "Falha na comunicacao com o backend";
    }
    if (apiErrorsEl) {
      apiErrorsEl.textContent = "Erro de atualizacao: " + (error && error.message ? error.message : "desconhecido");
    }
    if (typeof done === "function") {
      done();
    }
  });
}

function startCountdown() {
  var countdownEl = document.getElementById("countdown");
  if (!countdownEl) {
    return;
  }

  if (countdownTimer) {
    clearInterval(countdownTimer);
  }

  countdownTimer = setInterval(function () {
    countdownValue -= 1;
    if (countdownValue < 0) {
      countdownValue = 0;
    }
    countdownEl.textContent = "Proxima atualizacao: " + formatCountdown(countdownValue);
  }, 1000);
}

function init() {
  applyTvProfile();

  fetchDashboard(function () {
    startCountdown();

    var refreshLoop = function () {
      fetchDashboard(function () {
        refreshTimer = setTimeout(refreshLoop, refreshSeconds * 1000);
      });
    };

    if (refreshTimer) {
      clearTimeout(refreshTimer);
    }
    refreshTimer = setTimeout(refreshLoop, refreshSeconds * 1000);
  });
}

init();
