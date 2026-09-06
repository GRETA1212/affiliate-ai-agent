import { useEffect, useState } from "react";

type Classification =
  | "winner"
  | "loser"
  | "promising"
  | "neutral"
  | "insufficient_data"
  | "inactive";

type Recommendation = {
  campaign_id: string;
  campaign_name: string;
  product_name: string;
  campaign_status: string;
  classification: Classification;
  recommended_action: string;
  priority: number;
  confidence: number;
  human_clicks: number;
  approved_conversions: number;
  pending_conversions: number;
  conversion_rate: number;
  approved_revenue_by_currency: Record<string, number>;
  epc_by_currency: Record<string, number>;
  peer_median_epc_by_currency: Record<string, number>;
  reasons: string[];
  next_actions: string[];
};

type AdvisorResponse = {
  generated_at: string;
  summary: {
    total_campaigns: number;
    winners: number;
    losers: number;
    promising: number;
    insufficient_data: number;
    action_required: number;
    leaders_by_currency: Array<{
      currency: string;
      campaign_id: string;
      campaign_name: string;
      epc: number;
    }>;
  };
  recommendations: Recommendation[];
  methodology_note: string;
};

export default function Advisor({ api }: { api: string }) {
  const [data, setData] = useState<AdvisorResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${api}/api/v1/performance/recommendations`);
      if (!response.ok) {
        setError("Could not analyze campaign performance.");
        return;
      }
      setData((await response.json()) as AdvisorResponse);
    } catch {
      setError("Performance advisor is unavailable. Check the backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel advisor-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Performance advisor</p>
          <h2>Winner / loser detection from real campaign data</h2>
        </div>
        <button type="button" onClick={() => void load()} disabled={loading}>
          {loading ? "Analyzing…" : "Refresh recommendations"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {data && (
        <>
          <div className="advisor-summary">
            <Summary label="Winners" value={data.summary.winners} />
            <Summary label="Losers" value={data.summary.losers} />
            <Summary label="Promising" value={data.summary.promising} />
            <Summary label="Need more data" value={data.summary.insufficient_data} />
            <Summary label="Action required" value={data.summary.action_required} />
          </div>

          {data.summary.leaders_by_currency.length > 0 && (
            <div className="leader-strip">
              {data.summary.leaders_by_currency.map((leader) => (
                <span key={leader.currency}>
                  {leader.currency} leader: <strong>{leader.campaign_name}</strong> · EPC {leader.epc.toFixed(3)}
                </span>
              ))}
            </div>
          )}

          <div className="recommendation-list">
            {data.recommendations.length === 0 ? (
              <p className="muted">Create a campaign and collect real clicks before analysis begins.</p>
            ) : (
              data.recommendations.map((item) => (
                <article
                  className={`recommendation-card ${item.classification}`}
                  key={item.campaign_id}
                >
                  <div className="campaign-card-head">
                    <div>
                      <span className="source">{item.classification.replace("_", " ")}</span>
                      <h3>{item.campaign_name}</h3>
                      <p className="muted">{item.product_name}</p>
                    </div>
                    <div className="advisor-action">
                      <strong>{actionLabel(item.recommended_action)}</strong>
                      <small>{Math.round(item.confidence * 100)}% confidence</small>
                    </div>
                  </div>

                  <div className="metrics">
                    <span>{item.human_clicks} human clicks</span>
                    <span>{item.approved_conversions} approved conversions</span>
                    <span>{(item.conversion_rate * 100).toFixed(2)}% CVR</span>
                    <span>Revenue {formatMoneyMap(item.approved_revenue_by_currency)}</span>
                    <span>EPC {formatMoneyMap(item.epc_by_currency)}</span>
                    {item.pending_conversions > 0 && <span>{item.pending_conversions} pending</span>}
                    <span>priority {item.priority}/5</span>
                  </div>

                  <div className="advisor-columns">
                    <div>
                      <strong>Why</strong>
                      <ul>{item.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                    </div>
                    <div>
                      <strong>Next actions</strong>
                      <ol>{item.next_actions.map((action) => <li key={action}>{action}</li>)}</ol>
                    </div>
                  </div>
                </article>
              ))
            )}
          </div>

          <p className="fine-print">{data.methodology_note}</p>
        </>
      )}
    </section>
  );
}

function Summary({ label, value }: { label: string; value: number }) {
  return (
    <div className="summary-stat">
      <small>{label}</small>
      <strong>{value}</strong>
    </div>
  );
}

function actionLabel(value: string): string {
  return value.replaceAll("_", " ");
}

function formatMoneyMap(values: Record<string, number>): string {
  const entries = Object.entries(values);
  if (entries.length === 0) return "—";
  return entries.map(([currency, value]) => `${currency} ${value.toFixed(2)}`).join(" · ");
}
