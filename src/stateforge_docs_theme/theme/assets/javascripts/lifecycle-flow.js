(() => {
  "use strict";

  const EVENT_DURATION_MS = 620;

  function parseEvents(step) {
    try {
      const events = JSON.parse(step.dataset.events || "[]");
      return Array.isArray(events) ? events : [];
    } catch (error) {
      console.error("StateForge lifecycle events are invalid", error);
      return [];
    }
  }

  function initialize(root) {
    if (root.dataset.initialized === "true") return;

    const steps = Array.from(root.querySelectorAll("[data-sf-flow-step]"));
    const sourceState = root.querySelector("[data-sf-flow-source-state]");
    const targetState = root.querySelector("[data-sf-flow-target-state]");
    const packet = root.querySelector("[data-sf-flow-packet]");
    const message = root.querySelector("[data-sf-flow-message]");
    const status = root.querySelector("[data-sf-flow-status]");
    const source = root.querySelector('[data-sf-flow-actor="source"]');
    const target = root.querySelector('[data-sf-flow-actor="target"]');

    if (
      steps.length === 0 ||
      !sourceState ||
      !targetState ||
      !packet ||
      !message ||
      !status ||
      !source ||
      !target
    ) {
      return;
    }

    let run = 0;
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    );

    function clearAnimation() {
      packet.classList.remove("is-forward", "is-reverse");
      source.classList.remove("is-sending", "is-receiving");
      target.classList.remove("is-sending", "is-receiving");
    }

    function showEvent(event) {
      const direction = event.direction === "reverse" ? "reverse" : "forward";
      message.textContent = event.label || "Protocol message";
      clearAnimation();

      if (reducedMotion.matches) return;

      const sender = direction === "forward" ? source : target;
      const receiver = direction === "forward" ? target : source;
      sender.classList.add("is-sending");
      receiver.classList.add("is-receiving");
      void packet.offsetWidth;
      packet.classList.add(`is-${direction}`);
    }

    async function select(step, play) {
      const selectedRun = ++run;
      const events = parseEvents(step);

      for (const candidate of steps) {
        const selected = candidate === step;
        candidate.setAttribute("aria-pressed", String(selected));
        const action = candidate.querySelector("[data-sf-flow-action]");
        if (action) action.textContent = selected ? "Replay" : "Play";
      }

      sourceState.textContent = step.dataset.sourceState || "Source";
      targetState.textContent = step.dataset.targetState || "Target";
      root.dataset.stage = step.dataset.stage || "";
      clearAnimation();

      if (!play) {
        const firstEvent = events[0];
        message.textContent = firstEvent?.label || "Protocol exchange";
        status.textContent =
          root.dataset.prompt || "Select a stage to play its exchange";
        root.setAttribute("aria-busy", "false");
        return;
      }

      if (reducedMotion.matches || events.length === 0) {
        const finalEvent = events.at(-1);
        message.textContent = finalEvent?.label || "Protocol exchange";
        status.textContent = step.dataset.result || "Ready";
        root.setAttribute("aria-busy", "false");
        return;
      }

      root.setAttribute("aria-busy", "true");
      for (const event of events) {
        if (run !== selectedRun) return;
        status.textContent = event.detail || event.label || "Protocol exchange";
        showEvent(event);
        await new Promise((resolve) => {
          window.setTimeout(resolve, EVENT_DURATION_MS);
        });
      }

      if (run !== selectedRun) return;
      clearAnimation();
      status.textContent = step.dataset.result || "Stage complete";
      root.setAttribute("aria-busy", "false");
    }

    for (const step of steps) {
      step.addEventListener("click", () => select(step, true));
    }

    root.dataset.initialized = "true";
    const initial =
      steps.find((step) => step.getAttribute("aria-pressed") === "true") ||
      steps[0];
    select(initial, false);
  }

  for (const root of document.querySelectorAll("[data-sf-lifecycle]")) {
    initialize(root);
  }
})();
