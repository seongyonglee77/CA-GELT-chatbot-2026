(() => {
  "use strict";

  const personaCards = [...document.querySelectorAll("[data-persona-id]")];

  if (!personaCards.length) return;

  personaCards.forEach((card, index) => {
    card.style.setProperty("--card-index", String(index));
  });
})();
