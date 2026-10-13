/** Pure deterministic Tisdale scoring. No data leaves the browser. */
export const MAX_SCORE = 21;
export const FACTORS = Object.freeze([
  { key: "age", label: "Age ≥68 years", max: 1 },
  { key: "sex", label: "Female sex", max: 1 },
  { key: "loop_diuretic", label: "Loop diuretic", max: 1 },
  { key: "potassium", label: "Potassium ≤3.5 mEq/L", max: 2 },
  { key: "qtc", label: "Admission QTc ≥450 ms", max: 2 },
  { key: "acute_mi", label: "Acute myocardial infarction", max: 2 },
  { key: "heart_failure", label: "Heart failure", max: 3 },
  { key: "num_qtdrugs", label: "QTc-prolonging medications", max: 6 },
  { key: "sepsis", label: "Sepsis", max: 3 },
]);

function numeric(value, label, min, max, integer = false) {
  const n = typeof value === "number" ? value : Number(value);
  if (value === null || value === undefined || String(value).trim() === "" ||
      !Number.isFinite(n) || n < min || n > max || (integer && !Number.isInteger(n))) {
    throw new RangeError(`${label} must be ${integer ? "an integer" : "a number"} between ${min} and ${max}`);
  }
  return n;
}
function yesNo(value, label) {
  if (value === true || value === false) return value;
  if (value === "yes" || value === "true" || value === "1") return true;
  if (value === "no" || value === "false" || value === "0") return false;
  throw new TypeError(`${label} must be yes or no`);
}
export function scoreTisdale(input) {
  if (!input || typeof input !== "object") throw new TypeError("Input object required");
  const missing = FACTORS.filter(({ key }) => input[key] === null || input[key] === undefined ||
    String(input[key]).trim() === "").map(({ key }) => key);
  const row = [];
  const push = (key, points, value) => row.push({ key, label: FACTORS.find(f => f.key === key).label, points, value });
  if (!missing.includes("age")) {
    const n = numeric(input.age, "Age", 0, 150);
    push("age", n >= 68 ? 1 : 0, n);
  }
  if (!missing.includes("sex")) {
    const s = String(input.sex).toLowerCase().trim();
    if (!["female", "male", "f", "m"].includes(s)) throw new TypeError("Sex must be female or male");
    push("sex", ["female", "f"].includes(s) ? 1 : 0, s);
  }
  if (!missing.includes("loop_diuretic")) {
    const v = yesNo(input.loop_diuretic, "Loop diuretic");
    push("loop_diuretic", v ? 1 : 0, v);
  }
  if (!missing.includes("potassium")) {
    const n = numeric(input.potassium, "Potassium", 0.1, 10);
    push("potassium", n <= 3.5 ? 2 : 0, n);
  }
  if (!missing.includes("qtc")) {
    const n = numeric(input.qtc, "Admission QTc", 200, 800);
    push("qtc", n >= 450 ? 2 : 0, n);
  }
  if (!missing.includes("acute_mi")) {
    const v = yesNo(input.acute_mi, "Acute MI");
    push("acute_mi", v ? 2 : 0, v);
  }
  if (!missing.includes("heart_failure")) {
    const v = yesNo(input.heart_failure, "Heart failure");
    push("heart_failure", v ? 3 : 0, v);
  }
  if (!missing.includes("num_qtdrugs")) {
    const n = numeric(input.num_qtdrugs, "QTc-prolonging medication count", 0, 100, true);
    push("num_qtdrugs", n >= 2 ? 6 : n === 1 ? 3 : 0, n);
  }
  if (!missing.includes("sepsis")) {
    const v = yesNo(input.sepsis, "Sepsis");
    push("sepsis", v ? 3 : 0, v);
  }
  const score = row.reduce((s, item) => s + item.points, 0);
  if (score > MAX_SCORE) throw new Error("Score exceeds validated maximum");
  const complete = missing.length === 0;
  const tier = !complete ? "Incomplete" : score <= 6 ? "Low" : score <= 10 ? "Moderate" : "High";
  return { score, max_score: MAX_SCORE, complete, tier, missing, components: row };
}
