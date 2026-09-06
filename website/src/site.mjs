const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

export const siteName = process.env.SITE_NAME || "AI Tool Compass";
export const siteUrl = (process.env.SITE_URL || "https://example.invalid").replace(/\/$/, "");
export const contactEmail = process.env.CONTACT_EMAIL || "hello@example.invalid";

export const navigation = [
  ["/best-ai-tools/", "Best AI Tools"],
  ["/ai-app-builders/", "App Builders"],
  ["/ai-voice/", "AI Voice"],
  ["/ai-marketing/", "AI Marketing"],
  ["/comparisons/", "Comparisons"],
  ["/tutorials/", "Tutorials"],
];

const cards = (items) => `
  <div class="card-grid">
    ${items.map((item) => `
      <article class="card">
        <p class="kicker">${escapeHtml(item.kicker)}</p>
        <h3>${escapeHtml(item.title)}</h3>
        <p>${escapeHtml(item.text)}</p>
        <a class="text-link" href="${item.href}">${escapeHtml(item.cta || "Read guide")} →</a>
      </article>
    `).join("")}
  </div>
`;

const article = ({eyebrow, title, dek, sections, note}) => `
  <section class="article-hero">
    <p class="eyebrow">${escapeHtml(eyebrow)}</p>
    <h1>${escapeHtml(title)}</h1>
    <p class="lede">${escapeHtml(dek)}</p>
  </section>
  <article class="article-body">
    ${sections.map((section) => `
      <section>
        <h2>${escapeHtml(section.heading)}</h2>
        ${section.paragraphs.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}
        ${section.points ? `<ul>${section.points.map((point) => `<li>${escapeHtml(point)}</li>`).join("")}</ul>` : ""}
      </section>
    `).join("")}
    ${note ? `<aside class="editorial-note"><strong>Editorial note:</strong> ${escapeHtml(note)}</aside>` : ""}
  </article>
`;

export const pages = [
  {
    path: "/",
    title: "Practical AI tool guides for creators and small businesses",
    description: "Independent, practical guides to AI tools for app building, voice, marketing and business workflows.",
    body: `
      <section class="hero">
        <div>
          <p class="eyebrow">Independent AI software research</p>
          <h1>Choose AI tools by the work they actually help you do.</h1>
          <p class="lede">Clear comparisons, beginner-friendly tutorials and buyer-focused checklists for creators, founders and small businesses.</p>
          <div class="hero-actions">
            <a class="button" href="/best-ai-tools/">Explore the best AI tools</a>
            <a class="button secondary" href="/about/">How we evaluate tools</a>
          </div>
        </div>
        <aside class="hero-card">
          <p class="kicker">What we score</p>
          <ul class="check-list">
            <li>Problem fit and ease of use</li>
            <li>Pricing clarity and limitations</li>
            <li>Realistic strengths and trade-offs</li>
            <li>Alternatives for different budgets</li>
            <li>Affiliate relationships disclosed clearly</li>
          </ul>
        </aside>
      </section>
      <section class="section">
        <div class="section-heading"><p class="eyebrow">Start here</p><h2>Find the right category</h2></div>
        ${cards([
          {kicker:"Build", title:"AI app builders", text:"Compare no-code and AI-assisted tools for prototypes, internal tools and customer-facing apps.", href:"/ai-app-builders/"},
          {kicker:"Create", title:"AI voice tools", text:"Understand voice generation, editing, licensing questions and workflow fit for video and audio creators.", href:"/ai-voice/"},
          {kicker:"Grow", title:"AI marketing tools", text:"Evaluate research, content, SEO and workflow tools without assuming automation automatically means better marketing.", href:"/ai-marketing/"},
        ])}
      </section>
      <section class="section split">
        <div><p class="eyebrow">Our approach</p><h2>Helpful first, affiliate second.</h2></div>
        <div><p>We do not publish fake testimonials or pretend we personally tested something when we did not. Guides separate verified facts, practical evaluation criteria and editorial judgment.</p><p>If a page contains an affiliate link, it is disclosed. A commission does not change the price you pay, and it does not guarantee a product will be recommended.</p></div>
      </section>
    `,
  },
  {
    path: "/best-ai-tools/",
    title: "Best AI tools for small businesses and creators",
    description: "A practical framework for choosing AI tools by job, budget, workflow fit and risk rather than hype.",
    body: article({
      eyebrow: "Buyer guide",
      title: "Best AI tools: start with the job, not the hype",
      dek: "The useful question is not “Which AI tool is best?” It is “Which tool solves this specific job with the least friction and acceptable cost?”",
      sections: [
        {heading:"1. Define the job", paragraphs:["Start with one repeatable task: drafting product descriptions, building a prototype, creating voiceovers, researching keywords or summarizing customer feedback. A narrow job makes comparison possible."], points:["What input does the tool need?","What output must be good enough to use?","How often will you use it?","What would failure cost you?"]},
        {heading:"2. Compare total workflow cost", paragraphs:["Subscription price is only part of the cost. Count setup time, editing time, integrations, export limits and the cost of switching later. A cheaper tool can be expensive if every output needs heavy correction."]},
        {heading:"3. Check control and portability", paragraphs:["Prefer tools that let you export your work, understand usage rights and avoid locking critical business data into a workflow you cannot leave."], points:["Export formats","Commercial-use terms","Team access","API or integration options","Data retention and privacy controls"]},
        {heading:"4. Use a short paid test", paragraphs:["Before committing to an annual plan, run a small real-world test. Use the same task across two or three tools and compare time saved, output quality and required corrections."]},
      ],
      note:"Specific product rankings will only be added when the supporting evidence is current and the comparison criteria are explicit.",
    }),
  },
  {
    path: "/ai-app-builders/",
    title: "AI app builders: what to compare before choosing one",
    description: "A beginner-friendly guide to comparing AI app builders for prototypes, internal tools and production apps.",
    body: article({
      eyebrow: "Category guide",
      title: "AI app builders: prototype fast without losing control",
      dek: "AI app builders can shorten the path from idea to working software, but the right choice depends on how much code ownership, backend control and deployment flexibility you need.",
      sections: [
        {heading:"Who they are best for", paragraphs:["They are especially useful for founders validating an idea, small teams building internal tools and non-specialists who want a working prototype before hiring a full engineering team."]},
        {heading:"What to compare", paragraphs:["Do not compare only the first demo. Compare what happens after the app becomes more complex."], points:["Can you export or own the generated code?","How are database and authentication handled?","Can you connect an external API?","What happens when the AI makes a bad change?","How easy is deployment and rollback?","How does pricing grow with usage?"]},
        {heading:"A practical test", paragraphs:["Ask each tool to build the same small application: login, one database table, a form, a dashboard and one external API call. Then measure how many manual fixes are needed and whether you understand the resulting project well enough to maintain it."]},
        {heading:"When not to use one", paragraphs:["For regulated workflows, security-sensitive systems or products with unusual infrastructure requirements, an AI builder may still help prototype the interface, but production architecture needs deeper engineering review."]},
      ],
      note:"We will add named product comparisons after checking current pricing, export rules and affiliate terms from official sources.",
    }),
  },
  {
    path: "/ai-voice/",
    title: "AI voice tools: a practical buyer guide",
    description: "How to compare AI voice tools for narration, podcasts, short-form video and multilingual content.",
    body: article({
      eyebrow: "Category guide",
      title: "AI voice tools: quality matters, but rights and workflow matter too",
      dek: "Natural speech is only one part of the decision. Editing speed, language support, licensing, consent and predictable pricing can matter just as much.",
      sections: [
        {heading:"Choose the use case first", paragraphs:["A creator producing ten short videos a week has different needs from a company generating multilingual training audio. Define length, language, turnaround time and whether the voice must remain consistent across months."]},
        {heading:"Evaluate more than realism", paragraphs:["Listen for pronunciation, pacing and emotional control, but also check whether you can correct a single sentence without regenerating the entire project."], points:["Voice consistency","Pronunciation controls","Editing workflow","Language coverage","Commercial-use terms","Consent requirements for cloning","Monthly character or minute limits"]},
        {heading:"Run a blind listening test", paragraphs:["Generate the same 30–60 second script in two or three tools. Ask several people which version is easiest to understand and least distracting. Record how long each version took to fix."]},
        {heading:"Use ethical voice practices", paragraphs:["Do not clone a person's voice without appropriate permission. For branded or commercial projects, keep records of the rights you have to use the selected voice and review the provider's current terms."]},
      ],
      note:"Any future affiliate recommendation will disclose the relationship and will not rely on fabricated personal experience.",
    }),
  },
  {
    path: "/ai-marketing/",
    title: "AI marketing tools: what actually saves time",
    description: "A framework for comparing AI marketing, SEO, content and research tools using measurable workflow outcomes.",
    body: article({
      eyebrow: "Category guide",
      title: "AI marketing tools: automate the repetitive parts, not the judgment",
      dek: "The strongest use cases reduce research, drafting and reporting time while keeping a human responsible for positioning, evidence and final claims.",
      sections: [
        {heading:"Useful marketing jobs for AI", paragraphs:["AI can help cluster research, summarize customer language, draft variants, repurpose content and surface patterns in campaign data. These jobs are easier to evaluate than vague promises to “do all your marketing.”"]},
        {heading:"Metrics to track", paragraphs:["Measure whether the tool improves the workflow, not whether the interface looks impressive."], points:["Hours saved per week","Editing time per asset","Qualified traffic","Conversion rate","Cost per useful output","Error or correction rate"]},
        {heading:"Avoid low-value automation", paragraphs:["Publishing large volumes of generic content can create more review work and weaker trust. A smaller number of useful pages built around real questions is usually a better foundation for an affiliate site than mass-generated pages."]},
        {heading:"Keep claims verifiable", paragraphs:["Product comparisons should separate official facts from editorial judgment. Pricing, feature availability and affiliate terms change, so commercial claims should be checked before publication."]},
      ],
      note:"This site is designed to connect later to our internal campaign tracker so recommendations can be informed by actual click and conversion data without exposing private analytics publicly.",
    }),
  },
  {
    path: "/comparisons/",
    title: "AI tool comparisons",
    description: "Transparent comparison methodology for AI software, with clear criteria, trade-offs and disclosure standards.",
    body: `
      <section class="article-hero"><p class="eyebrow">Comparisons</p><h1>Side-by-side guides built around a real buying decision.</h1><p class="lede">Every comparison should answer who each product is for, where each one is weaker and what evidence supports the conclusion.</p></section>
      <section class="section">
        ${cards([
          {kicker:"Method", title:"How we compare AI tools", text:"We use the same task, the same decision criteria and clearly separate verified facts from editorial judgment.", href:"/about/", cta:"See methodology"},
          {kicker:"Coming next", title:"AI app builder comparison", text:"A structured comparison covering code ownership, backend control, deployment, pricing and beginner usability.", href:"/ai-app-builders/", cta:"Read the category guide"},
          {kicker:"Coming next", title:"AI voice comparison", text:"A structured test for voice quality, editing workflow, rights, language coverage and pricing.", href:"/ai-voice/", cta:"Read the category guide"},
        ])}
      </section>
    `,
  },
  {
    path: "/tutorials/",
    title: "AI tutorials for practical business workflows",
    description: "Beginner-friendly tutorials for evaluating and using AI tools in real creator and small-business workflows.",
    body: `
      <section class="article-hero"><p class="eyebrow">Tutorials</p><h1>Practical workflows before product pitches.</h1><p class="lede">Tutorials start with a problem, explain the process and mention tools only where they are relevant.</p></section>
      <section class="section">
        ${cards([
          {kicker:"Workflow", title:"How to test an AI tool before paying annually", text:"Build a short benchmark task, record time saved, correction effort and export limitations, then compare two alternatives.", href:"/best-ai-tools/"},
          {kicker:"Workflow", title:"How to evaluate an AI voice generator", text:"Use a fixed script, blind listening, correction time and licensing checks instead of judging only a polished demo.", href:"/ai-voice/"},
          {kicker:"Workflow", title:"How to validate an AI-built app", text:"Test authentication, data storage, error handling, exportability and deployment before treating a prototype as production-ready.", href:"/ai-app-builders/"},
        ])}
      </section>
    `,
  },
  {
    path: "/about/",
    title: "About and editorial methodology",
    description: "How AI Tool Compass evaluates software, handles affiliate relationships and keeps recommendations evidence-based.",
    body: article({
      eyebrow: "About",
      title: "Our editorial methodology",
      dek: "This site is being built to help readers make practical AI software decisions while keeping affiliate incentives visible and separate from the evaluation process.",
      sections: [
        {heading:"What we publish", paragraphs:["We focus on buyer guides, comparisons and tutorials for AI tools used by creators, founders and small businesses."]},
        {heading:"How we evaluate", paragraphs:["We define the job first, compare products against the same criteria and prefer official documentation for pricing, product capabilities and commercial terms."], points:["Problem fit","Ease of use","Output quality","Control and exportability","Pricing clarity","Support and integrations","Rights, privacy and operational risk"]},
        {heading:"How affiliate relationships work", paragraphs:["Some links may become affiliate links. If a reader purchases through one, the site may receive a commission. That relationship is disclosed and does not guarantee a recommendation."]},
        {heading:"What we do not do", paragraphs:["We do not fabricate testimonials, fake hands-on experience, fake clicks or conversions, or hide paid relationships. If evidence is incomplete, the page should say so."]},
      ],
    }),
  },
  {
    path: "/contact/",
    title: "Contact",
    description: "Contact the editorial team behind AI Tool Compass.",
    body: `
      <section class="article-hero"><p class="eyebrow">Contact</p><h1>Contact the editorial team</h1><p class="lede">Questions, corrections and product information are welcome.</p></section>
      <section class="narrow-card"><h2>Email</h2><p><a href="mailto:${escapeHtml(contactEmail)}">${escapeHtml(contactEmail)}</a></p><p class="muted">Product submissions do not guarantee coverage or a positive recommendation. Please disclose any commercial relationship in your message.</p></section>
    `,
  },
  {
    path: "/affiliate-disclosure/",
    title: "Affiliate disclosure",
    description: "Affiliate relationship disclosure for AI Tool Compass.",
    body: article({
      eyebrow: "Legal",
      title: "Affiliate disclosure",
      dek: "Transparency matters when recommendations can generate revenue.",
      sections: [
        {heading:"How affiliate links work", paragraphs:["Some links on this site may be affiliate links. If you click one and make a qualifying purchase, the site may receive a commission from the merchant or affiliate network. This generally does not increase the price you pay."]},
        {heading:"Editorial independence", paragraphs:["Compensation does not guarantee inclusion, a positive review or a specific ranking. We aim to explain material trade-offs and disclose when information is based on official product documentation rather than hands-on testing."]},
        {heading:"Your responsibility", paragraphs:["Products, prices and terms change. Review the provider's current terms, pricing and suitability before purchasing or relying on a tool for important work."]},
      ],
    }),
  },
  {
    path: "/privacy/",
    title: "Privacy policy",
    description: "Privacy policy for the public AI Tool Compass website.",
    body: article({
      eyebrow: "Legal",
      title: "Privacy policy",
      dek: "This starter policy describes the minimal-data design of the public site and must be reviewed before production launch for the final hosting, analytics and jurisdiction.",
      sections: [
        {heading:"Information you provide", paragraphs:["If you contact us, we may receive the information you choose to include in your message, such as your email address and question."]},
        {heading:"Technical and analytics data", paragraphs:["The production site may use hosting logs or privacy-conscious analytics to understand aggregate traffic. The exact providers will be listed here before launch if they are enabled."]},
        {heading:"Affiliate tracking", paragraphs:["Affiliate networks may use cookies or similar attribution technologies after you click an affiliate link. Their privacy practices are governed by their own policies and the applicable consent requirements."]},
        {heading:"Data minimization", paragraphs:["Our internal campaign tracker is designed not to store raw visitor IP addresses. Public-site analytics should also be configured to collect only what is needed for legitimate measurement and security."]},
        {heading:"Contact", paragraphs:[`Questions about this policy can be sent to ${contactEmail}.`]},
      ],
      note:"This is a launch-ready structure, not jurisdiction-specific legal advice. It should be reviewed once the final domain, hosting, analytics and target markets are known.",
    }),
  },
  {
    path: "/terms/",
    title: "Terms of use",
    description: "Terms of use for AI Tool Compass.",
    body: article({
      eyebrow: "Legal",
      title: "Terms of use",
      dek: "These terms set basic expectations for using the informational content on this site.",
      sections: [
        {heading:"Informational content", paragraphs:["Content is provided for general informational purposes. It is not a guarantee that a particular product will meet your needs or produce financial results."]},
        {heading:"No earnings guarantee", paragraphs:["Affiliate marketing results depend on traffic quality, audience fit, program rules, conversion rates and many factors outside this site's control. Examples and forecasts are not guarantees of income."]},
        {heading:"Third-party products", paragraphs:["Third-party software, pricing, availability and terms can change without notice. Your purchase and use of a third-party product are governed by that provider's terms."]},
        {heading:"Acceptable use", paragraphs:["Do not misuse the site, attempt unauthorized access or interfere with its operation. Automated abuse, fake clicks and fraudulent affiliate activity are not permitted."]},
      ],
      note:"These starter terms should be reviewed for the final operating entity and jurisdiction before commercial launch.",
    }),
  },
];

export function renderPage(page) {
  const canonical = `${siteUrl}${page.path}`;
  const nav = navigation.map(([href, label]) => `<a href="${href}">${escapeHtml(label)}</a>`).join("");
  const jsonLd = JSON.stringify({
    "@context": "https://schema.org",
    "@type": page.path === "/" ? "WebSite" : "WebPage",
    name: page.title,
    description: page.description,
    url: canonical,
    isPartOf: {"@type":"WebSite", name:siteName, url:`${siteUrl}/`},
  }).replaceAll("<", "\\u003c");

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(page.title)} | ${escapeHtml(siteName)}</title>
  <meta name="description" content="${escapeHtml(page.description)}">
  <link rel="canonical" href="${canonical}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="${escapeHtml(page.title)}">
  <meta property="og:description" content="${escapeHtml(page.description)}">
  <meta property="og:url" content="${canonical}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="stylesheet" href="/styles.css">
  <script type="application/ld+json">${jsonLd}</script>
</head>
<body>
  <header class="site-header">
    <a class="brand" href="/">${escapeHtml(siteName)}</a>
    <nav aria-label="Primary navigation">${nav}</nav>
  </header>
  <main>${page.body}</main>
  <footer class="site-footer">
    <div><strong>${escapeHtml(siteName)}</strong><p>Practical AI software guides for real work.</p></div>
    <div class="footer-links">
      <a href="/about/">About</a>
      <a href="/contact/">Contact</a>
      <a href="/affiliate-disclosure/">Affiliate disclosure</a>
      <a href="/privacy/">Privacy</a>
      <a href="/terms/">Terms</a>
    </div>
    <p class="footer-note">Some links may be affiliate links. We may earn a commission from qualifying purchases. No earnings or product-performance result is guaranteed.</p>
  </footer>
</body>
</html>`;
}
