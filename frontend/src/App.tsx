import { FormEvent, useState } from "react";

type ScoreResult = {
  product_name: string;
  score: number;
  rating: string;
};

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function App() {
  const [product, setProduct] = useState("Example VPS");
  const [result, setResult] = useState<ScoreResult | null>(null);
  const [error, setError] = useState("");

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
        <article><h3>Research</h3><p>CJ, Impact, Google Ads and YouTube connectors are next.</p></article>
        <article><h3>Forecast</h3><p>Estimate clicks, conversions, revenue and EPC before investing time.</p></article>
        <article><h3>Create</h3><p>Generate help-first campaign angles with clear affiliate disclosure.</p></article>
      </section>
    </main>
  );
}
