(() => {
  "use strict";
  const byId = (id) => document.getElementById(id);
  const i18n = window.LHC_I18N;
  const validLanguage = (value) => value === "en" || value === "ru";
  function initialLanguage() {
    const requested = new URLSearchParams(location.search).get("lang");
    if (validLanguage(requested)) return requested;
    try {
      const saved = localStorage.getItem("lhc-language");
      if (validLanguage(saved)) return saved;
    } catch (_) { /* Storage may be disabled; the switch still works. */ }
    return (navigator.language || "en").toLowerCase().startsWith("ru") ? "ru" : "en";
  }
  const state = { data: null, mode: "quick", step: 0, language: initialLanguage(), error: null };
  const t = (key, values) => i18n.t(key, state.language, values);
  const coordinates = [{ x: 50, y: 15 }, { x: 84, y: 40 }, { x: 74, y: 80 }, { x: 26, y: 80 }, { x: 16, y: 40 }];
  const sourceLanguage = (text) => /[А-Яа-яЁё]/.test(text) ? "ru" : "en";

  function make(tag, cls, text) {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined) el.textContent = String(text);
    return el;
  }
  function showStep(index) {
    if (!state.data) return;
    const steps = state.data.modes[state.mode].steps;
    state.step = (index + steps.length) % steps.length;
    const step = steps[state.step];
    byId("stage-kicker").textContent = t("step", { number: step.number });
    byId("stage-title").textContent = t(step.title);
    byId("stage-description").textContent = t(step.editorial);
    // Do not translate, render as HTML, or otherwise change canonical Git excerpts.
    byId("stage-source").textContent = step.sourceExcerpt || t("missingExcerpt");
    byId("stage-source").lang = step.sourceExcerpt ? sourceLanguage(step.sourceExcerpt) : state.language;
    byId("stage-link").href = step.source;
    byId("step-counter").textContent = step.number + " / " + String(steps.length).padStart(2, "0");
    document.querySelectorAll(".cycle-node").forEach((node, i) => {
      const selected = i === state.step;
      node.classList.toggle("is-selected", selected);
      node.setAttribute("aria-pressed", String(selected));
    });
  }
  function showMode(mode, index = 0) {
    if (!state.data || !state.data.modes[mode]) return;
    state.mode = mode;
    const info = state.data.modes[mode];
    document.querySelectorAll(".mode-tab").forEach((tab) => {
      const active = tab.dataset.mode === mode;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    byId("workflow-panel").setAttribute("aria-labelledby", mode + "-tab");
    byId("loop-label").textContent = t(mode) + " / " + t(info.tagline).toLocaleUpperCase(state.language);
    byId("loop-status").textContent = "01—" + String(info.steps.length).padStart(2, "0");
    byId("workflow-note").textContent = t(info.note);
    const container = byId("cycle-nodes");
    container.replaceChildren();
    info.steps.forEach((step, i) => {
      const node = make("button", "cycle-node");
      node.type = "button";
      node.style.setProperty("--x", coordinates[i % coordinates.length].x + "%");
      node.style.setProperty("--y", coordinates[i % coordinates.length].y + "%");
      node.setAttribute("aria-label", t("showStage", { number: step.number, title: t(step.title) }));
      node.append(make("span", "cycle-node-number", step.number), make("strong", "cycle-node-label", t(step.title)));
      node.addEventListener("click", () => showStep(i));
      container.append(node);
    });
    showStep(index);
  }
  function renderRoles(roles) {
    const grid = byId("roles-grid");
    const open = new Set(Array.from(grid.querySelectorAll(".role-toggle[aria-expanded='true']"), (button) => button.dataset.role));
    grid.replaceChildren();
    byId("roles-count").textContent = t("roleCount", { count: String(roles.length).padStart(2, "0") });
    roles.forEach((role, i) => {
      const card = make("article", "role-card");
      const top = make("div", "role-top");
      top.append(make("span", "role-num", t("role", { number: String(i + 1).padStart(2, "0") })));
      top.append(make("span", "role-optional", t(role.optional ? "onDemand" : "orchestrator")));
      const title = make("h3", "", role.name);
      title.lang = "en"; // Canonical identifiers (Lead, Adviser, etc.) remain unchanged.
      card.append(top, make("div", "role-monogram", role.name.slice(0, 1)), title);
      card.append(make("p", "role-source-label", t("original")));
      const legacyPrefix = "Optional method reference; the active router decides when to use it. ";
      let summaryText = role.summary;
      if (summaryText.startsWith(legacyPrefix)) {
        summaryText = summaryText.slice(legacyPrefix.length);
        card.append(make("p", "role-reference-note", t("roleNotice")));
      }
      const summary = make("p", "role-summary", summaryText);
      summary.lang = sourceLanguage(summaryText);
      card.append(summary);
      const expanded = open.has(role.name);
      const toggle = make("button", "role-toggle", t(expanded ? "hideRole" : "readRole"));
      toggle.type = "button";
      toggle.dataset.role = role.name;
      toggle.setAttribute("aria-expanded", String(expanded));
      const detailsId = "role-details-" + i;
      toggle.setAttribute("aria-controls", detailsId);
      toggle.append(make("span", "", expanded ? "−" : "+"));
      const details = make("div", "role-details");
      details.id = detailsId;
      details.hidden = !expanded;
      const original = make("pre", "", role.details);
      original.lang = sourceLanguage(role.details);
      details.append(make("p", "role-origin", t("verbatim")), original);
      const source = make("a", "", t("openSource"));
      source.href = role.source;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      details.append(source);
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
    byId("commit-sha").textContent = data.shortRevision;
    byId("commit-link").href = data.repository + "/commit/" + data.revision;
    const built = new Date(data.generatedAt);
    byId("commit-date").textContent = Number.isNaN(built.valueOf()) ? t("updatedOnPush") : t("generated", {
      date: built.toLocaleDateString(state.language === "ru" ? "ru-RU" : "en-GB", {
        year: "numeric", month: "short", day: "numeric", timeZone: "UTC"
      })
    });
  }
  function renderError() {
    const reason = t(state.error.key, state.error.values);
    byId("roles-count").textContent = t("unavailable");
    byId("roles-grid").replaceChildren(make("p", "role-error", t("loadError", { reason })));
    byId("stage-source").textContent = t("sourceError");
    byId("stage-source").lang = state.language;
    byId("workflow-note").textContent = t("staleWarning");
  }
  function selectLanguage(language, persist = false) {
    if (!validLanguage(language)) return;
    state.language = language;
    i18n.apply(language);
    if (persist) {
      try { localStorage.setItem("lhc-language", language); } catch (_) { /* Optional storage. */ }
      try {
        const url = new URL(location.href);
        url.searchParams.set("lang", language);
        history.replaceState(history.state, "", url);
      } catch (_) { /* A sandboxed preview may disable history updates. */ }
    }
    renderFooter();
    if (state.data) {
      renderRoles(state.data.roles);
      showMode(state.mode, state.step);
    } else {
      byId("stage-kicker").textContent = t("step", { number: "01" });
      byId("stage-title").textContent = t("Define the outcome");
      byId("stage-description").textContent = t("Name the real user, before/after difference and a hands-on canary.");
      byId("loop-label").textContent = t("quick") + " / " + t("Smallest useful route").toLocaleUpperCase(language);
      if (state.error) renderError();
      else {
        byId("roles-count").textContent = t("loadingRoles");
        byId("roles-grid").replaceChildren(make("p", "role-loading", t("loadingRoles")));
        byId("stage-source").textContent = t("loadingSource");
        byId("workflow-note").textContent = t("An illustration of the short path through the actual LHC router, not a separately mandated protocol.");
      }
    }
  }
  function prepareControls() {
    const tabs = Array.from(document.querySelectorAll(".mode-tab"));
    tabs.forEach((tab, i) => {
      tab.addEventListener("click", () => showMode(tab.dataset.mode));
      tab.addEventListener("keydown", (event) => {
        let next;
        if (event.key === "ArrowRight") next = (i + 1) % tabs.length;
        else if (event.key === "ArrowLeft") next = (i - 1 + tabs.length) % tabs.length;
        else if (event.key === "Home") next = 0;
        else if (event.key === "End") next = tabs.length - 1;
        else return;
        event.preventDefault();
        tabs[next].focus();
        showMode(tabs[next].dataset.mode);
      });
    });
    byId("prev-step").addEventListener("click", () => showStep(state.step - 1));
    byId("next-step").addEventListener("click", () => showStep(state.step + 1));
    document.querySelectorAll("[data-lang]").forEach((button) => {
      button.addEventListener("click", () => selectLanguage(button.dataset.lang, true));
    });
  }
  async function initialize() {
    prepareControls();
    selectLanguage(state.language);
    try {
      const response = await fetch("./data.json", { cache: "no-store" });
      if (!response.ok) throw { key: "fetchHTTP", values: { status: response.status } };
      const data = await response.json();
      if (!data || !data.modes || !Array.isArray(data.roles) || !data.roles.length ||
          !["quick", "full"].every((mode) => Array.isArray(data.modes[mode]?.steps) && data.modes[mode].steps.length)) {
        throw { key: "fetchInvalid" };
      }
      state.data = data;
      selectLanguage(state.language);
    } catch (error) {
      state.error = error && ["fetchHTTP", "fetchInvalid"].includes(error.key) ? error : { key: "fetchFailed" };
      selectLanguage(state.language);
    }
  }
  initialize();
})();
