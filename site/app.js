(() => {
  "use strict";
  const byId = id => document.getElementById(id);
  const i18n = window.LHC_I18N;
  const isLanguage = value => value === "en" || value === "ru";
  const sourceLanguage = text => /[А-Яа-яЁё]/.test(text) ? "ru" : "en";
  function initialLanguage() {
    const explicit = new URLSearchParams(location.search).get("lang");
    if (isLanguage(explicit)) return explicit;
    try { const saved = localStorage.getItem("lhc-language"); if (isLanguage(saved)) return saved; } catch (_) { /* Storage is optional. */ }
    return (navigator.language || "en").toLowerCase().startsWith("ru") ? "ru" : "en";
  }
  const state = { language: initialLanguage(), mode: "full", step: 0, data: null, error: null };
  const t = (key, values) => i18n.t(key, state.language, values);
  function make(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = String(text);
    return el;
  }
  function externalLink(label, href, className = "") {
    const link = make("a", className, label);
    link.href = href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    return link;
  }
  function currentRoute() { return state.data.story[state.mode]; }
  function showStep(index) {
    if (!state.data) return;
    const steps = currentRoute();
    state.step = (index + steps.length) % steps.length;
    const step = steps[state.step];
    byId("stage-kicker").textContent = t("step", { number: step.number });
    byId("stage-title").textContent = t(step.titleKey);
    byId("stage-description").textContent = t(step.copyKey);
    byId("stage-role").textContent = step.owner;
    // Canonical source is always plain text, preserved in its original language.
    byId("stage-source").textContent = step.sourceExcerpt;
    byId("stage-source").lang = sourceLanguage(step.sourceExcerpt);
    byId("stage-link").href = step.source;
    byId("step-counter").textContent = step.number + " / " + String(steps.length).padStart(2, "0");
    document.querySelectorAll(".journey-stage").forEach((button, i) => {
      button.classList.toggle("is-selected", i === state.step);
      button.setAttribute("aria-pressed", String(i === state.step));
    });
  }
  function showMode(mode, index = 0) {
    if (!state.data || !["full", "quick"].includes(mode)) return;
    state.mode = mode;
    document.querySelectorAll(".mode-tab").forEach(tab => {
      const active = tab.dataset.mode === mode;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    byId("workflow-panel").setAttribute("aria-labelledby", mode + "-tab");
    byId("workflow-note").textContent = t(mode === "full" ? "loop.fullNote" : "loop.quickNote");
    const container = byId("cycle-nodes");
    container.classList.toggle("quick", mode === "quick");
    container.replaceChildren();
    const groups = new Map();
    for (const name of ["plan", "build", "proof"]) {
      const group = make("div", "journey-group");
      group.append(make("h3", "", t("group." + name)));
      groups.set(name, group);
      container.append(group);
    }
    currentRoute().forEach((step, i) => {
      const button = make("button", "journey-stage cycle-node");
      button.type = "button";
      button.dataset.stage = step.id;
      button.setAttribute("aria-label", t("showStage", { number: step.number, title: t(step.titleKey) }));
      button.append(make("span", "stage-number", step.number), make("span", "stage-name", t(step.titleKey)));
      button.addEventListener("click", () => showStep(i));
      groups.get(step.group).append(button);
    });
    showStep(index);
  }
  function countKinds(roles) {
    const pad = value => String(value).padStart(2, "0");
    const counts = { roles: 0, methods: 0, aliases: 0 };
    for (const role of roles) {
      if (role.kind === "role") counts.roles += 1;
      else if (role.kind === "method-reference") counts.methods += 1;
      else if (role.kind === "compatibility-alias") counts.aliases += 1;
    }
    return { roles: pad(counts.roles), methods: pad(counts.methods), aliases: pad(counts.aliases) };
  }
  function renderRoles() {
    const grid = byId("roles-grid");
    const open = new Set(Array.from(grid.querySelectorAll(".role-toggle[aria-expanded='true']"), button => button.dataset.role));
    grid.replaceChildren();
    byId("roles-count").textContent = t("roleCount", countKinds(state.data.roles));
    state.data.roles.forEach((role, index) => {
      const card = make("article", "role-card");
      const top = make("div", "role-top");
      top.append(make("span", "", String(index + 1).padStart(2, "0")), make("span", "", t("role.kind." + role.kind)));
      const title = make("h3", "", role.name);
      title.lang = "en";
      const summary = make("p", "role-summary", role.summary);
      summary.lang = sourceLanguage(role.summary);
      card.append(top, make("div", "role-symbol", role.name[0]), title, summary);
      const expanded = open.has(role.name);
      const toggle = make("button", "role-toggle", t(expanded ? "hideRole" : "readRole"));
      toggle.type = "button";
      toggle.dataset.role = role.name;
      toggle.setAttribute("aria-expanded", String(expanded));
      toggle.setAttribute("aria-controls", "role-details-" + index);
      toggle.append(make("span", "", expanded ? "−" : "+"));
      const details = make("div", "role-details");
      details.id = "role-details-" + index;
      details.hidden = !expanded;
      const original = make("pre", "", role.details);
      original.lang = sourceLanguage(role.details);
      details.append(make("p", "role-origin", t("verbatim")), original,
        externalLink(t("openSource"), role.source));
      toggle.addEventListener("click", () => {
        details.hidden = !details.hidden;
        toggle.setAttribute("aria-expanded", String(!details.hidden));
        toggle.firstChild.textContent = t(details.hidden ? "readRole" : "hideRole");
        toggle.lastChild.textContent = details.hidden ? "+" : "−";
      });
      card.append(toggle, details);
      grid.append(card);
    });
  }
  function renderFooter() {
    byId("built-from-label").textContent = t("builtFrom");
    if (!state.data) {
      byId("commit-sha").textContent = t(state.error ? "unavailable" : "checking");
      byId("commit-date").textContent = t("updatedOnPush");
      return;
    }
    const data = state.data;
    byId("product-version").textContent = data.productVersion;
    byId("commit-sha").textContent = data.shortRevision;
    byId("commit-link").href = data.repository + "/commit/" + data.revision;
    const built = new Date(data.generatedAt);
    byId("commit-date").textContent = Number.isNaN(built.valueOf()) ? t("updatedOnPush") : t("generated", {
      date: built.toLocaleDateString(state.language === "ru" ? "ru-RU" : "en-GB", {
        year: "numeric", month: "short", day: "numeric", timeZone: "UTC"
      })
    });
    document.querySelectorAll(".philosophy-link").forEach(link => { link.href = data.story.philosophySource; });
    document.querySelectorAll(".gaps-link").forEach(link => { link.href = data.story.gapsSource; });
  }
  function renderError() {
    byId("roles-count").textContent = t("unavailable");
    const message = t("loadError", { reason: t(state.error) });
    byId("roles-grid").replaceChildren(make("p", "role-error", message));
    byId("cycle-nodes").replaceChildren(make("p", "role-error", message));
    byId("workflow-note").textContent = t("staleWarning");
    byId("stage-source").textContent = t("sourceError");
    byId("stage-source").lang = state.language;
    byId("stage-kicker").textContent = t("unavailable");
    document.querySelectorAll(".mode-tab, #prev-step, #next-step").forEach(button => { button.disabled = true; });
  }
  function selectLanguage(language, persist = false) {
    if (!isLanguage(language)) return;
    state.language = language;
    i18n.apply(language);
    if (persist) {
      try { localStorage.setItem("lhc-language", language); } catch (_) { /* No persistent storage required. */ }
      try { const url = new URL(location.href); url.searchParams.set("lang", language); history.replaceState(history.state, "", url); } catch (_) { /* Embedded previews may disallow history. */ }
    }
    renderFooter();
    if (state.data) { renderRoles(); showMode(state.mode, state.step); }
    else if (state.error) renderError();
  }
  function prepareControls() {
    const tabs = Array.from(document.querySelectorAll(".mode-tab"));
    tabs.forEach((tab, index) => {
      tab.addEventListener("click", () => showMode(tab.dataset.mode));
      tab.addEventListener("keydown", event => {
        const next = event.key === "ArrowRight" ? (index + 1) % tabs.length :
          event.key === "ArrowLeft" ? (index - 1 + tabs.length) % tabs.length :
          event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : null;
        if (next === null) return;
        event.preventDefault(); tabs[next].focus(); showMode(tabs[next].dataset.mode);
      });
    });
    byId("prev-step").addEventListener("click", () => showStep(state.step - 1));
    byId("next-step").addEventListener("click", () => showStep(state.step + 1));
    document.querySelectorAll("[data-lang]").forEach(button => {
      button.addEventListener("click", () => selectLanguage(button.dataset.lang, true));
    });
  }
  function validSnapshot(data) {
    if (!data || data.schemaVersion !== 4 || !data.story || data.story.version !== 1 || !Array.isArray(data.roles) || !data.roles.length) return false;
    if (!["revision", "shortRevision", "productVersion", "repository", "generatedAt"].every(key => typeof data[key] === "string" && data[key])) return false;
    const prefix = data.repository + "/blob/" + data.revision + "/";
    if (!["full", "quick"].every(mode => Array.isArray(data.story[mode]) && data.story[mode].length && data.story[mode].every(step =>
      step && ["id", "number", "owner", "titleKey", "copyKey", "sourceExcerpt", "source"].every(key => typeof step[key] === "string" && step[key]) &&
      ["plan", "build", "proof"].includes(step.group) && i18n.messages[step.titleKey] && i18n.messages[step.copyKey] && step.source.startsWith(prefix)))) return false;
    return data.roles.every(role => role && ["name", "summary", "details", "source", "kind"].every(key => typeof role[key] === "string" && role[key]) &&
      role.source.startsWith(prefix) && ["role", "method-reference", "compatibility-alias"].includes(role.kind));
  }
  async function initialize() {
    prepareControls(); selectLanguage(state.language);
    try {
      const response = await fetch("./data.json", { cache: "no-store" });
      if (!response.ok) throw new Error("fetchFailed");
      const data = await response.json();
      if (!validSnapshot(data)) throw new Error("fetchInvalid");
      state.data = data;
      selectLanguage(state.language);
    } catch (error) {
      state.error = error && error.message === "fetchInvalid" ? "fetchInvalid" : "fetchFailed";
      selectLanguage(state.language);
    }
  }
  initialize();
})();
