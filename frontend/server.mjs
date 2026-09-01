// Railway 用：以單一 Node 程序靜態伺服 dist/，避免多帶一層 nginx。
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";

const DIST = new URL("./dist/", import.meta.url).pathname;
const PORT = process.env.PORT || 8080;
const MIME = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript",
  ".css": "text/css", ".svg": "image/svg+xml", ".json": "application/json",
  ".woff2": "font/woff2", ".png": "image/png", ".ico": "image/x-icon",
};

createServer(async (req, res) => {
  const url = new URL(req.url, "http://x");
  let path = join(DIST, normalize(url.pathname).replace(/^(\.\.[/\\])+/, ""));
  try {
    const body = await readFile(path);
    res.writeHead(200, { "content-type": MIME[extname(path)] ?? "application/octet-stream" });
    res.end(body);
  } catch {
    const html = await readFile(join(DIST, "index.html"));
    res.writeHead(200, { "content-type": MIME[".html"] });
    res.end(html);
  }
}).listen(PORT, "0.0.0.0", () => console.log(`frontend on :${PORT}`));
