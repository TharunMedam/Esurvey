const normalizeResponse = input => {
  const department = String(input.department || "").trim();
  const satisfaction = Number(input.satisfaction);
  const nps = Number(input.nps);
  const recommendation = String(input.recommendation || "").trim();

  if (!department) {
    throw new Error("department is required");
  }

  if (!Number.isInteger(satisfaction) || satisfaction < 1 || satisfaction > 5) {
    throw new Error("satisfaction must be an integer from 1 to 5");
  }

  if (!Number.isInteger(nps) || nps < 0 || nps > 10) {
    throw new Error("nps must be an integer from 0 to 10");
  }

  return {
    id: input.id,
    department,
    satisfaction,
    nps,
    recommendation,
    submittedAt: input.submittedAt || new Date().toISOString()
  };
};

const average = values =>
  values.length
    ? Number((values.reduce((total, value) => total + value, 0) / values.length).toFixed(2))
    : 0;

const summarize = responses => {
  const normalized = responses.map(normalizeResponse);
  const byDepartment = {};

  for (const response of normalized) {
    if (!byDepartment[response.department]) {
      byDepartment[response.department] = {
        count: 0,
        averageSatisfaction: 0,
        averageNps: 0
      };
    }

    byDepartment[response.department].count += 1;
  }

  for (const department of Object.keys(byDepartment)) {
    const records = normalized.filter(response => response.department === department);
    byDepartment[department].averageSatisfaction = average(
      records.map(response => response.satisfaction)
    );
    byDepartment[department].averageNps = average(records.map(response => response.nps));
  }

  return {
    responseCount: normalized.length,
    averageSatisfaction: average(normalized.map(response => response.satisfaction)),
    averageNps: average(normalized.map(response => response.nps)),
    highPriorityFollowUps: normalized
      .filter(response => response.satisfaction <= 3 || response.nps <= 6)
      .map(response => ({
        id: response.id,
        department: response.department,
        recommendation: response.recommendation || "No recommendation provided"
      })),
    byDepartment
  };
};

const parseCsv = csv => {
  const [headerLine, ...lines] = csv.trim().split(/\r?\n/);
  const headers = headerLine.split(",");

  return lines.map((line, index) => {
    const values = line.split(",");
    const record = { id: `sample-${index + 1}` };
    headers.forEach((header, columnIndex) => {
      record[header] = values[columnIndex];
    });
    return normalizeResponse(record);
  });
};

module.exports = { normalizeResponse, summarize, parseCsv };
