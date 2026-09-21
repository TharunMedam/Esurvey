const http = require("http");
const path = require("path");
const fs = require("fs");
const { URL } = require("url");
const { normalizeResponse, parseCsv, summarize } = require("./reporting");

const PORT = Number(process.env.PORT || 4200);
const samplePath = path.join(__dirname, "..", "data", "sample-responses.csv");
let responses = parseCsv(fs.readFileSync(samplePath, "utf8"));

const sendJson = (res, statusCode, payload) => {
  res.writeHead(statusCode, { "Content-Type": "application/json" });
  res.end(JSON.stringify(payload, null, 2));
};

const readBody = req =>
  new Promise((resolve, reject) => {
    let body = "";
    req.on("data", chunk => {
      body += chunk;
    });
    req.on("end", () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch {
        reject(new Error("request body must be valid JSON"));
      }
    });
    req.on("error", reject);
  });

const serveStatic = (res, fileName) => {
  const filePath = path.join(__dirname, "..", "public", fileName);
  fs.createReadStream(filePath)
    .on("error", () => sendJson(res, 404, { error: "not found" }))
    .pipe(res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" }));
};

const handle = async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  try {
    if (req.method === "GET" && url.pathname === "/") {
      return serveStatic(res, "index.html");
    }

    if (req.method === "GET" && url.pathname === "/api/responses") {
      const department = url.searchParams.get("department");
      const filtered = department
        ? responses.filter(response => response.department === department)
        : responses;

      return sendJson(res, 200, { responses: filtered });
    }

    if (req.method === "POST" && url.pathname === "/api/responses") {
      const response = normalizeResponse({
        ...(await readBody(req)),
        id: `response-${responses.length + 1}`
      });
      responses = [response, ...responses];

      return sendJson(res, 201, { response });
    }

    if (req.method === "GET" && url.pathname === "/api/reports/summary") {
      return sendJson(res, 200, { report: summarize(responses) });
    }

    return sendJson(res, 404, { error: "not found" });
  } catch (error) {
    return sendJson(res, 400, { error: error.message });
  }
};

if (require.main === module) {
  http.createServer(handle).listen(PORT, () => {
    console.log(`E-survey project running on http://localhost:${PORT}`);
  });
}

module.exports = handle;
