(() => {
  "use strict";

  const script = document.currentScript;
  const assetRoot = new URL("../images/", script ? script.src : document.baseURI);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function control(label, action, primary = false) {
    const node = element(
      "button",
      primary ? "sf-entity-flow__control is-primary" : "sf-entity-flow__control",
      label,
    );
    node.type = "button";
    node.dataset.action = action;
    return node;
  }

  function brand(entity) {
    const wrapper = element("span", "sf-entity-flow__brand");
    wrapper.dataset.brand = entity.brand || "none";
    if (entity.brand === "stateforge") {
      const picture = document.createElement("picture");
      const light = document.createElement("img");
      const dark = document.createElement("img");
      light.src = new URL("stateforge-mark-black.svg", assetRoot).href;
      dark.src = new URL("stateforge-mark.svg", assetRoot).href;
      light.alt = "StateForge";
      dark.alt = "StateForge";
      light.className = "sf-entity-flow__brand-light";
      dark.className = "sf-entity-flow__brand-dark";
      picture.append(light, dark);
      wrapper.append(picture);
    } else if (entity.brand === "service") {
      wrapper.setAttribute("aria-hidden", "true");
      const glyph = element("span", "sf-entity-flow__service-glyph");
      glyph.append(element("i"), element("i"), element("i"));
      wrapper.append(glyph);
    } else {
      wrapper.setAttribute("aria-hidden", "true");
      wrapper.append(element("span", "", entity.label.slice(0, 3)));
    }
    return wrapper;
  }

  class StateForgeEntityFlow extends HTMLElement {
    connectedCallback() {
      if (this.dataset.initialized === "true") return;
      const source = this.querySelector(".sf-entity-flow-data");
      if (!source) return;
      try {
        this.declaration = JSON.parse(source.textContent || "");
      } catch (error) {
        console.error("StateForge entity-flow declaration is invalid", error);
        return;
      }
      this.stepIndex = 0;
      this.timer = null;
      this.hasAutoplayed = false;
      this.dataset.initialized = "true";
      this.build(source);
      this.render(false);
      this.observeAutoplay();
    }

    disconnectedCallback() {
      this.stop();
      if (this.observer) this.observer.disconnect();
    }

    build(source) {
      const fallback = this.querySelector(".sf-entity-flow-fallback");
      if (fallback) fallback.remove();

      this.flow = element("section", "sf-entity-flow");
      this.flow.setAttribute("aria-label", this.declaration.title);
      this.flow.style.setProperty(
        "--sf-entity-flow-count",
        String(this.declaration.entities.length),
      );

      this.phase = element("div", "sf-entity-flow__phase");
      this.phase.append(
        element("span", "", "Current event"),
        element("strong"),
      );

      this.viewport = element("div", "sf-entity-flow__viewport");
      this.stage = element("div", "sf-entity-flow__stage");
      this.entityGrid = element("div", "sf-entity-flow__entities");
      this.cards = new Map();
      this.stateLabels = new Map();
      this.stateValues = new Map();

      for (const entity of this.declaration.entities) {
        const card = element("article", "sf-entity-flow__entity");
        card.dataset.entity = entity.id;
        card.dataset.accent = entity.accent;
        const header = element("header", "sf-entity-flow__entity-header");
        const identity = element("div", "sf-entity-flow__identity");
        identity.append(
          element("span", "sf-entity-flow__kind", entity.kind),
          element("strong", "", entity.label),
        );
        header.append(brand(entity), identity);
        const description = entity.description
          ? element("p", "sf-entity-flow__description", entity.description)
          : null;
        const state = element("div", "sf-entity-flow__state");
        const stateLabel = element("span");
        const stateValue = element("strong");
        state.append(stateLabel, stateValue);
        card.append(header);
        if (description) card.append(description);
        card.append(state);
        this.cards.set(entity.id, card);
        this.stateLabels.set(entity.id, stateLabel);
        this.stateValues.set(entity.id, stateValue);
        this.entityGrid.append(card);
      }

      this.transitionGrid = element("div", "sf-entity-flow__transitions");
      this.transitionGrid.setAttribute("aria-label", "Current entity transitions");
      this.stage.append(this.entityGrid, this.transitionGrid);
      this.viewport.append(this.stage);

      this.responsibility = element("div", "sf-entity-flow__responsibility");
      this.responsibility.append(
        element("span", "sf-entity-flow__responsibility-label", "Responsibility"),
        element("strong"),
      );

      this.detail = element("div", "sf-entity-flow__detail");
      this.detail.setAttribute("aria-live", "polite");
      const copy = element("div");
      this.stepCount = element("span", "sf-entity-flow__step-count");
      this.stepTitle = element("h3");
      this.stepDetail = element("p");
      copy.append(this.stepCount, this.stepTitle, this.stepDetail);
      this.detail.append(copy);

      this.progress = element("div", "sf-entity-flow__progress");
      this.progress.setAttribute("role", "progressbar");
      this.progress.setAttribute("aria-label", "Entity flow progress");
      this.progress.setAttribute("aria-valuemin", "1");
      this.progressBar = element("span", "sf-entity-flow__progress-bar");
      this.progress.append(this.progressBar);

      const footer = element("div", "sf-entity-flow__footer");
      this.stepButtons = element("div", "sf-entity-flow__step-buttons");
      this.declaration.steps.forEach((step, index) => {
        const node = element("button", "", String(index + 1));
        node.type = "button";
        node.dataset.step = String(index);
        node.setAttribute("aria-label", `Show ${step.title}`);
        node.addEventListener("click", () => {
          this.stop();
          this.stepIndex = index;
          this.render(true);
        });
        this.stepButtons.append(node);
      });
      const controls = element("div", "sf-entity-flow__controls");
      this.previous = control("Previous", "previous");
      this.play = control("Play", "play", true);
      this.play.setAttribute("aria-pressed", "false");
      this.next = control("Next", "next");
      controls.append(this.previous, this.play, this.next);
      controls.addEventListener("click", (event) => {
        const target = event.target.closest("button[data-action]");
        if (!target) return;
        if (target.dataset.action === "previous") this.move(-1);
        if (target.dataset.action === "next") this.move(1);
        if (target.dataset.action === "play") this.togglePlay();
      });
      footer.append(this.stepButtons, controls);

      this.flow.append(
        this.phase,
        this.viewport,
        this.responsibility,
        this.detail,
        this.progress,
        footer,
      );
      source.after(this.flow);
    }

    observeAutoplay() {
      if (!this.declaration.autoplay || reducedMotion.matches) return;
      this.observer = new IntersectionObserver(
        (entries) => {
          if (
            this.hasAutoplayed ||
            !entries.some((entry) => entry.isIntersecting)
          ) {
            return;
          }
          this.hasAutoplayed = true;
          this.start();
          this.observer.disconnect();
        },
        { threshold: 0.55 },
      );
      this.observer.observe(this);
    }

    stateAt(entityId) {
      const entity = this.declaration.entities.find((item) => item.id === entityId);
      let state = entity.state;
      for (let index = 0; index <= this.stepIndex; index += 1) {
        const update = this.declaration.steps[index].states[entityId];
        if (update) state = update;
      }
      return state;
    }

    move(offset) {
      this.stop();
      this.stepIndex = Math.max(
        0,
        Math.min(
          this.stepIndex + offset,
          this.declaration.steps.length - 1,
        ),
      );
      this.render(true);
    }

    togglePlay() {
      if (this.timer) {
        this.stop();
        return;
      }
      this.start();
    }

    start() {
      this.stop();
      if (this.stepIndex === this.declaration.steps.length - 1) {
        this.stepIndex = 0;
      }
      this.play.textContent = "Pause";
      this.play.setAttribute("aria-pressed", "true");
      this.render(true);
      this.timer = window.setInterval(() => {
        if (this.stepIndex >= this.declaration.steps.length - 1) {
          this.stop();
          return;
        }
        this.stepIndex += 1;
        this.render(true);
      }, 2200);
    }

    stop() {
      if (this.timer) window.clearInterval(this.timer);
      this.timer = null;
      if (this.play) {
        this.play.textContent = "Play";
        this.play.setAttribute("aria-pressed", "false");
      }
    }

    renderTransitions(transitions, animate) {
      this.transitionGrid.replaceChildren();
      const entityIndex = new Map(
        this.declaration.entities.map((entity, index) => [entity.id, index]),
      );
      transitions.forEach((transition, rowIndex) => {
        const source = entityIndex.get(transition.source);
        const target = entityIndex.get(transition.target);
        const start = Math.min(source, target) + 1;
        const end = Math.max(source, target) + 2;
        const node = element("div", "sf-entity-flow__transition");
        node.style.gridColumn = `${start} / ${end}`;
        node.style.gridRow = String(rowIndex + 1);
        node.classList.toggle("is-reverse", source > target);
        node.dataset.tone = transition.tone || "normal";
        node.append(
          element("span", "sf-entity-flow__transition-line"),
          element("span", "sf-entity-flow__packet"),
          element("code", "sf-entity-flow__message", transition.label),
        );
        this.transitionGrid.append(node);
        if (animate && !reducedMotion.matches) {
          window.requestAnimationFrame(() => node.classList.add("is-running"));
        }
      });
      this.transitionGrid.classList.toggle("is-empty", transitions.length === 0);
    }

    render(animate) {
      const current = this.declaration.steps[this.stepIndex];
      const active = new Set(current.active);
      const responsible = new Set(current.responsibility.entities);
      const completion = ((this.stepIndex + 1) / this.declaration.steps.length) * 100;

      this.phase.querySelector("strong").textContent = current.phase;
      for (const entity of this.declaration.entities) {
        const card = this.cards.get(entity.id);
        const state = this.stateAt(entity.id);
        card.classList.toggle("is-active", active.has(entity.id));
        card.classList.toggle("is-responsible", responsible.has(entity.id));
        card.dataset.tone = state.tone || "normal";
        this.stateLabels.get(entity.id).textContent = state.label;
        this.stateValues.get(entity.id).textContent = state.value;
      }
      this.renderTransitions(current.transitions, animate);

      this.responsibility.querySelector("strong").textContent =
        current.responsibility.label;
      this.stepCount.textContent = `Step ${this.stepIndex + 1} of ${this.declaration.steps.length}`;
      this.stepTitle.textContent = current.title;
      this.stepDetail.textContent = current.detail;
      this.progress.setAttribute(
        "aria-valuemax",
        String(this.declaration.steps.length),
      );
      this.progress.setAttribute("aria-valuenow", String(this.stepIndex + 1));
      this.progressBar.style.width = `${completion}%`;
      this.previous.disabled = this.stepIndex === 0;
      this.next.disabled = this.stepIndex === this.declaration.steps.length - 1;
      [...this.stepButtons.children].forEach((node, index) => {
        node.setAttribute("aria-current", index === this.stepIndex ? "step" : "false");
      });
    }
  }

  if (!customElements.get("stateforge-entity-flow")) {
    customElements.define("stateforge-entity-flow", StateForgeEntityFlow);
  }
})();
