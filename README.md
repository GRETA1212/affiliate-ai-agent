# Affiliate AI Agent

V1 starts with a deliberately small autonomous business loop: find 20 affiliate opportunities, score them, return the best 3 to test, and optionally generate a TikTok/YouTube Shorts test pack for the top candidate with local Ollama.

## What is implemented

- 20 initial opportunity candidates across SaaS, AI, creator, security, education, and digital-product niches.
- Weighted scoring based on demand, commission attractiveness, conversion potential, content potential, competition, and recurring revenue.
- Ranking CLI that prints all 20 candidates and highlights the top 3.
- Local Ollama content agent that generates 10 hooks, 3 short scripts, CTAs, positioning, and a test plan for the top opportunity.
- Unit tests for score bounds, ranking order, and top-3 selection.

## Run the opportunity hunter

```bash
python main.py
```

## Generate content with local Ollama

Make sure Ollama is running and the model exists locally, then run:

```bash
python main.py --generate --model qwen3:4b
```

The local Ollama API defaults to `http://localhost:11434/api/generate`. No paid API key is required for local models.

## Test

```bash
python -m pytest
```

## Scoring model

- Demand: 30%
- Commission attractiveness: 20%
- Conversion potential: 15%
- Content potential: 15%
- Low competition: 10%
- Recurring revenue: 10%

Commission attractiveness combines percentage commission with estimated absolute payout so a cheap product does not win solely because it advertises a large percentage.

## Important limitation of V1

The 20 candidates are seed data, not live market claims. This makes the scoring engine deterministic and testable first. The next milestone is to replace/enrich seed metrics with live sources (affiliate program data, search/trend signals, YouTube/TikTok performance inputs) while keeping the same scoring API.

## Roadmap

1. Live opportunity collectors and source provenance.
2. SQLite/Postgres persistence for opportunities and experiments.
3. Improve the content agent with campaign memory and variants.
4. Short-video renderer integration.
5. Publishing queue with human approval gates.
6. Analytics loop using views, CTR, conversion rate, EPC, revenue, cost, and profit.
7. Automatically reduce losing experiments and scale winning patterns.
