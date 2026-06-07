/* AI Comic Book — Studio SPA */
(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const state = {
    me: null,
    projects: [],
    activeProjectId: null,
    runs: [],
    activeRunId: null,
    runEventSource: null,
    inputKind: "topic",
  };

  // ===================================================================== API
  async function api(path, opts = {}) {
    const res = await fetch(path, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    let body = null;
    try { body = await res.json(); } catch (_) { /* no body */ }
    if (!res.ok) {
      const msg = (body && body.error) || `HTTP ${res.status}`;
      const err = new Error(msg);
      err.status = res.status;
      throw err;
    }
    return body;
  }

  // ===================================================================== AUTH
  let authMode = "login";

  function setAuthMode(mode) {
    authMode = mode;
    $("#authTitle").textContent = mode === "login" ? "Sign in to Comic Studio"
                                                   : "Create your Comic Studio account";
    $("#authSub").textContent = mode === "login"
      ? "Build full 6-page comic book lessons from any topic, in one command."
      : "Free during the YC research preview. No credit card.";
    $("#authSubmit").textContent = mode === "login" ? "Sign in" : "Create account";
    $("#signupOnly").style.display = mode === "login" ? "none" : "block";
    $("#toggleHint").textContent  = mode === "login" ? "No account?" : "Already have one?";
    $("#toggleAuth").textContent  = mode === "login" ? "Create one" : "Sign in instead";
    $("#authErr").textContent = "";
  }

  $("#toggleAuth").addEventListener("click", () => setAuthMode(authMode === "login" ? "signup" : "login"));

  $("#authSubmit").addEventListener("click", async () => {
    const email = $("#authEmail").value.trim();
    const password = $("#authPwd").value;
    const display_name = $("#suName").value.trim();
    $("#authErr").textContent = "";
    try {
      const body = authMode === "login"
        ? { email, password }
        : { email, password, display_name };
      const path = authMode === "login" ? "/api/login" : "/api/signup";
      const r = await api(path, { method: "POST", body: JSON.stringify(body) });
      state.me = r.user;
      await enterApp();
    } catch (e) { $("#authErr").textContent = e.message; }
  });

  $("#btnLogout").addEventListener("click", async () => {
    await api("/api/logout", { method: "POST" }).catch(() => {});
    location.reload();
  });

  async function bootstrap() {
    try {
      const r = await api("/api/me");
      state.me = r.user;
      await enterApp();
    } catch (_) {
      $("#auth").style.display = "flex";
      $("#app").style.display = "none";
    }
  }

  async function enterApp() {
    $("#auth").style.display = "none";
    $("#app").style.display = "grid";
    $("#who").textContent = `Signed in as ${state.me.display_name}`;
    await refreshProjects();
  }

  // ================================================================ PROJECTS
  async function refreshProjects() {
    const r = await api("/api/projects");
    state.projects = r.projects || [];
    renderProjects();
    if (!state.activeProjectId && state.projects.length) {
      selectProject(state.projects[0].id);
    } else if (state.activeProjectId) {
      const exists = state.projects.find(p => p.id === state.activeProjectId);
      if (!exists) { state.activeProjectId = null; renderEmptyOrStudio(); }
      else renderStudio();
    } else {
      renderEmptyOrStudio();
    }
  }

  function renderProjects() {
    const lib = $("#lib");
    lib.innerHTML = "";
    state.projects.forEach(p => {
      const el = document.createElement("div");
      el.className = "proj" + (p.id === state.activeProjectId ? " active" : "");
      el.innerHTML = `<div class="pn"></div><div class="pm"></div>`;
      el.querySelector(".pn").textContent = p.name;
      el.querySelector(".pm").textContent = `${p.grade_level} · ${p.run_count || 0} run${p.run_count===1?"":"s"}`;
      el.addEventListener("click", () => selectProject(p.id));
      lib.appendChild(el);
    });
  }

  function renderEmptyOrStudio() {
    const hasActive = !!state.activeProjectId;
    $("#emptyState").style.display = hasActive ? "none" : "block";
    $("#studio").style.display = hasActive ? "block" : "none";
    if (hasActive) renderStudio();
  }

  async function selectProject(id) {
    state.activeProjectId = id;
    state.activeRunId = null;
    closeStream();
    renderProjects();
    renderEmptyOrStudio();
    await refreshRuns();
  }

  function activeProject() {
    return state.projects.find(p => p.id === state.activeProjectId);
  }

  function renderStudio() {
    const p = activeProject(); if (!p) return;
    $("#projName").textContent = p.name;
    $("#projMeta").textContent = `${p.grade_level} · cast: ${(p.cast || []).join(", ") || "—"}`;
    $("#projMeta").className = "status-pill queued";
    $("#genGrade").value = p.grade_level || "AP Calculus AB";
  }

  // ---- project modal
  let modalMode = "new"; let modalProjectId = null;
  function openProjectModal(mode, p) {
    modalMode = mode; modalProjectId = p ? p.id : null;
    $("#projModalTitle").textContent = mode === "new" ? "New project" : "Edit project";
    $("#mProjName").value = p ? p.name : "";
    $("#mProjGrade").value = p ? p.grade_level : "AP Calculus AB";
    $("#mProjSetting").value = (p && p.setting_hint) || "";
    $("#mProjCast").value = (p && p.cast ? p.cast.join(", ") : "Doraemon, Nobita");
    $("#mProjErr").textContent = "";
    $("#projModal").classList.add("open");
  }
  function closeProjectModal() { $("#projModal").classList.remove("open"); }
  $("#btnNewProject").addEventListener("click", () => openProjectModal("new"));
  $("#emptyNew").addEventListener("click", () => openProjectModal("new"));
  $("#btnEditProject").addEventListener("click", () => {
    const p = activeProject(); if (p) openProjectModal("edit", p);
  });
  $("#mProjCancel").addEventListener("click", closeProjectModal);
  $("#projModal").addEventListener("click", e => { if (e.target.id === "projModal") closeProjectModal(); });
  $("#mProjSave").addEventListener("click", async () => {
    const body = {
      name: $("#mProjName").value.trim(),
      grade_level: $("#mProjGrade").value.trim() || "AP Calculus AB",
      setting_hint: $("#mProjSetting").value.trim() || null,
      cast: $("#mProjCast").value.split(",").map(s => s.trim()).filter(Boolean),
    };
    try {
      if (modalMode === "new") {
        const r = await api("/api/projects", { method: "POST", body: JSON.stringify(body) });
        await refreshProjects();
        selectProject(r.project.id);
      } else {
        await api(`/api/projects/${modalProjectId}`, { method: "PATCH", body: JSON.stringify(body) });
        await refreshProjects();
      }
      closeProjectModal();
    } catch (e) { $("#mProjErr").textContent = e.message; }
  });
  $("#btnDeleteProject").addEventListener("click", async () => {
    const p = activeProject(); if (!p) return;
    if (!confirm(`Delete project "${p.name}"? This removes its run history but not the on-disk PDFs.`)) return;
    await api(`/api/projects/${p.id}`, { method: "DELETE" });
    state.activeProjectId = null;
    await refreshProjects();
  });

  // =================================================================== RUNS
  // input-kind tabs
  $$(".kind-tabs .tab").forEach(t => {
    t.addEventListener("click", () => {
      if (t.disabled) return;
      $$(".kind-tabs .tab").forEach(x => x.classList.remove("active"));
      t.classList.add("active");
      state.inputKind = t.dataset.kind;
      $("#markdownField").style.display = state.inputKind === "markdown" ? "block" : "none";
    });
  });

  $("#btnGenerate").addEventListener("click", async () => {
    const p = activeProject(); if (!p) return;
    $("#genErr").textContent = "";
    const body = {
      source_kind: state.inputKind,
      title: $("#genTitle").value.trim(),
      grade_level: $("#genGrade").value.trim() || p.grade_level,
      backend: $("#genBackend").value,
      run_qa: $("#genQA").checked,
    };
    if (!body.title) { $("#genErr").textContent = "Topic / title is required."; return; }
    if (state.inputKind === "markdown") {
      body.source_text = $("#genMarkdown").value;
      if (!body.source_text.trim()) { $("#genErr").textContent = "Paste a markdown outline."; return; }
    }
    $("#btnGenerate").disabled = true;
    try {
      const r = await api(`/api/projects/${p.id}/runs`, { method: "POST", body: JSON.stringify(body) });
      await refreshRuns();
      openRun(r.run.id);
    } catch (e) {
      $("#genErr").textContent = e.message;
    } finally {
      $("#btnGenerate").disabled = false;
    }
  });

  async function refreshRuns() {
    if (!state.activeProjectId) { state.runs = []; renderRuns(); return; }
    const r = await api(`/api/projects/${state.activeProjectId}/runs`);
    state.runs = r.runs || [];
    renderRuns();
  }

  function renderRuns() {
    const list = $("#runs");
    list.innerHTML = "";
    $("#runsEmpty").style.display = state.runs.length ? "none" : "block";
    state.runs.forEach(run => {
      const el = document.createElement("div");
      el.className = "ri";
      const ts = new Date(run.created_at * 1000).toLocaleString();
      el.innerHTML = `<div><div class="t"></div><div class="sm"></div></div>
                      <span class="status-pill ${run.status}"></span>`;
      el.querySelector(".t").textContent = run.title;
      el.querySelector(".sm").textContent = `${ts} · ${run.backend} · ${run.source_kind}`;
      el.querySelector(".status-pill").textContent = run.status;
      el.addEventListener("click", () => openRun(run.id));
      list.appendChild(el);
    });
  }

  async function openRun(runId) {
    state.activeRunId = runId;
    closeStream();
    resetRunPane();
    // initial replay
    try {
      const r = await api(`/api/runs/${runId}`);
      r.events.forEach(applyEvent);
      setStatusPill(r.run.status, r.run);
      if (r.run.status === "running" || r.run.status === "queued") {
        openStream(runId);
      }
    } catch (e) {
      appendLog("error", `Could not load run: ${e.message}`);
    }
  }

  function openStream(runId) {
    const es = new EventSource(`/api/runs/${runId}/stream`);
    state.runEventSource = es;
    ["info","step","warn","error","done","panel","heartbeat"].forEach(name => {
      es.addEventListener(name, ev => {
        let data; try { data = JSON.parse(ev.data); } catch (_) { return; }
        applyEvent(data);
        if (name === "done" || name === "error") { closeStream(); refreshRuns(); }
      });
    });
    es.onerror = () => closeStream();
  }
  function closeStream() {
    if (state.runEventSource) {
      try { state.runEventSource.close(); } catch (_) {}
      state.runEventSource = null;
    }
  }

  function resetRunPane() {
    $("#log").innerHTML = "";
    $("#gallery").innerHTML = "";
    $("#galleryEmpty").style.display = "block";
    $("#pdfLink").style.display = "none";
    $$("#stepper .s").forEach(s => s.classList.remove("active","done","err"));
    $("#runStatus").textContent = "loading…";
    $("#runStatus").className = "status-pill queued";
  }

  function setStatusPill(status, run) {
    $("#runStatus").textContent = status;
    $("#runStatus").className = `status-pill ${status}`;
    if (run && run.pdf_path && status === "done") {
      const link = $("#pdfLink");
      link.style.display = "inline";
      const rel = run.pdf_path.split("outputs/").pop().replace(/^runs\//, "");
      link.href = `/assets/runs/${rel}`;
    }
  }

  function applyEvent(ev) {
    const kind = ev.kind, payload = ev.payload || {};
    if (kind === "heartbeat") return;

    if (kind === "step") {
      $$("#stepper .s").forEach(s => {
        const n = parseInt(s.dataset.step, 10);
        if (n < payload.step) { s.classList.add("done"); s.classList.remove("active"); }
        else if (n === payload.step) { s.classList.add("active"); }
        else s.classList.remove("active","done");
      });
      appendLog("step", `▸ Step ${payload.step}/${payload.total}: ${payload.label}`);
    } else if (kind === "info") {
      appendLog("info", payload.message || "");
    } else if (kind === "warn") {
      appendLog("warn", `⚠ ${payload.message || ""}`);
    } else if (kind === "error") {
      appendLog("error", `✖ ${payload.message || ""}`);
      $$("#stepper .s.active").forEach(s => { s.classList.remove("active"); s.classList.add("err"); });
      setStatusPill("error");
    } else if (kind === "panel") {
      appendLog("panel", `panel: scene ${payload.scene} → ${payload.path}`);
      addTile(payload);
    } else if (kind === "done") {
      appendLog("done", `✓ ${payload.message || "Done"}`);
      $$("#stepper .s").forEach(s => { s.classList.remove("active"); s.classList.add("done"); });
      setStatusPill("done", { pdf_path: payload.pdf_path });
    }
  }

  function appendLog(kind, msg) {
    const log = $("#log");
    const line = document.createElement("div");
    line.className = `l ${kind}`;
    line.textContent = msg;
    log.appendChild(line);
    log.scrollTop = log.scrollHeight;
  }

  function addTile(payload) {
    $("#galleryEmpty").style.display = "none";
    const tile = document.createElement("div");
    tile.className = "tile";
    const rel = payload.path; // e.g. runs/<run_id>/panels/scene_01.svg
    const url = `/assets/${rel}`;
    let media;
    if (rel.endsWith(".svg")) {
      media = `<object data="${url}" type="image/svg+xml"></object>`;
    } else {
      media = `<img src="${url}" alt="scene ${payload.scene}">`;
    }
    tile.innerHTML =
      `<div class="ph">${media}</div>
       <div class="meta"><b>Scene ${payload.scene}</b><span>${payload.caption || ""}</span></div>`;
    $("#gallery").appendChild(tile);
  }

  bootstrap();
})();
