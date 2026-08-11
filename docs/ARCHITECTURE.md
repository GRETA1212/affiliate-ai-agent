# Architecture

## V1 flow

`Offer signals -> Opportunity scorer -> Revenue forecast -> Campaign planner -> API -> Dashboard`

The V1 core is deterministic. This makes every recommendation auditable and gives us a stable baseline before adding LLM-generated reasoning or learned ranking.

### Backend

- `models.py`: validated API contracts.
- `opportunity_scorer.py`: weighted 0-100 ranking model.
- `forecast.py`: expected-click, conversion, revenue, and EPC math.
- `content_agent.py`: help-first campaign ideation and disclosure template.
- `connectors/`: credential-aware placeholders for external data sources.
- `main.py`: FastAPI endpoints.

### Planned data layer

V2 will add SQLite/PostgreSQL storage for offers, network terms, content assets, tracking links, clicks, conversions, revenue, and experiment history.

### Planned learning loop

Once real data exists, predicted metrics will be compared with observed CTR, conversion rate, EPC, and revenue. The system can then calibrate weights by niche, channel, network, and content intent.

## Safety and quality boundaries

The system should not bypass advertiser approval, fabricate product experience, generate fake reviews, spam platforms, or circumvent affiliate-network restrictions. Automated publishing remains opt-in and must preserve affiliate disclosures.
