# TikTok Shop Creator Center intake — Maya.exe Italy

Use this only after the legitimate Italy creator account has e-commerce permission and Creator Center access.

## Goal

Collect enough exact listing-level data to let Product Scout rank products using real creator economics. Do not copy seller platform fees into creator commission fields.

## First session: collect 10 exact listings

Prioritize products that fit Maya's current content pillars:

1. makeup / lip / blush products that can support a visible look
2. makeup tools with a clear before/after or speed benefit
3. beauty-tech devices with a simple demonstrable job
4. creator gear that directly improves beauty-video production

Avoid health-heavy products, supplements, or products that would require claims Maya cannot verify during the first test phase.

## For every listing record

Copy exactly what Creator Center shows:

- exact product name
- seller/store name
- product listing URL or product ID
- current displayed price
- creator affiliate commission rate
- estimated creator commission per eligible order if shown
- whether a different ad/Shop Ads commission is shown
- free sample availability
- sample requirements/deadline
- seller/store quality signal shown to creator
- sales/trend/ranking signal shown to creator, if any
- product category
- shipping origin / EU-stock evidence if shown
- any campaign or boosted commission information
- date/time observed

If a field is not visible, enter `UNKNOWN`. Never estimate it.

## Screen-to-score workflow

For each exact product:

1. Save the Creator Center data in `data/product-scorecard.csv`.
2. Give 0–10 scores for:
   - Italy demand/buyer intent
   - visual demo potential
   - creator commission economics
   - seller quality
   - Maya fit
3. Run the hard-block checks in `runbooks/product-scoring.md`.
4. Rank only products with verified listing + seller + creator commission fields.
5. Move at most 3 products into the first test queue.

## What to prefer in the first 3 products

Prefer products where:

- the product can be understood visually in 3–5 seconds
- one product can support at least 3 truthful videos
- a real sample is available or the product is already legitimately owned
- the creator commission in EUR/order is meaningful relative to likely conversion friction
- the seller/store quality signal is strong
- the product naturally fits V001/V003/V004-style beauty content

## What to reject quickly

Reject or pause when:

- commission is high but the product is hard to demonstrate
- the seller looks weak or the listing is unclear
- the concept requires fake testing or invented results
- the product needs medical/efficacy claims to sell
- there is no exact creator commission shown
- the listing is cheap but shipping/returns/compliance make the seller unstable
- the product is unrelated to Maya merely because a category has high GMV

## Samples

TikTok Shop Creator Center supports product discovery, sample requests, adding products to content, and earnings analytics. When a free sample is approved and received, follow the current Creator Center sample obligation shown for that product. Do not say a sample was received before physical receipt.

For the first sample batch, request at most 3–5 products. Do not create an obligation to produce low-quality shoppable videos for products Maya would not otherwise cover.

## First output to Orchestrator

Return a table with:

`rank | product | seller | price | creator rate | creator EUR/order | sample | seller signal | visual angle | weighted score | risk | decision`

Then recommend exactly:

- 1 primary product
- 1 backup product
- 1 experiment product

Every recommendation must include the exact video angle and what real footage/proof is required.
