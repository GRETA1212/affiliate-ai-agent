const checked = "18 August 2026";

const horizonsPricing = "https://www.hostinger.com/horizons/pricing";
const horizonsPlans = "https://support.hostinger.com/en/articles/11136677-hostinger-horizons-plan-details";
const horizonsAffiliate = "https://www.hostinger.com/pk/horizons/affiliate-program";
const horizonsAffiliateTerms = "https://www.hostinger.com/legal/affiliate-program-agreement";

const sourceList = (items) => `
  <section class="source-box">
    <h2>Official sources checked</h2>
    <ul>${items.map(([label, url]) => `<li><a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a></li>`).join("")}</ul>
    <p class="fact-date">Last fact-check: ${checked}.</p>
  </section>
`;

const directCta = (href, label) => `<a class="button product-cta" href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>`;

const home = {
  path: "/",
  title: "AI Tool Compass — practical AI software buying guides",
  description: "Fact-checked AI software comparisons and buyer guides for app builders, AI marketing, voice tools and small-business workflows.",
  body: `
    <section class="hero">
      <div>
        <p class="eyebrow">Fact-checked AI software guides</p>
        <h1>Find the AI tool that fits the job — before you spend money.</h1>
        <p class="lede">We compare current pricing, workflow fit, limits and trade-offs using official sources. Start with our AI app-builder guides, where Hostinger Horizons and Lovable are the first focused buying decisions.</p>
        <div class="hero-actions">
          <a class="button" href="/ai-app-builders/hostinger-horizons-buyer-guide/">Read the Hostinger Horizons guide</a>
          <a class="button secondary" href="/comparisons/lovable-vs-hostinger-horizons/">Compare Lovable vs Horizons</a>
        </div>
      </div>
      <aside class="hero-card">
        <p class="kicker">What we check before recommending</p>
        <ul class="check-list">
          <li>Current plan price and renewal language</li>
          <li>Free trial or free starting point</li>
          <li>Hosting, code and deployment control</li>
          <li>Limits that matter after the first demo</li>
          <li>Commercial relationships disclosed clearly</li>
        </ul>
      </aside>
    </section>

    <section class="section">
      <div class="section-heading"><p class="eyebrow">Start with a buying decision</p><h2>Our first money-intent guides</h2></div>
      <div class="card-grid">
        <article class="card"><p class="kicker">AI app builder</p><h3>Hostinger Horizons buyer guide</h3><p>Current free tier, paid plans, hosting, AI-credit limits, selling features and who should shortlist it.</p><a class="text-link" href="/ai-app-builders/hostinger-horizons-buyer-guide/">Read guide →</a></article>
        <article class="card"><p class="kicker">Comparison</p><h3>Lovable vs Hostinger Horizons</h3><p>Choose between a builder-first workflow and an all-in-one hosting/app-building workflow.</p><a class="text-link" href="/comparisons/lovable-vs-hostinger-horizons/">Read comparison →</a></article>
        <article class="card"><p class="kicker">Small business</p><h3>Best AI tools by job</h3><p>Pick a tool because it solves a measurable job — not because it has the loudest AI marketing.</p><a class="text-link" href="/best-ai-tools/small-business-2026/">Read shortlist →</a></article>
      </div>
    </section>

    <section class="section split">
      <div><p class="eyebrow">Commercial transparency</p><h2>Useful first. Affiliate second.</h2></div>
      <div><p>We may earn a commission from some links after affiliate approval. Until then, product buttons use direct official links. Affiliate economics never count as evidence that a product is better.</p><p>We do not invent testing, testimonials, traffic or earnings. Pricing and commercial terms are re-checked before a page is promoted heavily.</p></div>
    </section>
  `,
};

const hostingerBuyerGuide = {
  path: "/ai-app-builders/hostinger-horizons-buyer-guide/",
  title: "Hostinger Horizons buyer guide 2026: pricing, strengths and limits",
  description: "A fact-checked Hostinger Horizons buyer guide covering its free tier, current paid plans, hosting, AI credits, selling features, code editing and practical fit.",
  body: `
    <section class="article-hero commercial-hero">
      <p class="eyebrow">AI app builder buyer guide</p>
      <h1>Hostinger Horizons in 2026: an AI app builder built around getting a project live</h1>
      <p class="lede">Horizons combines AI-assisted web-app building with hosting and, on higher plans, features for subscriptions, products, analytics, collaboration and deeper code control. Its strongest fit is someone who wants fewer separate tools between idea and launch.</p>
      <p class="fact-date">Fact-checked against official Hostinger sources · ${checked}</p>
    </section>

    <aside class="commercial-disclosure"><strong>Commercial disclosure</strong><p>This page currently uses direct Hostinger links. If an approved affiliate link is added later, it will be clearly disclosed and marked sponsored. Pricing and affiliate terms can change.</p></aside>

    <article class="article-body commercial-article">
      <section><h2>Quick verdict</h2><p><strong>Shortlist Hostinger Horizons</strong> if you want to build and publish a web app without assembling hosting, deployment and basic business tooling yourself. It is especially interesting for MVPs, internal tools, simple SaaS ideas, booking flows and small commerce projects.</p><p><strong>Look elsewhere or test carefully</strong> if your project needs unusual infrastructure, strict regulatory controls or complete architecture freedom from day one.</p></section>

      <section><h2>Current starting point</h2><p>Hostinger currently offers a free option with 5 AI credits, no credit card requirement and one website for testing. The free tier does not include free hosting, a domain or a mailbox, so it is best treated as a product evaluation path rather than a production plan.</p></section>

      <section><h2>Current US plan examples</h2><p>On Hostinger's current US pricing page, Explorer is listed at <strong>$6.99/month on a 12-month purchase</strong> with 30 AI credits per month, Starter at <strong>$13.99/month</strong> with 70 AI credits per month, and Hobbyist at <strong>$39.99/month</strong> with 200 AI credits per month. These are current promotional page values and should be re-checked at checkout.</p><p>Starter currently adds capabilities such as up to 25 websites, subscription selling, physical/digital product selling, analytics, image/voice prompting, project collaboration and AI features such as chatbots. Hobbyist increases project capacity and adds a code editor.</p></section>

      <section><h2>What makes Horizons different</h2><ul><li><strong>Integrated launch path:</strong> paid plans bundle hosting.</li><li><strong>Business features:</strong> higher plans include selling subscriptions and products.</li><li><strong>Built-in project capabilities:</strong> user accounts, logins and data storage are part of the current Explorer feature set.</li><li><strong>SEO and AI discoverability:</strong> current plan pages include SEO-optimized projects and getting found by AI tools.</li><li><strong>More control on higher tiers:</strong> Hobbyist includes code editing and project duplication/templates.</li></ul></section>

      <section><h2>What to test before paying for a year</h2><ol><li>Build a small app with login, data storage and one form.</li><li>Add one external integration or payment-related workflow if your idea needs it.</li><li>Measure how many AI credits the first usable version consumes.</li><li>Make an intentional bad change and test version recovery.</li><li>Publish the project and confirm what is included in the plan you intend to buy.</li></ol></section>

      <section><h2>Affiliate transparency</h2><p>Hostinger currently advertises up to 60% commission on eligible Horizons purchases for approved affiliates. Its affiliate agreement says Horizons commission applies to the initial purchase and that specific offers can vary. That is relevant to how this site may eventually be compensated, but it is <strong>not</strong> part of the product-quality score.</p></section>

      <section><h2>Bottom line</h2><p>Horizons is compelling when the main goal is to move from idea to a hosted working app with as little platform assembly as possible. The most important buyer question is not whether the first prompt looks impressive; it is whether the credit usage, correction workflow and included hosting/business features still make sense after you build a realistic version of your project.</p><div class="cta-row">${directCta(horizonsPricing, "Check Hostinger Horizons current plans")}</div></section>

      ${sourceList([
        ["Hostinger Horizons pricing", horizonsPricing],
        ["Hostinger Horizons plan details", horizonsPlans],
        ["Hostinger Horizons affiliate program", horizonsAffiliate],
        ["Hostinger affiliate program agreement", horizonsAffiliateTerms],
      ])}
    </article>
  `,
};

const appBuildersLaunchIndex = {
  path: "/ai-app-builders/",
  title: "AI app builders in 2026: Hostinger Horizons, Lovable and practical comparisons",
  description: "Fact-checked AI app-builder buyer guides covering Hostinger Horizons, Lovable, hosting, code control, pricing and practical fit.",
  body: `
    <section class="article-hero"><p class="eyebrow">AI app builders</p><h1>Choose the builder by what happens after the first prompt.</h1><p class="lede">We focus on hosting, code control, data, recovery, cost and whether the finished app is maintainable enough for the job.</p></section>
    <section class="section"><div class="card-grid">
      <article class="card"><p class="kicker">Priority guide</p><h3>Hostinger Horizons buyer guide</h3><p>Current free tier, paid pricing, hosting, AI credits, selling features and practical fit.</p><a class="text-link" href="/ai-app-builders/hostinger-horizons-buyer-guide/">Read buyer guide →</a></article>
      <article class="card"><p class="kicker">Comparison</p><h3>Lovable vs Hostinger Horizons</h3><p>Compare ownership, workflow, hosting and the type of project each platform suits.</p><a class="text-link" href="/comparisons/lovable-vs-hostinger-horizons/">Read comparison →</a></article>
      <article class="card"><p class="kicker">Lovable</p><h3>Lovable buyer guide</h3><p>Credits, code ownership, team workspaces and workload-based usage.</p><a class="text-link" href="/ai-app-builders/lovable-buyer-guide/">Read guide →</a></article>
    </div></section>
  `,
};

export const launchPages = [home, hostingerBuyerGuide, appBuildersLaunchIndex];
