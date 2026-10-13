import test from "node:test";
import assert from "node:assert/strict";
import { scoreTisdale, MAX_SCORE, FACTORS } from "../web/calculator.mjs";

const normal = { age: 40, sex: "male", loop_diuretic: "no", potassium: 4.1,
  qtc: 410, acute_mi: "no", heart_failure: "no", num_qtdrugs: 0, sepsis: "no" };

test("full model comprises nine factors and maximum 21", () => {
  assert.equal(FACTORS.length, 9);
  assert.equal(MAX_SCORE, 21);
  const r = scoreTisdale({ age: 80, sex: "female", loop_diuretic: "yes",
    potassium: 3, qtc: 500, acute_mi: "yes", heart_failure: "yes",
    num_qtdrugs: 2, sepsis: "yes" });
  assert.equal(r.score, 21);
  assert.equal(r.tier, "High");
  assert.equal(r.complete, true);
});
test("no risk factors", () => {
  const r = scoreTisdale(normal);
  assert.equal(r.score, 0);
  assert.equal(r.tier, "Low");
});
test("age threshold is 68 (not 65)", () => {
  assert.equal(scoreTisdale({ ...normal, age: 67 }).score, 0);
  assert.equal(scoreTisdale({ ...normal, age: 68 }).score, 1);
});
test("drug count contributes 0, 3, or 6 points", () => {
  for (const [n, expected] of [[0, 0], [1, 3], [2, 6], [5, 6]]) {
    assert.equal(scoreTisdale({ ...normal, num_qtdrugs: n }).score, expected);
  }
});
test("individual published weights for clinical factors", () => {
  assert.equal(scoreTisdale({ ...normal, potassium: 3.5 }).score, 2);
  assert.equal(scoreTisdale({ ...normal, qtc: 450 }).score, 2);
  assert.equal(scoreTisdale({ ...normal, heart_failure: "yes" }).score, 3);
  assert.equal(scoreTisdale({ ...normal, sepsis: "yes" }).score, 3);
});
test("risk tiers follow 0-6, 7-10, >=11", () => {
  assert.equal(scoreTisdale({ ...normal, num_qtdrugs: 2 }).tier, "Low");
  assert.equal(scoreTisdale({ ...normal, num_qtdrugs: 2, age: 70 }).tier, "Moderate");
  assert.equal(scoreTisdale({ ...normal, num_qtdrugs: 2, age: 70, sepsis: "yes", potassium: 3.2 }).tier, "High");
});
test("missing clinical data never yields a low-risk category", () => {
  const { qtc, ...incomplete } = normal;
  const r = scoreTisdale(incomplete);
  assert.equal(r.complete, false);
  assert.equal(r.tier, "Incomplete");
  assert.deepEqual(r.missing, ["qtc"]);
});
test("invalid sex, nonfinite numbers, fractional drug counts, and ambiguous flags are rejected", () => {
  for (const delta of [
    { sex: "other" }, { potassium: "NaN" }, { qtc: Infinity },
    { num_qtdrugs: 1.5 }, { loop_diuretic: "perhaps" }, { age: -1 },
  ]) assert.throws(() => scoreTisdale({ ...normal, ...delta }));
});
