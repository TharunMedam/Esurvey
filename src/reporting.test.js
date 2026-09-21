const assert = require("assert");
const { normalizeResponse, summarize, parseCsv } = require("./reporting");

assert.throws(
  () => normalizeResponse({ department: "", satisfaction: 6, nps: 11 }),
  /department is required/
);

const responses = parseCsv(`department,satisfaction,nps,recommendation
Support,5,9,docs
Support,3,6,routing
Engineering,4,8,release notes`);

const report = summarize(responses);
assert.strictEqual(report.responseCount, 3);
assert.strictEqual(report.averageSatisfaction, 4);
assert.strictEqual(report.byDepartment.Support.count, 2);
assert.strictEqual(report.highPriorityFollowUps.length, 1);

console.log("esurvey reporting tests passed");
