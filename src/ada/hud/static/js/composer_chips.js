/** Composer quick-capture chips (M19a). */

export function wireComposerChips() {
  const row = document.getElementById("composer-chips");
  const input = document.getElementById("chat-input");
  if (!row || !input) return;
  row.querySelectorAll(".composer-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const pre = btn.getAttribute("data-prefill") || "";
      const chip = btn.getAttribute("data-chip") || "";
      input.value = pre;
      input.dataset.packChip = chip;
      input.focus();
    });
  });
  input.addEventListener("input", () => {
    if (!input.value.trim()) {
      input.dataset.packChip = "";
    }
  });
}
