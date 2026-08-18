import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { pages, renderPage, siteUrl } from "../src/site.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const dist = join(root, "dist");

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });

for (const page of pages) {
  const relative = page.path === "/" ? "index.html" : join(page.path.slice(1), "index.html");
  const target = join(dist, relative);
  await mkdir(dirname(target), { recursive: true });
  await writeFile(target, renderPage(page), "utf8");
}

await cp(join(root, "src", "styles.css"), join(dist, "styles.css"));

const sitemap = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${pages.map((page) => `  <url><loc>${siteUrl}${page.path}</loc></url>`).join("\n")}\n</urlset>\n`;
await writeFile(join(dist, "sitemap.xml"), sitemap, "utf8");
await writeFile(join(dist, "robots.txt"), `User-agent: *\nAllow: /\nSitemap: ${siteUrl}/sitemap.xml\n`, "utf8");

if (siteUrl.includes("example.invalid")) {
  console.warn("Maya.exe built with placeholder MAYA_SITE_URL. Set it before production deployment.");
}

console.log(`Built ${pages.length} Maya.exe pages into ${dist}`);
