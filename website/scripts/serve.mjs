import { createReadStream, existsSync } from "node:fs";
import { stat } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";
import http from "node:http";
import { spawn } from "node:child_process";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const dist = join(root, "dist");
const port = Number(process.env.PORT || 4174);

await new Promise((resolve, reject) => {
  const build = spawn(process.execPath, [join(here, "build.mjs")], { stdio: "inherit" });
  build.on("exit", (code) => code === 0 ? resolve() : reject(new Error(`build failed: ${code}`)));
});

const types = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".xml": "application/xml; charset=utf-8",
};

http.createServer(async (request, response) => {
  const rawPath = new URL(request.url || "/", `http://${request.headers.host}`).pathname;
  const safePath = normalize(decodeURIComponent(rawPath)).replace(/^(\.\.[/\\])+/, "");
  let target = join(dist, safePath);

  try {
    const info = existsSync(target) ? await stat(target) : null;
    if (info?.isDirectory()) target = join(target, "index.html");
    if (!existsSync(target)) {
      response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("Not found");
      return;
    }
    response.writeHead(200, { "Content-Type": types[extname(target)] || "application/octet-stream" });
    createReadStream(target).pipe(response);
  } catch {
    response.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("Server error");
  }
}).listen(port, "127.0.0.1", () => {
  console.log(`Public website preview: http://127.0.0.1:${port}`);
});
