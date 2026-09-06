const siteUrl = (process.env.MAYA_SITE_URL || "https://maya.example.invalid").replace(/\/$/, "");
const trackingBase = (process.env.AFFILIATE_TRACKING_BASE_URL || "").replace(/\/$/, "");

const escapeHtml = (value = "") => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

const nav = [
  ["Videos", "/videos/"],
  ["Reviews", "/reviews/"],
  ["AI Beauty Tools", "/ai-beauty-tools/"],
  ["Beauty Tech", "/beauty-tech/"],
  ["Guides", "/guides/"],
  ["Templates", "/templates/"],
  ["Deals", "/deals/"],
  ["TikTok Shop", "/tiktok-shop/"],
  ["About", "/about/"],
];

const products = [
  {
    id: "led-mask",
    name: "LED face mask",
    category: "Beauty-tech gadgets",
    description: "A light-therapy device category we want Maya to test on camera before making a recommendation.",
    price: "Price to verify",
    url: process.env.TIKTOK_SHOP_LED_MASK_URL || "",
    status: "Testing queue",
  },
  {
    id: "smart-mirror",
    name: "Smart vanity mirror",
    category: "Beauty-tech gadgets",
    description: "Adjustable-light smart mirror for makeup and close-up creator workflows.",
    price: "Price to verify",
    url: process.env.TIKTOK_SHOP_SMART_MIRROR_URL || "",
    status: "Researching",
  },
  {
    id: "brush-set",
    name: "Everyday makeup brush set",
    category: "Makeup tools",
    description: "A practical brush kit for AI-selected looks and repeatable tutorial formats.",
    price: "Price to verify",
    url: process.env.TIKTOK_SHOP_BRUSH_SET_URL || "",
    status: "Researching",
  },
  {
    id: "ring-light",
    name: "Compact creator ring light",
    category: "Creator gear",
    description: "Simple lighting gear for beauty close-ups, short videos and before/after shots.",
    price: "Price to verify",
    url: process.env.TIKTOK_SHOP_RING_LIGHT_URL || "",
    status: "Testing queue",
  },
  {
    id: "skin-scanner",
    name: "AI-assisted skin scanner",
    category: "AI-assisted beauty",
    description: "A connected beauty device category worth testing for usefulness, privacy and accuracy claims.",
    price: "Price to verify",
    url: process.env.TIKTOK_SHOP_SKIN_SCANNER_URL || "",
    status: "Researching",
  },
  {
    id: "heat-brush",
    name: "Smart heat styling brush",
    category: "Beauty-tech gadgets",
    description: "Temperature-controlled styling tool for fast routines and comparison content.",
    price: "Price to verify",
    url: process.env.TIKTOK_SHOP_HEAT_BRUSH_URL || "",
    status: "Researching",
  },
];

const aiTools = [
  ["Virtual try-on apps", "Preview makeup looks before buying products.", "AI Makeup"],
  ["Shade matching tools", "Compare foundation or lipstick suggestions with real-world results.", "AI Makeup"],
  ["Routine planner AI", "Turn products you already own into a simple AM/PM routine.", "Skincare"],
  ["Beauty content hook writer", "Generate short-form hooks, titles and shot-list ideas.", "Creator Tools"],
  ["Ingredient explainers", "Translate ingredient lists into plain language, without replacing professional advice.", "Skincare"],
  ["Thumbnail cleanup tools", "Speed up background removal and cover-frame cleanup.", "Creator Tools"],
];

const videos = [
  ["I let AI choose my entire makeup look", "AI Makeup", "Coming soon"],
  ["Can a beauty app stop you buying the wrong shade?", "AI Makeup", "Coming soon"],
  ["I gave AI a small budget to build a full makeup routine", "Experiment", "Coming soon"],
  ["Human makeup artist vs AI: what does each get right?", "Experiment", "Coming soon"],
  ["Three beauty-tech gadgets that might actually save time", "Beauty Tech", "Coming soon"],
  ["I built a tiny beauty app without coding", "Creator Tools", "Coming soon"],
  ["Can AI create a five-minute work makeup routine?", "AI Makeup", "Coming soon"],
  ["Beauty creator workflow: from idea to short video with AI", "Creator Tools", "Coming soon"],
];

const guides = [
  ["How to test an AI beauty app before paying", "Check free tiers, privacy, cancellation, real limits and whether the output helps with an actual decision."],
  ["Beauty-tech buying checklist", "A practical checklist for claims, return policies, app dependencies, subscriptions and replacement costs."],
  ["How to film beauty close-ups with simple lighting", "A beginner setup for consistent before/after footage without pretending lighting does not affect results."],
  ["How to evaluate AI skincare advice", "Use AI for organization and questions, not diagnosis; verify medical claims with qualified sources."],
];

const templates = [
  ["Beauty creator content calendar", "A weekly structure for research, testing, filming, editing and publishing."],
  ["Honest product review script", "A repeatable format for context, what was tested, pros, cons, who it suits and what remains unknown."],
  ["AI beauty prompt starter pack", "Prompts for hooks, comparisons, shot lists and educational scripts."],
  ["Product test log", "Track date, product, claim, test method, result and what still needs verification."],
];

const disclosure = `Maya.exe is a virtual AI creator. Maya is not a real person. The editorial team behind Maya.exe chooses topics, verifies claims and controls what gets published. Some outbound links may become affiliate or sponsored links. When that happens, they are labelled and use sponsored/nofollow attributes. We do not publish invented follower counts, fabricated testimonials, fake product tests or made-up discounts.`;

const card = ({ kicker, title, text, href, cta = "Explore" }) => `
  <article class="card">
    ${kicker ? `<p class="kicker">${escapeHtml(kicker)}</p>` : ""}
    <h3>${escapeHtml(title)}</h3>
    <p>${escapeHtml(text)}</p>
    ${href ? `<a class="text-link" href="${escapeHtml(href)}">${escapeHtml(cta)} →</a>` : ""}
  </article>`;

const affiliateButton = (href, label) => {
  if (!href) return `<span class="button disabled">Link coming soon</span>`;
  return `<a class="button" href="${escapeHtml(href)}" target="_blank" rel="sponsored nofollow noopener noreferrer">${escapeHtml(label)}</a>`;
};

const productCard = (item) => `
  <article class="product-card">
    <div class="tag-row"><span class="tag">${escapeHtml(item.category)}</span><span class="tag affiliate">Affiliate-ready</span></div>
    <div class="product-art" aria-hidden="true"><span>${escapeHtml(item.name.slice(0, 1))}</span></div>
    <h3>${escapeHtml(item.name)}</h3>
    <p>${escapeHtml(item.description)}</p>
    <div class="product-meta"><strong>${escapeHtml(item.price)}</strong><span>${escapeHtml(item.status)}</span></div>
    ${affiliateButton(item.url, "View on TikTok Shop")}
  </article>`;

const sectionHeader = (eyebrow, title, text = "") => `
  <div class="section-heading">
    <div><p class="eyebrow">${escapeHtml(eyebrow)}</p><h2>${escapeHtml(title)}</h2>${text ? `<p>${escapeHtml(text)}</p>` : ""}</div>
  </div>`;

const homeBody = `
<section class="hero">
  <div class="hero-copy">
    <div class="virtual-badge">Virtual AI creator · human-directed</div>
    <p class="eyebrow">Beauty × AI × useful tech</p>
    <h1>Beauty, but make it smart.</h1>
    <p class="lede">Maya.exe explores AI beauty apps, makeup tech, creator tools and gadgets with one rule: attention is useful only when the recommendation is honest.</p>
    <div class="hero-actions"><a class="button" href="/videos/">See upcoming videos</a><a class="button secondary" href="/tiktok-shop/">Explore TikTok Shop picks</a></div>
    <div class="trust-row"><span>AI creator disclosed</span><span>No fake reviews</span><span>Affiliate-ready</span><span>Built for short-form video</span></div>
  </div>
  <div class="hero-visual">
    <div class="studio-scene">
      <div class="mirror"></div><div class="phone"></div><div class="makeup makeup-a"></div><div class="makeup makeup-b"></div><div class="glow"></div>
      <div class="scene-caption"><strong>Maya.exe studio</strong><span>A cozy beauty-tech world, not a fake human identity.</span></div>
    </div>
  </div>
</section>
<section class="section">
  ${sectionHeader("Content engine", "Four repeatable formats", "Every format can create attention first and monetization second.")}
  <div class="card-grid">
    ${card({kicker:"AI Makeup", title:"AI picks my look", text:"Use virtual try-on, shade matching and prompt-based beauty tools as the experiment."})}
    ${card({kicker:"Beauty Tech", title:"Worth it or gimmick?", text:"Test gadgets against the job they claim to solve, not against marketing copy."})}
    ${card({kicker:"Experiments", title:"Human vs AI", text:"Compare AI suggestions with practical human judgment and explain the trade-offs."})}
    ${card({kicker:"Creator Tools", title:"How the content gets made", text:"Show the AI, editing and app-building tools behind the Maya brand."})}
  </div>
</section>
<section class="section tint">
  ${sectionHeader("TikTok Shop", "Products become content, not random listings", "Each product should earn a place through a video angle, a useful test, or a clear comparison.")}
  <div class="product-grid">${products.slice(0,4).map(productCard).join("")}</div>
  <div class="center"><a class="button secondary" href="/tiktok-shop/">Open the full TikTok Shop plan</a></div>
</section>
<section class="section">
  ${sectionHeader("Video queue", "The first Maya episodes")}
  <div class="video-grid">${videos.slice(0,4).map(([title, category, status], i) => `<article class="video-card"><div class="video-thumb"><span>${String(i+1).padStart(2,"0")}</span></div><p class="kicker">${escapeHtml(category)}</p><h3>${escapeHtml(title)}</h3><p class="status">${escapeHtml(status)}</p></article>`).join("")}</div>
</section>
<section class="section split about-strip">
  <div><p class="eyebrow">Trust architecture</p><h2>Maya looks human. The brand stays transparent.</h2></div>
  <div><p>${escapeHtml(disclosure)}</p><a class="text-link" href="/affiliate-disclosure/">Read the full disclosure →</a></div>
</section>
<section class="section">
  <div class="newsletter"><div><p class="eyebrow">Smart beauty note</p><h2>Build an audience we can actually own.</h2><p>Newsletter signup is staged for the next integration. We will connect a real provider before collecting addresses.</p></div><form onsubmit="return false"><input type="email" placeholder="Email signup coming soon" disabled><button class="button disabled" disabled>Coming soon</button></form></div>
</section>`;

const simpleGrid = (items, kicker) => `<div class="card-grid">${items.map(([title, text, tag]) => card({kicker:tag || kicker,title,text})).join("")}</div>`;

const pages = [
  { path: "/", title: "Maya.exe — Beauty, but make it smart", description: "A virtual AI beauty-tech creator exploring useful AI beauty apps, gadgets, creator tools and TikTok Shop products.", body: homeBody },
  { path: "/videos/", title: "Maya.exe videos", description: "Upcoming Maya.exe beauty-tech, AI makeup and creator-tool video formats.", body: `<section class="page-hero"><p class="eyebrow">Videos</p><h1>Content designed to earn attention before asking for a click.</h1><p class="lede">The first queue is deliberately broad enough to test AI makeup, beauty tech, experiments and creator workflows.</p></section><section class="section"><div class="video-grid">${videos.map(([title,category,status],i)=>`<article class="video-card"><div class="video-thumb"><span>${String(i+1).padStart(2,"0")}</span></div><p class="kicker">${escapeHtml(category)}</p><h3>${escapeHtml(title)}</h3><p class="status">${escapeHtml(status)}</p></article>`).join("")}</div></section>` },
  { path: "/reviews/", title: "Maya.exe reviews", description: "Transparent review framework for AI beauty apps, beauty tech and creator tools.", body: `<section class="page-hero"><p class="eyebrow">Reviews</p><h1>We only call something a review after there is something real to review.</h1><p class="lede">No fabricated tests. Until a product has been evaluated, it stays in the research or testing queue.</p></section><section class="section">${simpleGrid([["Testing queue","Products and tools waiting for a defined test method."],["Researching","Claims, terms, pricing and safety questions being checked."],["Reviewed","This state will only appear after a documented evaluation."],["Not recommended","Reserved for products where the evidence or fit does not justify promotion."]],"Review state")}</section>` },
  { path: "/ai-beauty-tools/", title: "AI beauty tools", description: "AI makeup, shade matching, beauty planning and creator-tool categories for Maya.exe.", body: `<section class="page-hero"><p class="eyebrow">AI Beauty Tools</p><h1>Software that helps with a real beauty decision.</h1><p class="lede">The category is more interesting when the tool can save time, reduce wasted purchases or improve a creator workflow.</p></section><section class="section">${simpleGrid(aiTools.map(([a,b,c])=>[a,b,c]))}</section>` },
  { path: "/beauty-tech/", title: "Beauty tech", description: "Beauty-tech product categories and test ideas for Maya.exe.", body: `<section class="page-hero"><p class="eyebrow">Beauty Tech</p><h1>Gadgets need a job, not just a futuristic look.</h1><p class="lede">Maya will judge devices by usefulness, recurring cost, app dependence, claims, return policy and whether the workflow is actually better.</p></section><section class="section"><div class="product-grid">${products.filter(p=>p.category.includes("Beauty-tech")||p.category.includes("AI-assisted")).map(productCard).join("")}</div></section>` },
  { path: "/guides/", title: "Maya.exe guides", description: "Practical beauty-tech and AI beauty guides.", body: `<section class="page-hero"><p class="eyebrow">Guides & Tips</p><h1>Useful enough to save, simple enough to use.</h1></section><section class="section">${simpleGrid(guides,"Guide")}</section>` },
  { path: "/templates/", title: "Maya.exe templates", description: "Beauty creator templates and AI prompt resources.", body: `<section class="page-hero"><p class="eyebrow">Templates</p><h1>Digital products we can eventually sell without making the audience regret the purchase.</h1><p class="lede">The first templates are marked coming soon until the actual files are produced.</p></section><section class="section">${simpleGrid(templates.map(([a,b])=>[a,b,"Coming soon"]))}</section>` },
  { path: "/deals/", title: "Maya.exe deals", description: "Verified beauty-tech and AI software deals when real offers are available.", body: `<section class="page-hero"><p class="eyebrow">Deals</p><h1>No fake countdowns. No invented discounts.</h1><p class="lede">This page stays intentionally quiet until a real offer, current price and valid outbound link are verified.</p></section><section class="section"><div class="empty-state"><strong>No verified deals yet.</strong><p>When a deal is added, the price, expiry and affiliate relationship will be stated clearly.</p></div></section>` },
  { path: "/tiktok-shop/", title: "Maya.exe TikTok Shop", description: "Affiliate-ready TikTok Shop product categories for the Maya.exe beauty-tech creator brand.", body: `<section class="page-hero"><p class="eyebrow">TikTok Shop</p><h1>Shop the products that give Maya something worth testing.</h1><p class="lede">Product links are disabled until a real TikTok Shop affiliate URL and current price are supplied. That keeps the storefront truthful while we build the content engine.</p></section><section class="section"><aside class="disclosure-box"><strong>Shop disclosure</strong><p>Future TikTok Shop links may be affiliate links, meaning the Maya.exe business can earn a commission from qualifying purchases. Recommendations are not live until the underlying listing is verified.</p></aside><div class="product-grid">${products.map(productCard).join("")}</div></section>` },
  { path: "/about/", title: "About Maya.exe", description: "Meet Maya.exe, the virtual AI beauty-tech creator and the transparent editorial model behind the brand.", body: `<section class="page-hero"><p class="eyebrow">About</p><h1>Maya is virtual. The business behind her is real.</h1><p class="lede">The goal is to build a recognizable beauty-tech media brand without pretending an AI character is a real human being.</p></section><section class="section split"><div><h2>What Maya does</h2><p>She gives the brand a consistent voice and visual identity for AI beauty, gadgets, creator tools and experiments.</p></div><div><h2>What the team does</h2><p>Humans choose what gets researched, what gets published, what counts as a test and which commercial relationships are accepted.</p></div></section>` },
  { path: "/contact/", title: "Contact Maya.exe", description: "Contact information for Maya.exe partnerships and editorial questions.", body: `<section class="page-hero"><p class="eyebrow">Contact</p><h1>Partnerships should start with a clear brief.</h1><p class="lede">A working contact inbox will be added before launch. We will separate editorial questions, sponsorships and product-test requests.</p></section><section class="section"><div class="empty-state"><strong>Contact setup pending.</strong><p>Do not publish a personal email address here. Add a dedicated Maya.exe business inbox at launch.</p></div></section>` },
  { path: "/affiliate-disclosure/", title: "Maya.exe affiliate disclosure", description: "Affiliate and virtual-creator disclosure for Maya.exe.", body: `<section class="page-hero"><p class="eyebrow">Disclosure</p><h1>Commercial relationships should be easy to see.</h1></section><section class="section article"><p>${escapeHtml(disclosure)}</p><h2>How affiliate links work</h2><p>If Maya.exe links to a merchant using an affiliate tracking link, the business may receive a commission if a qualifying purchase occurs. Affiliate links are marked and use sponsored/nofollow attributes.</p><h2>What affiliate status does not mean</h2><p>A commission does not prove a product is good, safe, effective or suitable for a particular person. Product claims and health-related claims need their own evidence.</p><h2>TikTok Shop</h2><p>TikTok Shop product links will only be activated after the listing, price and affiliate destination are verified. Placeholder products on this site are not endorsements.</p></section>` },
];

const header = () => `<header class="site-header"><a class="brand" href="/"><span class="brand-dot">M</span><span>Maya.exe</span></a><nav>${nav.map(([label,href])=>`<a href="${href}">${label}</a>`).join("")}</nav><a class="shop-pill" href="/tiktok-shop/">Shop</a></header>`;
const footer = () => `<footer class="site-footer"><div><strong>Maya.exe</strong><p>Beauty, but make it smart.</p><p class="tiny">Maya is a virtual AI creator, not a real person.</p></div><div class="footer-links"><a href="/about/">About</a><a href="/contact/">Contact</a><a href="/affiliate-disclosure/">Affiliate disclosure</a><a href="/tiktok-shop/">TikTok Shop</a></div></footer>`;

const renderPage = (page) => `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(page.title)}</title><meta name="description" content="${escapeHtml(page.description)}"><link rel="canonical" href="${siteUrl}${page.path}"><meta property="og:type" content="website"><meta property="og:title" content="${escapeHtml(page.title)}"><meta property="og:description" content="${escapeHtml(page.description)}"><meta property="og:url" content="${siteUrl}${page.path}"><meta name="theme-color" content="#f8e8e5"><link rel="stylesheet" href="/styles.css"><script type="application/ld+json">${JSON.stringify({"@context":"https://schema.org","@type":"WebSite",name:"Maya.exe",url:siteUrl,description:"Virtual AI beauty-tech creator brand."})}</script></head><body>${header()}<main>${page.body}</main>${footer()}</body></html>`;

export { pages, renderPage, siteUrl, trackingBase };
