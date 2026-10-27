(() => {
  "use strict";

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function button(label, action, primary = false) {
    const node = element("button", primary ? "is-primary" : "", label);
    node.type = "button";
    node.dataset.action = action;
    return node;
  }

  class StateForgeProcedurePlayer extends HTMLElement {
    connectedCallback() {
      if (this.dataset.initialized === "true") return;
      const source = this.querySelector(".sf-procedure-data");
      if (!source) return;
      try {
        this.declaration = JSON.parse(source.textContent || "");
      } catch (error) {
        console.error("StateForge procedure declaration is invalid", error);
        return;
      }
      this.scenario = this.declaration.default_scenario;
      this.stepIndex = 0;
      this.timer = null;
      this.dataset.initialized = "true";
      this.build(source);
      this.render();
    }

    disconnectedCallback() {
      this.stop();
    }

    build(source) {
      const fallback = this.querySelector(".sf-procedure-fallback");
      if (fallback) fallback.remove();

      this.player = element("section", "sf-procedure");
      this.player.setAttribute(
        "aria-label",
        `${this.declaration.title} interactive procedure`,
      );
      this.player.style.setProperty(
        "--sf-entity-count",
        String(this.declaration.entities.length),
      );

      const scenarioLabel = element(
        "label",
        "sf-procedure__scenario-label",
        "Scenario",
      );
      this.scenarioSelect = element("select");
      this.scenarioSelect.setAttribute("aria-label", "Procedure scenario");
      for (const [id, scenario] of Object.entries(this.declaration.scenarios)) {
        const option = element("option", "", scenario.label);
        option.value = id;
        this.scenarioSelect.append(option);
      }
      this.scenarioSelect.addEventListener("change", () => {
        this.stop();
        this.scenario = this.scenarioSelect.value;
        this.stepIndex = 0;
        this.render();
      });
      scenarioLabel.append(this.scenarioSelect);
      scenarioLabel.hidden = Object.keys(this.declaration.scenarios).length < 2;

      this.topologyScroll = element("div", "sf-procedure__topology-scroll");
      this.topology = element("div", "sf-procedure__topology");
      this.laneGrid = element("div", "sf-procedure__lane-grid");
      this.lanes = new Map();
      this.entityCards = new Map();
      this.activityPanels = new Map();
      for (const entity of this.declaration.entities) {
        const lane = element("section", "sf-procedure__lane");
        lane.dataset.entity = entity.id;
        const card = element("div", "sf-procedure__entity");
        card.dataset.entity = entity.id;
        if (entity.role) card.title = entity.role;
        card.append(
          element("span", "sf-procedure__entity-kind", entity.kind),
          element("strong", "", entity.label),
        );
        const panel = element("div", "sf-procedure__activity");
        panel.dataset.entity = entity.id;
        panel.append(element("strong"), element("ul"));
        lane.append(card, panel);
        this.lanes.set(entity.id, lane);
        this.entityCards.set(entity.id, card);
        this.activityPanels.set(entity.id, panel);
        this.laneGrid.append(lane);
      }

      this.phase = element("div", "sf-procedure__phase");
      this.phase.append(
        element("span", "sf-procedure__phase-label", "Phase"),
        element("strong"),
      );

      this.flowGrid = element("div", "sf-procedure__flow-grid");
      this.flowGrid.setAttribute("aria-label", "Current procedure transitions");

      this.context = element("div", "sf-procedure__context");
      this.contextKind = element("span", "sf-procedure__context-kind");
      this.contextValue = element("code");
      this.context.append(this.contextKind, this.contextValue);

      this.topology.append(this.laneGrid, this.flowGrid);
      this.topologyScroll.append(this.topology);

      this.detail = element("div", "sf-procedure__detail");
      this.detail.setAttribute("aria-live", "polite");
      const detailCopy = element("div");
      this.stepCount = element("span", "sf-procedure__step-count");
      this.stepTitle = element("h3");
      this.stepDetail = element("p");
      detailCopy.append(this.stepCount, this.stepTitle, this.stepDetail);
      this.fields = element("div", "sf-procedure__fields");
      this.detail.append(detailCopy, this.fields);

      this.progress = element("div", "sf-procedure__progress");
      this.progress.setAttribute("role", "progressbar");
      this.progress.setAttribute("aria-label", "Procedure progress");
      this.progress.setAttribute("aria-valuemin", "1");
      this.progressBar = element("div", "sf-procedure__progress-bar");
      this.progress.append(this.progressBar);

      const controls = element("div", "sf-procedure__controls");
      this.previous = button("Previous", "previous");
      this.play = button("Play", "play", true);
      this.play.setAttribute("aria-pressed", "false");
      this.next = button("Next", "next");
      controls.append(scenarioLabel, this.previous, this.play, this.next);
      controls.addEventListener("click", (event) => {
        const target = event.target.closest("button[data-action]");
        if (!target) return;
        if (target.dataset.action === "previous") this.move(-1);
        if (target.dataset.action === "next") this.move(1);
        if (target.dataset.action === "play") this.togglePlay();
      });

      this.player.append(
        this.phase,
        this.topologyScroll,
        this.context,
        this.detail,
        this.progress,
        controls,
      );
      source.after(this.player);
    }

    get steps() {
      return this.declaration.scenarios[this.scenario].steps;
    }

    move(offset) {
      this.stop();
      this.stepIndex = Math.max(
        0,
        Math.min(this.stepIndex + offset, this.steps.length - 1),
      );
      this.render();
    }

    togglePlay() {
      if (this.timer) {
        this.stop();
        return;
      }
      if (this.stepIndex === this.steps.length - 1) this.stepIndex = 0;
      this.play.textContent = "Pause";
      this.play.setAttribute("aria-pressed", "true");
      this.render();
      this.timer = window.setInterval(() => {
        if (this.stepIndex >= this.steps.length - 1) {
          this.stop();
          return;
        }
        this.stepIndex += 1;
        this.render();
      }, 2300);
    }

    stop() {
      if (this.timer) window.clearInterval(this.timer);
      this.timer = null;
      if (this.play) {
        this.play.textContent = "Play";
        this.play.setAttribute("aria-pressed", "false");
      }
    }

    renderActivity(entity, activity, active) {
      const panel = this.activityPanels.get(entity.id);
      panel.hidden = !activity;
      panel.classList.toggle("is-idle", !active);
      panel.querySelector("strong").textContent = activity?.title || "";
      const items = activity ? activity.items : [];
      panel.querySelector("ul").replaceChildren(
        ...items.map((value) => element("li", "", value)),
      );
    }

    renderTransitions(transitions) {
      this.flowGrid.replaceChildren();
      const entityIndex = new Map(
        this.declaration.entities.map((entity, index) => [entity.id, index]),
      );
      transitions.forEach((transition, rowIndex) => {
        const source = entityIndex.get(transition.source);
        const target = entityIndex.get(transition.target);
        const start = Math.min(source, target) + 1;
        const end = Math.max(source, target) + 2;
        const flow = element("div", "sf-procedure__transition");
        flow.style.gridColumn = `${start} / ${end}`;
        flow.style.gridRow = String(rowIndex + 1);
        flow.classList.toggle("is-reverse", source > target);
        flow.classList.toggle("is-self", source === target);
        flow.dataset.tone = transition.tone || "normal";
        flow.append(element("span", "sf-procedure__transition-line"));
        const message = element(
          "span",
          "sf-procedure__transition-message",
          transition.label,
        );
        flow.append(message);
        this.flowGrid.append(flow);
      });
      this.flowGrid.classList.toggle("is-empty", transitions.length === 0);
    }

    render() {
      const current = this.steps[this.stepIndex];
      const active = new Set(current.active);
      const completion = ((this.stepIndex + 1) / this.steps.length) * 100;

      this.scenarioSelect.value = this.scenario;
      this.phase.querySelector("strong").textContent = current.phase;

      for (const entity of this.declaration.entities) {
        this.lanes
          .get(entity.id)
          .classList.toggle("is-active", active.has(entity.id));
        this.entityCards
          .get(entity.id)
          .classList.toggle("is-active", active.has(entity.id));
        this.renderActivity(
          entity,
          current.activities[entity.id],
          active.has(entity.id),
        );
      }
      this.renderTransitions(current.transitions);

      this.context.hidden = !current.context;
      if (current.context) {
        this.contextKind.textContent = current.context.kind;
        this.contextValue.textContent = current.context.value;
      }

      this.stepCount.textContent = `Step ${this.stepIndex + 1} of ${this.steps.length}`;
      this.stepTitle.textContent = current.title;
      this.stepDetail.textContent = current.detail;
      this.fields.replaceChildren(
        ...(current.fields || []).map((value) => element("code", "", value)),
      );
      this.progress.setAttribute("aria-valuemax", String(this.steps.length));
      this.progress.setAttribute("aria-valuenow", String(this.stepIndex + 1));
      this.progressBar.style.width = `${completion}%`;
      this.previous.disabled = this.stepIndex === 0;
      this.next.disabled = this.stepIndex === this.steps.length - 1;
    }
  }

  if (!customElements.get("stateforge-procedure-player")) {
    customElements.define(
      "stateforge-procedure-player",
      StateForgeProcedurePlayer,
    );
  }
})();
