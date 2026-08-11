import { FormEvent, useState } from "react";

import Advisor from "./Advisor";
import Workspace, { WorkspaceSeed } from "./Workspace";

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
  network_hint: string | null;
  commission_text: string | null;
  commission_percent: number | null;
  fixed_payout_amount: number | null;
  fixed_payout_currency: string | null;
  epc_per_click: number | null;
  cookie_days: number | null;
  recurring: boolean;
  verified_at: string | null;
  commercial_readiness_score: number;
  opportunity_score: number;
  market_interest_score: number | null;
  market_competition_score: number | null;
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
  const [workspaceSeed, setWorkspaceSeed] = useState<WorkspaceSeed | null>(null);
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
          include_verified_catalog: true,
          enrich_impact_terms: true,
          include_youtube: true,
          youtube_probe_count: 3,
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

  function startCampaign(item: RankedOpportunity) {
    setWorkspaceSeed({
      name: `${item.name} campaign`,
      productName: item.name,
      affiliateUrl: item.tracking_url || "",
      source: item.source,
      opportunityScore: item.opportunity_score,
    });
    document.getElementById("campaign-workspace")?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <main>
      <header>
        <p className="eyebrow">Affiliate AI Agent · V0.7</p>
        <h1>Find offers, measure real revenue, and detect which campaigns deserve more traffic.</h1>
        <p className="lede">
          Research affiliate opportunities, track clicks, sync CJ and Impact commissions, then use
          your own conversion rate and EPC to identify winners, losers, and campaigns that still
          need more data.
        </p>
      </header>

      <section className="panel opportunity-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Opportunity engine</p>
            <h2>Top opportunities</h2>
          </div>
          <span className="status-dot">Verified + CJ + Impact + YouTube</span>
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

        {error && <p className="error">{error}</p>}

        {top && (
          <div className="opportunity-results">
            {top.warnings.length > 0 && (
              <div className="warning-box">
                {top.warnings.map((warning) => <p key={warning}>{warning}</p>)}
              </div>
            )}
            {top.opportunities.length === 0 ? (
              <p className="muted">No ranked opportunities matched this market.</p>
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
                        <strong>{item.opportunity_score.toFixed(0)}</strong>
                        <small>opportunity</small>
                      </div>
                    </div>
                    <div className="metrics">
                      <span>{item.commercial_readiness_score.toFixed(0)} commercial</span>
                      {item.commission_percent !== null && <span>{item.commission_percent}% commission</span>}
                      {item.fixed_payout_amount !== null && (
                        <span>
                          {item.fixed_payout_currency ? `${item.fixed_payout_currency} ` : ""}
                          {item.fixed_payout_amount} fixed payout
                        </span>
                      )}
                      {item.epc_per_click !== null && <span>EPC ≈ {item.epc_per_click.toFixed(3)}/click</span>}
                      {item.cookie_days !== null && <span>{item.cookie_days}-day attribution</span>}
                      {item.recurring && <span>recurring</span>}
                      {item.market_interest_score !== null && <span>YouTube interest {item.market_interest_score.toFixed(0)}/100</span>}
                      {item.market_competition_score !== null && <span>YouTube competition {item.market_competition_score.toFixed(0)}/100</span>}
                      {item.network_hint && <span>{item.network_hint}</span>}
                      {item.verified_at && <span>verified {item.verified_at}</span>}
                      <span>{Math.round(item.confidence * 100)}% data confidence</span>
                    </div>
                    {item.commission_text && <p className="commission-text">{item.commission_text}</p>}
                    <ul>
                      {item.reasons.slice(0, 5).map((reason) => <li key={reason}>{reason}</li>)}
                    </ul>
                    <div className="links">
                      {item.tracking_url && <a href={item.tracking_url}>Network tracking link</a>}
                      {item.program_url && <a href={item.program_url}>Program page</a>}
                      <button type="button" className="small-button" onClick={() => startCampaign(item)}>
                        Start campaign
                      </button>
                    </div>
                  </div>
                </article>
              ))
            )}
            <p className="fine-print">{top.scoring_note}</p>
          </div>
        )}
      </section>

      <div id="campaign-workspace">
        <Workspace api={API} seed={workspaceSeed} />
      </div>

      <Advisor api={API} />

      <section className="panel secondary-panel">
        <h2>Manual signal scorer</h2>
        <form onSubmit={submitScore}>
          <label>
            Product or offer
            <input value={product} onChange={(event) => setProduct(event.target.value)} />
          </label>
          <button type="submit">Analyze sample signals</button>
        </form>
        {result && (
          <div className="result">
            <span>{result.product_name}</span>
            <strong>{result.score}/100</strong>
            <small>{result.rating.replace("_", " ")}</small>
          </div>
        )}
      </section>

      <section className="grid">
        <article><h3>Research</h3><p>Verified programs plus live network and direct-source evidence.</p></article>
        <article><h3>Track</h3><p>Campaign slugs and network sync produce your own performance history.</p></article>
        <article><h3>Decide</h3><p>Winner/loser rules compare real EPC only within the same currency and wait for enough clicks.</p></article>
      </section>
    </main>
  );
}
