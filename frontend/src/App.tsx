import { FormEvent, useState } from "react";

type ScoreResult = {
  product_name: string;
  score: number;
  rating: string;
};

type CJLink = {
  advertiser_id: string | null;
  advertiser_name: string | null;
  link_id: string | null;
  link_name: string | null;
  category: string | null;
  sale_commission: string | null;
  seven_day_epc_per_100_clicks: number | null;
  three_month_epc_per_100_clicks: number | null;
  relationship_status: string | null;
};

type CJSearchResult = {
  total_matched: number;
  records_returned: number;
  page_number: number;
  links: CJLink[];
};

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function App() {
  const [product, setProduct] = useState("Example VPS");
  const [result, setResult] = useState<ScoreResult | null>(null);
  const [error, setError] = useState("");
  const [cjKeyword, setCjKeyword] = useState("vps");
  const [cjResult, setCjResult] = useState<CJSearchResult | null>(null);
  const [cjError, setCjError] = useState("");
  const [cjLoading, setCjLoading] = useState(false);

  async function submit(event: FormEvent) {
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

  async function searchCJ(event: FormEvent) {
    event.preventDefault();
    setCjError("");
    setCjLoading(true);
    setCjResult(null);

    const params = new URLSearchParams({
      advertiser_ids: "joined",
      records_per_page: "10",
    });
    if (cjKeyword.trim()) {
      params.set("keywords", cjKeyword.trim());
    }

    try {
      const response = await fetch(`${API}/api/v1/cj/links?${params.toString()}`);
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { detail?: string } | null;
        setCjError(body?.detail || "CJ search failed.");
        return;
      }
      setCjResult(await response.json());
    } catch {
      setCjError("Could not reach the backend.");
    } finally {
      setCjLoading(false);
    }
  }

  return (
    <main>
      <header>
        <p className="eyebrow">Affiliate AI Agent · MVP</p>
        <h1>Find opportunities before creating content.</h1>
        <p className="lede">
          Score demand, buyer intent, trend, competition, commission quality and EPC signals.
        </p>
      </header>

      <section className="panel">
        <h2>Live CJ research</h2>
        <p className="subtle">
          Search links from advertisers joined to your CJ publisher account. EPC is shown per 100
          clicks, matching CJ reporting.
        </p>
        <form onSubmit={searchCJ}>
          <label>
            Keyword
            <input value={cjKeyword} onChange={(event) => setCjKeyword(event.target.value)} />
          </label>
          <button type="submit" disabled={cjLoading}>
            {cjLoading ? "Searching…" : "Search CJ"}
          </button>
        </form>
        {cjError && <p className="error">{cjError}</p>}
        {cjResult && (
          <div className="cj-results">
            <p className="subtle">
              {cjResult.total_matched} matches · showing {cjResult.records_returned}
            </p>
            <div className="cj-list">
              {cjResult.links.map((link) => (
                <article className="cj-row" key={`${link.advertiser_id}-${link.link_id}`}>
                  <div>
                    <strong>{link.link_name || link.advertiser_name || "Unnamed CJ link"}</strong>
                    <p>
                      {link.advertiser_name || "Unknown advertiser"}
                      {link.category ? ` · ${link.category}` : ""}
                    </p>
                  </div>
                  <div className="metrics">
                    <span>
                      <small>Commission</small>
                      <strong>{link.sale_commission || "—"}</strong>
                    </span>
                    <span>
                      <small>7-day EPC</small>
                      <strong>
                        {link.seven_day_epc_per_100_clicks === null
                          ? "—"
                          : `$${link.seven_day_epc_per_100_clicks.toFixed(2)}`}
                      </strong>
                    </span>
                    <span>
                      <small>3-month EPC</small>
                      <strong>
                        {link.three_month_epc_per_100_clicks === null
                          ? "—"
                          : `$${link.three_month_epc_per_100_clicks.toFixed(2)}`}
                      </strong>
                    </span>
                  </div>
                </article>
              ))}
            </div>
          </div>
        )}
      </section>

      <section className="panel spaced">
        <h2>Opportunity scorer</h2>
        <form onSubmit={submit}>
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
        <article>
          <h3>Research</h3>
          <p>CJ is live; Impact, Google Ads and YouTube are the next data connectors.</p>
        </article>
        <article>
          <h3>Forecast</h3>
          <p>Estimate clicks, conversions, revenue and EPC before investing time.</p>
        </article>
        <article>
          <h3>Create</h3>
          <p>Generate help-first campaign angles with clear affiliate disclosure.</p>
        </article>
      </section>
    </main>
  );
}
