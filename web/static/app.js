/* ComicLearn Studio SPA */
(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const state = {
    me: null,
    config: { providers: { anthropic: false, gemini: false }, mathpix: false },
    releases: { current: null, releases: [] },
    projects: [],
    activeProjectId: null,
    runs: [],
    activeRunId: null,
    activeRun: null,
    lbScene: null,
    runEventSource: null,
    inputKind: "topic",
    pdfFile: null,
    qaByScene: {},      // scene -> {verdict, score}
    tilesByScene: {},   // scene -> tile element
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

  async function apiUpload(path, formData) {
    const res = await fetch(path, {
      credentials: "same-origin",
      method: "POST",
      body: formData, // browser sets multipart boundary
    });
    let body = null;
    try { body = await res.json(); } catch (_) { /* no body */ }
    if (!res.ok) {
      throw new Error((body && body.error) || `HTTP ${res.status}`);
    }
    return body;
  }

  // ===================================================================== AUTH
  let authMode = "login";

  function setAuthMode(mode) {
    authMode = mode;
    $("#authTitle").textContent = mode === "login" ? "Sign in to ComicLearn Studio"
                                                   : "Create your ComicLearn Studio account";
    $("#authSub").textContent = mode === "login"
      ? "Build full 6-page comic book lessons from any topic, outline, or textbook PDF."
      : "Free during the research preview. No credit card.";
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
    const access_code = $("#suCode").value.trim();
    $("#authErr").textContent = "";
    try {
      const body = authMode === "login"
        ? { email, password }
        : { email, password, display_name, access_code };
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
    await loadConfig();
    await refreshProjects();
  }

  // ================================================================ CONFIG
  async function loadConfig() {
    const [config, releases] = await Promise.all([
      api("/api/config").catch(() => null),
      api("/api/releases").catch(() => null),
    ]);
    if (config) state.config = config;
    if (releases) state.releases = releases;
    applyConfig();
  }

  function applyConfig() {
    const p = state.config.providers || {};
    const provSel = $("#genProvider");
    // Annotate availability so the teacher knows which keys are configured.
    $$("option", provSel).forEach(opt => {
      if (opt.value === "anthropic") {
        opt.textContent = "Claude (Anthropic)" + (p.anthropic ? "" : " — no key");
        opt.disabled = !p.anthropic;
      }
      if (opt.value === "gemini") {
        opt.textContent = "Gemini" + (p.gemini ? "" : " — no key");
        opt.disabled = !p.gemini;
      }
    });
    const backendSel = $("#genBackend");
    $$("option", backendSel).forEach(opt => {
      if (opt.value === "gemini" && !p.gemini) {
        opt.textContent = "Nano Banana Pro (Gemini) — no key";
      }
    });
    if (!p.gemini) backendSel.value = "svg";

    $("#ocrHint").textContent = state.config.mathpix
      ? "✓ Mathpix OCR is configured — math formulas extract as clean LaTeX."
      : "Tip: set MATHPIX_APP_ID / MATHPIX_APP_KEY in .env for LaTeX-accurate math OCR. Falling back to local text extraction.";

    const bits = [];
    bits.push(p.anthropic ? "Claude ✓" : "Claude –");
    bits.push(p.gemini ? "Gemini ✓" : "Gemini –");
    const version = state.releases.current || state.config.app_version;
    if (version) bits.push(`v${version}`);
    $("#footEnv").textContent = bits.join(" · ");
    const latest = (state.releases.releases || [])[0];
    $("#btnReleases").title = latest
      ? `${latest.title || "Latest release"} · ${latest.date || ""}`
      : `Image model: ${state.config.image_model || "n/a"}`;
  }

  function openReleaseModal() {
    renderReleaseHistory();
    $("#releaseModal").classList.add("open");
  }

  function closeReleaseModal() {
    $("#releaseModal").classList.remove("open");
  }

  function renderReleaseHistory() {
    const list = $("#releaseList");
    list.innerHTML = "";
    const releases = state.releases.releases || [];
    if (!releases.length) {
      const empty = document.createElement("p");
      empty.className = "empty-inline";
      empty.textContent = "No release records yet.";
      list.appendChild(empty);
      return;
    }
    releases.forEach(rel => {
      const item = document.createElement("div");
      item.className = "release-item";

      const top = document.createElement("div");
      top.className = "release-top";
      const title = document.createElement("div");
      title.className = "release-title";
      const version = document.createElement("b");
      version.textContent = `v${rel.version || "unknown"}`;
      const name = document.createElement("span");
      name.textContent = rel.title || "";
      title.append(version, name);
      const date = document.createElement("time");
      date.textContent = rel.date || "";
      top.append(title, date);

      const changes = document.createElement("ul");
      (rel.changes || []).forEach(change => {
        const li = document.createElement("li");
        li.textContent = change;
        changes.appendChild(li);
      });

      item.append(top, changes);
      list.appendChild(item);
    });
  }

  $("#btnReleases").addEventListener("click", openReleaseModal);
  $("#releaseClose").addEventListener("click", closeReleaseModal);
  $("#releaseModal").addEventListener("click", e => {
    if (e.target.id === "releaseModal") closeReleaseModal();
  });

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

  // =================================================================== INPUT KIND TABS
  $$(".kind-tabs .tab").forEach(t => {
    t.addEventListener("click", () => {
      $$(".kind-tabs .tab").forEach(x => x.classList.remove("active"));
      t.classList.add("active");
      state.inputKind = t.dataset.kind;
      $("#markdownField").style.display = state.inputKind === "markdown" ? "block" : "none";
      $("#pdfField").style.display = state.inputKind === "pdf" ? "block" : "none";
    });
  });

  // =================================================================== PDF DROPZONE
  const dz = $("#dropzone");
  const fileInput = $("#genPdf");
  dz.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => setPdfFile(fileInput.files[0] || null));
  ["dragover", "dragenter"].forEach(ev =>
    dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.add("over"); }));
  ["dragleave", "drop"].forEach(ev =>
    dz.addEventListener(ev, e => { e.preventDefault(); dz.classList.remove("over"); }));
  dz.addEventListener("drop", e => {
    const f = e.dataTransfer.files && e.dataTransfer.files[0];
    if (f) setPdfFile(f);
  });

  function setPdfFile(f) {
    if (f && !/\.pdf$/i.test(f.name)) {
      $("#genErr").textContent = "Please choose a .pdf file.";
      return;
    }
    state.pdfFile = f;
    $("#dzFile").textContent = f ? `📄 ${f.name} (${(f.size / 1048576).toFixed(1)} MB)` : "";
    dz.classList.toggle("has-file", !!f);
  }

  // =================================================================== GENERATE
  $("#btnGenerate").addEventListener("click", async () => {
    const p = activeProject(); if (!p) return;
    $("#genErr").textContent = "";
    const title = $("#genTitle").value.trim();
    const grade = $("#genGrade").value.trim() || p.grade_level;
    const backend = $("#genBackend").value;
    const provider = $("#genProvider").value;
    const image_quality = $("#genQuality").value;
    const run_qa = $("#genQA").checked;

    if (!title) { $("#genErr").textContent = "Topic / title is required."; return; }

    $("#btnGenerate").disabled = true;
    try {
      let r;
      if (state.inputKind === "pdf") {
        if (!state.pdfFile) {
          $("#genErr").textContent = "Drop or choose a PDF first.";
          return;
        }
        const fd = new FormData();
        fd.append("file", state.pdfFile);
        fd.append("title", title);
        fd.append("grade_level", grade);
        fd.append("pages", $("#genPages").value.trim());
        fd.append("backend", backend);
        fd.append("provider", provider);
        fd.append("image_quality", image_quality);
        fd.append("run_qa", run_qa ? "true" : "false");
        r = await apiUpload(`/api/projects/${p.id}/runs/pdf`, fd);
      } else {
        const body = {
          source_kind: state.inputKind,
          title,
          grade_level: grade,
          backend,
          provider,
          image_quality,
          run_qa,
        };
        if (state.inputKind === "markdown") {
          body.source_text = $("#genMarkdown").value;
          if (!body.source_text.trim()) { $("#genErr").textContent = "Paste a markdown outline."; return; }
        }
        r = await api(`/api/projects/${p.id}/runs`, { method: "POST", body: JSON.stringify(body) });
      }
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
      el.className = "ri" + (run.id === state.activeRunId ? " active" : "");
      const ts = new Date(run.created_at * 1000).toLocaleString();
      el.innerHTML = `<div><div class="t"></div><div class="sm"></div></div>
                      <span class="status-pill ${run.status}"></span>`;
      el.querySelector(".t").textContent = run.title;
      el.querySelector(".sm").textContent =
        `${ts} · ${run.source_kind} · text:${run.provider || "auto"} · img:${run.backend}`;
      el.querySelector(".status-pill").textContent = run.status;
      el.addEventListener("click", () => openRun(run.id));
      list.appendChild(el);
    });
  }

  // =================================================================== RUN VIEW
  async function openRun(runId) {
    state.activeRunId = runId;
    closeStream();
    resetRunPane();
    renderRuns();
    try {
      const r = await api(`/api/runs/${runId}`);
      state.activeRun = r.run;
      r.events.forEach(applyEvent);
      setStatusPill(r.run.status, r.run);
      updateReviseHint();
      if (r.run.status === "running" || r.run.status === "queued") {
        openStream(runId);
      }
    } catch (e) {
      appendLog("error", `Could not load run: ${e.message}`);
    }
  }

  function canRevise() {
    return !!(state.activeRun
      && state.activeRun.status === "done"
      && state.activeRun.backend !== "mock");
  }

  function updateReviseHint() {
    $("#reviseHint").style.display =
      canRevise() && Object.keys(state.tilesByScene).length ? "block" : "none";
  }

  function openStream(runId) {
    const es = new EventSource(`/api/runs/${runId}/stream`);
    state.runEventSource = es;
    ["info","step","warn","error","done","panel","qa","worksheet","heartbeat"].forEach(name => {
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
    $("#worksheetLink").style.display = "none";
    $("#pagebar").style.display = "none";
    $$("#stepper .s").forEach(s => s.classList.remove("active","done","err"));
    $("#runStatus").textContent = "loading…";
    $("#runStatus").className = "status-pill queued";
    state.qaByScene = {};
    state.tilesByScene = {};
  }

  function setStatusPill(status, run) {
    $("#runStatus").textContent = status;
    $("#runStatus").className = `status-pill ${status}`;
    if (run && run.pdf_path && status === "done") {
      const link = $("#pdfLink");
      link.style.display = "inline-flex";
      const rel = run.pdf_path.split("outputs/").pop().replace(/^runs\//, "");
      link.href = `/assets/runs/${rel}`;
    }
    if (run && run.worksheet_path && status === "done") {
      const wl = $("#worksheetLink");
      wl.style.display = "inline-flex";
      const rel = run.worksheet_path.split("outputs/").pop().replace(/^runs\//, "");
      wl.href = `/assets/runs/${rel}`;
      wl.setAttribute("download", "");
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
      $("#pagebar").style.display = "none";
      setStatusPill("error");
    } else if (kind === "worksheet") {
      appendLog("done", `✎ Worksheet ready: ${payload.title || "worksheet.md"}`);
      const wl = $("#worksheetLink");
      wl.style.display = "inline-flex";
      wl.href = `/assets/${payload.path}`;
      wl.setAttribute("download", "");
    } else if (kind === "panel") {
      const re = payload.rerendered ? " (re-rendered after QA)" : "";
      const t = payload.secs ? ` in ${payload.secs}s` : "";
      appendLog("panel", `🖼 Page ${payload.scene}${payload.total ? `/${payload.total}` : ""} drawn${t}${re}`);
      addTile(payload);
      updatePagebar(payload);
    } else if (kind === "qa") {
      state.qaByScene[payload.scene] = payload;
      const icon = payload.verdict === "pass" ? "✓" : payload.verdict === "warn" ? "△" : "✗";
      appendLog(payload.verdict === "fail" ? "warn" : "info",
        `${icon} QA scene ${payload.scene}: ${payload.verdict} · score ${payload.score}` +
        (payload.issues && payload.issues.length ? ` · ${payload.issues[0]}` : ""));
      applyQaBadge(payload.scene);
    } else if (kind === "done") {
      appendLog("done", `✓ ${payload.message || "Done"}`);
      $$("#stepper .s").forEach(s => { s.classList.remove("active"); s.classList.add("done"); });
      $("#pagebar").style.display = "none";
      setStatusPill("done", { pdf_path: payload.pdf_path, worksheet_path: payload.worksheet_path });
      if (state.activeRun) state.activeRun.status = "done";
      updateReviseHint();
    }
  }

  function updatePagebar(payload) {
    if (!payload.total) return;
    const done = Object.keys(state.tilesByScene).length;
    const bar = $("#pagebar");
    bar.style.display = "flex";
    $("#pagebarLabel").textContent = `Pages drawn: ${done}/${payload.total}`;
    $("#pagebarFill").style.width = `${Math.round(done / payload.total * 100)}%`;
    if (done >= payload.total) setTimeout(() => { bar.style.display = "none"; }, 1500);
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
    // Replace existing tile for the same scene (QA re-render case).
    const old = state.tilesByScene[payload.scene];
    if (old) old.remove();

    const tile = document.createElement("div");
    tile.className = "tile";
    const rel = payload.path; // e.g. runs/<run_id>/panels/scene_01.svg
    const url = `/assets/${rel}?t=${Date.now()}`;
    let media;
    if (rel.endsWith(".svg")) {
      media = `<object data="${url}" type="image/svg+xml"></object>`;
    } else {
      media = `<img src="${url}" alt="page ${payload.scene}">`;
    }
    tile.innerHTML =
      `<div class="ph">${media}</div>
       <div class="meta"><b>Page ${payload.scene}</b><span class="cap"></span><span class="qa-badge"></span></div>`;
    tile.querySelector(".cap").textContent = payload.caption || "";
    tile.addEventListener("click", () =>
      openLightbox(url, `Page ${payload.scene} — ${payload.caption || ""}`, payload.scene));
    $("#gallery").appendChild(tile);
    state.tilesByScene[payload.scene] = tile;
    // keep gallery ordered by scene number
    const tiles = Object.entries(state.tilesByScene).sort((a, b) => a[0] - b[0]);
    tiles.forEach(([, t]) => $("#gallery").appendChild(t));
    applyQaBadge(payload.scene);
  }

  function applyQaBadge(scene) {
    const tile = state.tilesByScene[scene];
    const qa = state.qaByScene[scene];
    if (!tile || !qa) return;
    const badge = tile.querySelector(".qa-badge");
    badge.className = `qa-badge ${qa.verdict}`;
    badge.textContent = qa.verdict === "pass" ? `QA ✓ ${qa.score}`
                      : qa.verdict === "warn" ? `QA △ ${qa.score}`
                      : `QA ✗ ${qa.score}`;
    badge.title = (qa.issues || []).join("\n");
  }

  // =================================================================== LIGHTBOX
  function openLightbox(url, caption, scene) {
    const lb = $("#lightbox");
    const body = $("#lbBody");
    body.innerHTML = url.includes(".svg")
      ? `<object data="${url}" type="image/svg+xml"></object>`
      : `<img src="${url}" alt="">`;
    $("#lbCaption").textContent = caption || "";
    state.lbScene = scene || null;
    const showEdit = !!scene && canRevise();
    $("#lbEdit").style.display = showEdit ? "flex" : "none";
    if (showEdit) { $("#lbFeedback").value = ""; $("#lbEditMsg").textContent = ""; }
    lb.classList.add("open");
  }

  $("#lbRevise").addEventListener("click", async () => {
    const feedback = $("#lbFeedback").value.trim();
    const msg = $("#lbEditMsg");
    if (feedback.length < 3) { msg.textContent = "Describe what to change first."; return; }
    if (!state.activeRunId || !state.lbScene) return;
    $("#lbRevise").disabled = true;
    msg.textContent = "Sending to the studio…";
    try {
      await api(`/api/runs/${state.activeRunId}/revise`, {
        method: "POST",
        body: JSON.stringify({ scene: state.lbScene, feedback }),
      });
      $("#lightbox").classList.remove("open");
      if (state.activeRun) state.activeRun.status = "running";
      await openRun(state.activeRunId);   // re-subscribe to watch the revision live
      await refreshRuns();
    } catch (e) {
      msg.textContent = e.message;
    } finally {
      $("#lbRevise").disabled = false;
    }
  });
  $("#lbClose").addEventListener("click", () => $("#lightbox").classList.remove("open"));
  $("#lightbox").addEventListener("click", e => {
    if (e.target.id === "lightbox") $("#lightbox").classList.remove("open");
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") $("#lightbox").classList.remove("open");
    if (e.key === "Escape") closeReleaseModal();
  });

  bootstrap();
})();
