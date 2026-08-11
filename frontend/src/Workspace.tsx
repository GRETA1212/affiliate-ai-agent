import { FormEvent, useEffect, useState } from "react";

export type WorkspaceSeed = {
  name: string;
  productName: string;
  affiliateUrl: string;
  source: string;
  opportunityScore: number;
};

type Campaign = {
  id: string;
  name: string;
  product_name: string;
  affiliate_url: string;
  slug: string;
  status: "draft" | "active" | "paused" | "archived";
  source: string | null;
  opportunity_score: number | null;
};

type Metrics = {
  human_clicks: number;
  bot_clicks: number;
  approved_conversions: number;
  pending_conversions: number;
  conversion_rate: number;
  approved_revenue_by_currency: Record<string, number>;
  pending_revenue_by_currency: Record<string, number>;
  epc_by_currency: Record<string, number>;
};

type CampaignDetail = {
  campaign: Campaign;
  metrics: Metrics;
};

type Summary = {
  total_campaigns: number;
  active_campaigns: number;
  human_clicks: number;
  approved_conversions: number;
  conversion_rate: number;
  approved_revenue_by_currency: Record<string, number>;
  epc_by_currency: Record<string, number>;
};

type Props = {
  api: string;
  seed: WorkspaceSeed | null;
};

const emptySummary: Summary = {
  total_campaigns: 0,
  active_campaigns: 0,
  human_clicks: 0,
  approved_conversions: 0,
  conversion_rate: 0,
  approved_revenue_by_currency: {},
  epc_by_currency: {},
};

export default function Workspace({ api, seed }: Props) {
  const [campaigns, setCampaigns] = useState<CampaignDetail[]>([]);
  const [summary, setSummary] = useState<Summary>(emptySummary);
  const [name, setName] = useState("My first affiliate campaign");
  const [productName, setProductName] = useState("AI tool");
  const [affiliateUrl, setAffiliateUrl] = useState("");
  const [source, setSource] = useState("manual");
  const [opportunityScore, setOpportunityScore] = useState("");
  const [status, setStatus] = useState<Campaign["status"]>("draft");
  const [conversionCampaignId, setConversionCampaignId] = useState("");
  const [commission, setCommission] = useState("");
  const [saleAmount, setSaleAmount] = useState("");
  const [currency, setCurrency] = useState("EUR");
  const [network, setNetwork] = useState("");
  const [externalId, setExternalId] = useState("");
  const [conversionStatus, setConversionStatus] = useState("approved");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void loadWorkspace();
  }, []);

  useEffect(() => {
    if (!seed) return;
    setName(`${seed.productName} campaign`);
    setProductName(seed.productName);
    setAffiliateUrl(seed.affiliateUrl);
    setSource(seed.source);
    setOpportunityScore(seed.opportunityScore.toFixed(1));
    setStatus(seed.affiliateUrl ? "active" : "draft");
    setMessage(
      seed.affiliateUrl
        ? "Opportunity loaded. Review the tracking URL, then create the campaign."
        : "Opportunity loaded. Add your approved affiliate tracking URL before activating it.",
    );
  }, [seed]);

  async function loadWorkspace() {
    try {
      const [campaignResponse, summaryResponse] = await Promise.all([
        fetch(`${api}/api/v1/workspace/campaigns`),
        fetch(`${api}/api/v1/workspace/summary`),
      ]);
      if (!campaignResponse.ok || !summaryResponse.ok) return;
      const campaignData = (await campaignResponse.json()) as CampaignDetail[];
      setCampaigns(campaignData);
      setSummary((await summaryResponse.json()) as Summary);
      if (!conversionCampaignId && campaignData.length > 0) {
        setConversionCampaignId(campaignData[0].campaign.id);
      }
    } catch {
      setMessage("Campaign workspace is unavailable. Check the backend.");
    }
  }

  async function createCampaign(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`${api}/api/v1/workspace/campaigns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          product_name: productName,
          affiliate_url: affiliateUrl,
          source: source || null,
          opportunity_score: opportunityScore ? Number(opportunityScore) : null,
          status,
        }),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => null);
        setMessage(detail?.detail || "Could not create campaign.");
        return;
      }
      const created = (await response.json()) as CampaignDetail;
      setConversionCampaignId(created.campaign.id);
      setMessage(`Campaign created: /go/${created.campaign.slug}`);
      await loadWorkspace();
    } catch {
      setMessage("Could not reach the campaign API.");
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(campaign: Campaign, next: Campaign["status"]) {
    const response = await fetch(`${api}/api/v1/workspace/campaigns/${campaign.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: next }),
    });
    if (response.ok) await loadWorkspace();
  }

  async function logConversion(event: FormEvent) {
    event.preventDefault();
    if (!conversionCampaignId) return;
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(
        `${api}/api/v1/workspace/campaigns/${conversionCampaignId}/conversions`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            commission_amount: Number(commission),
            sale_amount: saleAmount ? Number(saleAmount) : null,
            currency: currency.toUpperCase(),
            status: conversionStatus,
            network: network || null,
            external_id: externalId || null,
          }),
        },
      );
      if (!response.ok) {
        const detail = await response.json().catch(() => null);
        setMessage(detail?.detail || "Could not save conversion.");
        return;
      }
      setCommission("");
      setSaleAmount("");
      setExternalId("");
      setMessage("Conversion saved. Revenue and EPC recalculated.");
      await loadWorkspace();
    } catch {
      setMessage("Could not reach the conversion API.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel workspace-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Persistent campaign workspace</p>
          <h2>Clicks → conversions → real revenue</h2>
        </div>
        <span className="status-dot">SQLite + tracked redirects</span>
      </div>

      <div className="workspace-summary">
        <SummaryStat label="Campaigns" value={`${summary.active_campaigns}/${summary.total_campaigns} active`} />
        <SummaryStat label="Human clicks" value={String(summary.human_clicks)} />
        <SummaryStat label="Conversions" value={String(summary.approved_conversions)} />
        <SummaryStat label="Conversion rate" value={`${(summary.conversion_rate * 100).toFixed(2)}%`} />
        <SummaryStat label="Approved revenue" value={formatMoneyMap(summary.approved_revenue_by_currency)} />
        <SummaryStat label="Real EPC" value={formatMoneyMap(summary.epc_by_currency)} />
      </div>

      <div className="workspace-grid">
        <form onSubmit={createCampaign} className="workspace-form">
          <h3>Create campaign</h3>
          <label>
            Campaign name
            <input value={name} onChange={(event) => setName(event.target.value)} required />
          </label>
          <label>
            Product / offer
            <input value={productName} onChange={(event) => setProductName(event.target.value)} required />
          </label>
          <label className="full-width">
            Your approved affiliate tracking URL
            <input
              type="url"
              value={affiliateUrl}
              onChange={(event) => setAffiliateUrl(event.target.value)}
              placeholder="https://network.example/your-tracking-link"
              required
            />
          </label>
          <label>
            Source
            <input value={source} onChange={(event) => setSource(event.target.value)} />
          </label>
          <label>
            Opportunity score
            <input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={opportunityScore}
              onChange={(event) => setOpportunityScore(event.target.value)}
            />
          </label>
          <label>
            Status
            <select value={status} onChange={(event) => setStatus(event.target.value as Campaign["status"])}>
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
            </select>
          </label>
          <p className="fine-print full-width">
            Use a real affiliate tracking link issued to your account. A public program/signup page will not earn commission.
          </p>
          <button type="submit" disabled={busy}>{busy ? "Saving…" : "Create tracked campaign"}</button>
        </form>

        <form onSubmit={logConversion} className="workspace-form">
          <h3>Log network conversion</h3>
          <label className="full-width">
            Campaign
            <select
              value={conversionCampaignId}
              onChange={(event) => setConversionCampaignId(event.target.value)}
              required
            >
              <option value="">Select campaign</option>
              {campaigns.map(({ campaign }) => (
                <option value={campaign.id} key={campaign.id}>{campaign.name}</option>
              ))}
            </select>
          </label>
          <label>
            Commission earned
            <input
              type="number"
              min="0"
              step="0.01"
              value={commission}
              onChange={(event) => setCommission(event.target.value)}
              required
            />
          </label>
          <label>
            Sale amount (optional)
            <input
              type="number"
              min="0"
              step="0.01"
              value={saleAmount}
              onChange={(event) => setSaleAmount(event.target.value)}
            />
          </label>
          <label>
            Currency
            <input maxLength={3} value={currency} onChange={(event) => setCurrency(event.target.value)} required />
          </label>
          <label>
            Network
            <input value={network} onChange={(event) => setNetwork(event.target.value)} placeholder="CJ / Impact" />
          </label>
          <label>
            External order/action ID
            <input value={externalId} onChange={(event) => setExternalId(event.target.value)} />
          </label>
          <label>
            Status
            <select value={conversionStatus} onChange={(event) => setConversionStatus(event.target.value)}>
              <option value="approved">Approved</option>
              <option value="pending">Pending</option>
              <option value="reversed">Reversed</option>
            </select>
          </label>
          <button type="submit" disabled={busy || !conversionCampaignId}>Save conversion</button>
        </form>
      </div>

      {message && <p className="workspace-message">{message}</p>}

      <div className="campaign-list">
        {campaigns.length === 0 ? (
          <p className="muted">No campaigns yet. Create one above or start from an opportunity.</p>
        ) : campaigns.map(({ campaign, metrics }) => {
          const trackedUrl = `${api.replace(/\/$/, "")}/go/${campaign.slug}`;
          return (
            <article className="campaign-card" key={campaign.id}>
              <div className="campaign-card-head">
                <div>
                  <span className="source">{campaign.source || "manual"}</span>
                  <h3>{campaign.name}</h3>
                  <p className="muted">{campaign.product_name}</p>
                </div>
                <span className={`campaign-status ${campaign.status}`}>{campaign.status}</span>
              </div>
              <div className="metrics">
                <span>{metrics.human_clicks} human clicks</span>
                <span>{metrics.bot_clicks} bot clicks excluded</span>
                <span>{metrics.approved_conversions} approved conversions</span>
                <span>{(metrics.conversion_rate * 100).toFixed(2)}% CVR</span>
                <span>Revenue {formatMoneyMap(metrics.approved_revenue_by_currency)}</span>
                <span>EPC {formatMoneyMap(metrics.epc_by_currency)}</span>
                {metrics.pending_conversions > 0 && <span>{metrics.pending_conversions} pending</span>}
              </div>
              <code className="tracking-url">{trackedUrl}</code>
              <div className="links campaign-actions">
                {campaign.status === "active" && <a href={trackedUrl} target="_blank" rel="noreferrer">Test tracked link</a>}
                {campaign.status !== "active" ? (
                  <button type="button" className="small-button" onClick={() => void changeStatus(campaign, "active")}>Activate</button>
                ) : (
                  <button type="button" className="small-button" onClick={() => void changeStatus(campaign, "paused")}>Pause</button>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return <div className="summary-stat"><small>{label}</small><strong>{value}</strong></div>;
}

function formatMoneyMap(values: Record<string, number>): string {
  const entries = Object.entries(values);
  if (entries.length === 0) return "—";
  return entries.map(([currency, value]) => `${currency} ${value.toFixed(2)}`).join(" · ");
}
