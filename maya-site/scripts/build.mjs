import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

process.env.MAYA_SITE_URL ||= "https://maya-exe.vercel.app";
const { pages, renderPage, siteUrl } = await import("../src/site.mjs");

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const dist = join(root, "dist");

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });

for (const page of pages) {
  const relative = page.path === "/" ? "index.html" : join(page.path.slice(1), "index.html");
  const target = join(dist, relative);
  await mkdir(dirname(target), { recursive: true });

  let html = renderPage(page);
  if (page.path === "/" || page.path === "/videos/") {
    html = html.replace(
      '<p class="status">Coming soon</p>',
      '<p class="status"><a class="text-link" href="/shop-the-look/ai-picked-makeup/">Live · Watch V001 →</a></p>',
    );
  }

  await writeFile(target, html, "utf8");
}

await cp(join(root, "src", "styles.css"), join(dist, "styles.css"));
await cp(join(root, "static"), dist, { recursive: true });

const extraSitemapPaths = [
  "/shop-the-look/ai-picked-makeup/",
];
const sitemapPaths = [...pages.map((page) => page.path), ...extraSitemapPaths];
const sitemap = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${sitemapPaths.map((path) => `  <url><loc>${siteUrl}${path}</loc></url>`).join("\n")}\n</urlset>\n`;
await writeFile(join(dist, "sitemap.xml"), sitemap, "utf8");
await writeFile(join(dist, "robots.txt"), `User-agent: *\nAllow: /\nSitemap: ${siteUrl}/sitemap.xml\n`, "utf8");

console.log(`Built ${pages.length + extraSitemapPaths.length} Maya.exe pages into ${dist}`);
