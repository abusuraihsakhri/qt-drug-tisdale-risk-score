import { scoreTisdale } from "./calculator.mjs";

const form = document.querySelector("#score-form");
const error = document.querySelector("#error");
const scoreDisplay = document.querySelector("#score");
const tierDisplay = document.querySelector("#tier");
const note = document.querySelector("#result-note");
const breakdown = document.querySelector("#breakdown");
const exportButton = document.querySelector("#export");
const printButton = document.querySelector("#print");
let lastResult = null;

function inputData() {
  return Object.fromEntries(new FormData(form).entries());
}
function resetDisplay() {
  lastResult = null;
  scoreDisplay.textContent = "—";
  tierDisplay.textContent = "Not calculated";
  tierDisplay.className = "";
  note.textContent = "Complete the clinical inputs, then calculate the risk score.";
  breakdown.replaceChildren();
  exportButton.disabled = true;
  printButton.disabled = true;
  error.textContent = "";
}
function render(result) {
  lastResult = result.complete ? result : null;
  scoreDisplay.textContent = String(result.score);
  tierDisplay.textContent = result.complete ? result.tier + " risk" : "Incomplete";
  tierDisplay.className = result.complete ? result.tier.toLowerCase() : "";
  note.textContent = result.complete
    ? result.tier === "High"
      ? "High-risk stratum. Prompt clinical review and close ECG monitoring may be appropriate."
      : result.tier === "Moderate"
        ? "Moderate-risk stratum. Consider ECG surveillance and correction of modifiable risk factors."
        : "Low-risk stratum within the validated model; individual clinical risks still require review."
    : "Incomplete assessment. A subtotal is shown; do not interpret it as the final risk category.";
  breakdown.replaceChildren();
  for (const part of result.components) {
    const li = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = part.label;
    const points = document.createElement("span");
    points.className = "points";
    points.textContent = "+" + part.points;
    li.append(label, points);
    breakdown.append(li);
  }
  exportButton.disabled = !result.complete;
  printButton.disabled = !result.complete;
}
form.addEventListener("submit", event => {
  event.preventDefault();
  error.textContent = "";
  try {
    const result = scoreTisdale(inputData());
    if (!result.complete) {
      const missing = result.missing.map(key => form.elements.namedItem(key)?.labels?.[0]?.textContent?.split(" · ")[0] || key);
      error.textContent = "Complete these fields: " + missing.join(", ") + ".";
      const first = form.elements.namedItem(result.missing[0]);
      if (first) first.focus();
    }
    render(result);
  } catch (err) {
    resetDisplay();
    error.textContent = err instanceof Error ? err.message : "Invalid input";
  }
});
form.addEventListener("reset", () => resetDisplay());
form.addEventListener("input", () => {
  if (lastResult) resetDisplay();
  else error.textContent = "";
});
document.querySelector("#example").addEventListener("click", () => {
  const example = { age: "72", sex: "female", loop_diuretic: "yes", potassium: "3.4",
    qtc: "465", acute_mi: "no", heart_failure: "yes", num_qtdrugs: "2", sepsis: "no" };
  for (const [name, value] of Object.entries(example)) form.elements.namedItem(name).value = value;
  error.textContent = "";
  render(scoreTisdale(example));
});
exportButton.addEventListener("click", () => {
  if (!lastResult) return;
  const rows = [["factor", "points"], ...lastResult.components.map(p => [p.label, p.points]),
    ["total", lastResult.score], ["risk", lastResult.tier]];
  const csv = rows.map(row => row.map(v => '"' + String(v).replaceAll('"', '""') + '"').join(",")).join("\r\n") + "\r\n";
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "tisdale-score.csv";
  link.click();
  URL.revokeObjectURL(url);
});
printButton.addEventListener("click", () => {
  if (lastResult) window.print();
});
resetDisplay();
