# Maya Product Scoring System

Purpose: rank monetizable product opportunities for Maya.exe using verified creator economics and observable content fit. This scorecard is for affiliate selection, not for choosing products Maya has supposedly tested.

## Critical distinction

TikTok Shop seller platform fees and Maya's creator affiliate commission are different values.

- `seller_platform_fee_percent` = fee TikTok charges the seller for using TikTok Shop. This affects seller economics but is **not Maya revenue**.
- `creator_affiliate_rate_percent` = rate Maya can earn for eligible attributed sales. This varies by product/collaboration and must be read from TikTok Shop Creator Center / the exact collaboration.
- `creator_commission_eur_per_order` = expected commission shown/calculated from the exact verified creator rate and current eligible sale price. Never infer this from TikTok's seller platform fee.

If creator commission is not visible from an authoritative creator/collaboration source, store `UNKNOWN` and block approval.

## Hard approval gate

An exact product cannot move from `candidate` to `approved_for_content` unless all of these are verified:

1. exact product name
2. exact seller/merchant
3. exact listing URL
4. current price if price will be used publicly
5. creator affiliate rate / expected commission where monetization is planned
6. seller-quality signal available to the creator
7. product/category eligibility for Italy
8. claims risk reviewed
9. Maya can represent the product honestly in the proposed creative
10. evidence date and source recorded

Additional physical-product preference: prefer EU-stocked or otherwise clearly compliant/fulfillable inventory when two candidates have similar creator economics and demand. Do not assume EU stock from a brand name alone.

## Scoring

Score verified candidates from 0 to 10 on each dimension:

- **Italy demand / buyer-intent evidence — 30%**
- **Visual demonstration potential — 25%**
- **Creator commission economics — 20%**
- **Seller quality — 15%**
- **Maya fit — 10%**

Base score:

`weighted_score = demand*0.30 + visual_demo*0.25 + creator_commission*0.20 + seller_quality*0.15 + maya_fit*0.10`

Then apply risk gates rather than hiding risk inside the score.

### Block regardless of score

- exact listing unverified
- creator commission presented as known when it is not
- fake/unverifiable discount
- seller identity or listing quality is unclear
- unsupported medical, efficacy, shade-match, safety, or performance claim needed for the concept
- product cannot be shown/tested truthfully
- obvious compliance/safety concern without adequate documentation
- geography/KYC/account eligibility would need to be faked

## Commission scoring guidance

Do not score the commission field from percentage alone. Rank by expected **EUR commission per completed eligible order**, then consider refund/return risk and whether the ticket price is realistic for Maya's audience.

Example only:

- Product A: €20 price at 20% creator rate = €4 potential commission/order.
- Product B: €80 price at 8% creator rate = €6.40 potential commission/order.

Product B has higher commission/order, but it may still lose if conversion friction, seller quality, return risk, or content fit are worse. These examples are arithmetic only, not current TikTok Shop listings.

## Candidate states

- `category_thesis` — evidence exists only at category level.
- `needs_creator_center` — exact SKU or creator commission needs Creator Center verification.
- `candidate` — exact listing identified, not yet cleared.
- `needs_human_review` — spend, sample acceptance, legal/health risk, or material claim needs approval.
- `approved_for_content` — listing and claims cleared for a specific video angle.
- `approved_for_affiliate` — exact monetized destination and disclosure cleared.
- `paused` — weak economics/performance or evidence no longer current.

## Maya-specific content test

Before promoting any product, answer:

1. Can a viewer understand the product benefit or comparison in 3–5 seconds?
2. Does it naturally fit AI makeup, beauty tech, experiments, or creator tools?
3. Can we create at least 3 truthful video angles from it?
4. Does the video remain interesting even if the viewer never buys?
5. Can we use real product footage if the concept implies physical performance?

If fewer than 4 answers are yes, deprioritize it even if commission is high.

## Post-publish optimization

Once real data exists, replace opinion with measured performance:

- product clicks per 1,000 views
- orders per 1,000 views
- commission revenue per 1,000 views
- refund/cancellation impact where visible
- seller amplification / ad-derived orders where distinguishable

The winning product is the one producing repeatable **verified revenue per 1,000 views** without misleading viewers, not the one with the highest headline commission percentage.
