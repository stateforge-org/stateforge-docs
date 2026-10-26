(() => {
  function configuration() {
    const dark = document.body.dataset.mdColorScheme === "slate";
    return {
      startOnLoad: false,
      securityLevel: "strict",
      theme: "base",
      themeVariables: {
        background: "transparent",
        fontFamily: "Inter, system-ui, sans-serif",
        primaryColor: dark ? "#18202a" : "#f4f8fc",
        primaryTextColor: dark ? "#f4f7fb" : "#161b22",
        primaryBorderColor: "#7fbcfb",
        lineColor: dark ? "#aeb8c5" : "#556274",
        secondaryColor: dark ? "#222a36" : "#edf3f9",
        tertiaryColor: dark ? "#11161c" : "#ffffff",
        actorBkg: dark ? "#18202a" : "#f4f8fc",
        actorBorder: "#7fbcfb",
        actorTextColor: dark ? "#f4f7fb" : "#161b22",
        signalColor: dark ? "#d7dee8" : "#364152",
        signalTextColor: dark ? "#f4f7fb" : "#161b22",
        labelBoxBkgColor: dark ? "#222a36" : "#edf3f9",
        labelBoxBorderColor: "#7fbcfb",
        labelTextColor: dark ? "#f4f7fb" : "#161b22",
        noteBkgColor: dark ? "#28231a" : "#fff8df",
        noteBorderColor: "#d99a31",
        noteTextColor: dark ? "#f4f7fb" : "#161b22",
      },
    };
  }

  // Mermaid registers its automatic DOMContentLoaded renderer when the bundle
  // is evaluated. Disable it immediately, before that event fires, so the
  // StateForge renderer is the single owner of diagram rendering.
  window.mermaid.initialize(configuration());

  async function render(root = document) {
    const diagrams = Array.from(root.querySelectorAll("pre.mermaid")).filter(
      (diagram) => !diagram.hasAttribute("data-processed"),
    );
    for (const diagram of diagrams) {
      try {
        const code = diagram.querySelector(":scope > code");
        if (code) {
          diagram.textContent = code.textContent;
        }
        await window.mermaid.run({ nodes: [diagram] });
      } catch (error) {
        console.error("StateForge Mermaid diagram is invalid", error);
      }
    }
  }

  function start() {
    void render();
    document.addEventListener(
      "toggle",
      (event) => {
        const details = event.target;
        if (details instanceof HTMLDetailsElement && details.open) {
          void render(details);
        }
      },
      true,
    );
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
