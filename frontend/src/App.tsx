import { FormEvent, useState } from "react";

type ScoreResult = {
  product_name: string;
  score: number;
  rating: string;
};

type RankedOpportunity = {
  source: string;
  name: string;
  advertiser: string | null;
  program_url: string | null;
  tracking_url: string | null;
  commission_text: string | null;
  commission_percent: number | null;
  epc_per_click: number | null;
  cookie_days: number | null;
  recurring: boolean;
  commercial_readiness_score: number;
  confidence: number;
  reasons: string[];
};

type TopResponse = {
  keywords: string | null;
  opportunities: RankedOpportunity[];
  warnings: string[];
  scoring_note: string;
};

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function App() {
  const [product, setProduct] = useState("Example VPS");
  const [result, setResult] = useState<ScoreResult | null>(null);
  const [keyword, setKeyword] = useState("AI software");
  const [directUrls, setDirectUrls] = useState("");
  const [top, setTop] = useState<TopResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submitScore(event: FormEvent) {
    event.preventDefault();
    setError("");
    const response = await fetch(`${API}/api/v1/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_name: product,
        network: "manual",
        demand: 82,
        buyer_intent: 90,
        trend: 75,
        competition: 48,
        commission_attractiveness: 80,
        network_epc_signal: 70,
      }),
    });
    if (!response.ok) {
      setError("Could not score the opportunity. Is the backend running?");
      return;
    }
    setResult(await response.json());
  }

  async function findOpportunities(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    setTop(null);
    const urls = directUrls
      .split(/\r?\n/)
      .map((value) => value.trim())
      .filter(Boolean);

    try {
      const response = await fetch(`${API}/api/v1/opportunities/top`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          keywords: keyword || null,
          direct_urls: urls,
          include_cj: true,
          include_impact: true,
          limit: 10,
        }),
      });
      if (!response.ok) {
        setError("The opportunity search failed. Check backend logs and connector credentials.");
        return;
      }
      setTop(await response.json());
    } catch {
      setError("Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <header>
        <p className="eyebrow">Affiliate AI Agent · V0.3</p>
        <h1>Find the strongest offers before creating content.</h1>
        <p className="lede">
          Search live CJ and Impact relationships, inspect public direct affiliate pages, then rank
          offers by commercial readiness and evidence quality.
        </p>
      </header>

      <section className="panel opportunity-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Live research</p>
            <h2>Top opportunities</h2>
          </div>
          <span className="status-dot">CJ + Impact + Direct</span>
        </div>
        <form onSubmit={findOpportunities} className="research-form">
          <label>
            Market / keyword
            <input value={keyword} onChange={(event) => setKeyword(event.target.value)} />
          </label>
          <label className="full-width">
            Direct affiliate pages to inspect (optional, one URL per line)
            <textarea
              rows={4}
              value={directUrls}
              placeholder={"https://example.com/affiliates\nhttps://example.ai/partners"}
              onChange={(event) => setDirectUrls(event.target.value)}
            />
          </label>
          <button type="submit" disabled={loading}>
            {loading ? "Researching…" : "Find top opportunities"}
          </button>
        </form>

        {top && (
          <div className="opportunity-results">
            {top.warnings.length > 0 && (
              <div className="warning-box">
                {top.warnings.map((warning) => <p key={warning}>{warning}</p>)}
              </div>
            )}
            {top.opportunities.length === 0 ? (
              <p className="muted">No ranked opportunities yet. Configure a network or add direct URLs.</p>
            ) : (
              top.opportunities.map((item, index) => (
                <article className="opportunity-card" key={`${item.source}-${item.name}-${index}`}>
                  <div className="rank">#{index + 1}</div>
                  <div className="opportunity-body">
                    <div className="opportunity-title">
                      <div>
                        <span className="source">{item.source}</span>
                        <h3>{item.name}</h3>
                        {item.advertiser && <p className="muted">{item.advertiser}</p>}
                      </div>
                      <div className="score-block">
                        <strong>{item.commercial_readiness_score.toFixed(0)}</strong>
                        <small>readiness</small>
                      </div>
                    </div>
                    <div className="metrics">
                      {item.commission_percent !== null && <span>{item.commission_percent}% commission</span>}
                      {item.epc_per_click !== null && <span>EPC ≈ {item.epc_per_click.toFixed(3)}/click</span>}
                      {item.cookie_days !== null && <span>{item.cookie_days}-day cookie</span>}
                      {item.recurring && <span>recurring</span>}
                      <span>{Math.round(item.confidence * 100)}% data confidence</span>
                    </div>
                    <ul>
                      {item.reasons.slice(0, 4).map((reason) => <li key={reason}>{reason}</li>)}
                    </ul>
                  </div>
                </article>
              ))
            )}
            <p className="fine-print">{top.scoring_note}</p>
          </div>
        )}
      </section>

      <section className="panel secondary-panel">
        <h2>Manual signal scorer</h2>
        <form onSubmit={submitScore}>
          <label>
            Product or offer
            <input value={product} onChange={(event) => setProduct(event.target.value)} />
          </label>
          <button type="submit">Analyze sample signals</button>
        </form>
        {error && <p className="error">{error}</p>}
        {result && (
          <div className="result">
            <span>{result.product_name}</span>
            <strong>{result.score}/100</strong>
            <small>{result.rating.replace("_", " ")}</small>
          </div>
        )}
      </section>

      <section className="grid">
        <article><h3>Research</h3><p>Live network relationships and direct affiliate terms.</p></article>
        <article><h3>Rank</h3><p>Commercial readiness with explicit confidence and evidence.</p></article>
        <article><h3>Learn</h3><p>Next: demand, trends, clicks, conversions and real EPC feedback.</p></article>
      </section>
    </main>
  );
}
