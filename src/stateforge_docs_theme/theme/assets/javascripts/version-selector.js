"use strict";

for (const selector of document.querySelectorAll("[data-sf-version-selector]")) {
  selector.addEventListener("change", () => {
    const destination = selector.value;
    if (destination) {
      window.location.assign(destination);
    }
  });
}
