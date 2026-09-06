# Maya.exe TikTok Shop commission audit — Italy

Evidence date: 2026-08-19

## Critical correction

Do not confuse TikTok Shop's seller platform commission fee with the affiliate commission paid to Maya as a creator.

TikTok Shop Italy currently charges sellers a standard platform commission fee of 9% on settled orders, with category-level reductions for some electronics / beauty & personal care electronics to an effective 7%. This is a seller cost, not Maya's creator earnings rate.

For creators, TikTok Shop's affiliate documentation states that affiliate commission rates vary by product and are set through seller collaboration structures. Product-level creator commission must therefore be read from Creator Center / the exact collaboration, not inferred from the seller fee.

## Product Scout rule update

For every exact TikTok Shop product candidate, record these as separate fields:

- seller_platform_fee_rate: informational only; never use as Maya's earnings rate
- creator_affiliate_commission_rate: exact rate shown to the creator for that product/collaboration
- creator_affiliate_commission_eur_per_order: calculated from the current eligible sale basis only after the exact rate and current price are verified
- shop_ad_commission_rate: separate from the standard organic creator rate where TikTok/seller uses affiliate shopping ads

If creator_affiliate_commission_rate is not visible from a legitimate Creator Center / collaboration source, store UNKNOWN and do not estimate.

## EU small-parcel customs change

From 1 July 2026 the EU applies a temporary fixed €3 customs duty to goods in small consignments under €150, charged per category/tariff-heading group in the parcel for relevant IOSS imports. This makes direct-from-non-EU one-order fulfillment less attractive for low-ticket products than before.

Operational implication for Maya: prefer products with EU inventory / reliable EU fulfillment where practical, but do not claim the customs rule makes every non-EU product unprofitable. Product margin, seller logistics, VAT handling, returns and who bears the import cost all still need exact verification.

## Ranking rule for Maya

Rank products by:

1. demonstrated demand / sales signal available to the creator
2. visual demonstration strength for short-form video
3. creator affiliate commission in EUR per eligible order
4. seller/listing quality and returns risk
5. Maya fit and repeatable content potential
6. EU fulfillment / delivery practicality
7. claims and compliance risk

Never rank a product higher merely because its seller pays a lower TikTok platform fee.

## Primary sources checked

- TikTok Shop Academy Italy — product-category seller commission rates, updated 28 May 2026
- TikTok Shop Academy Italy — creator affiliate payment and commission rules, updated 15 July 2026
- TikTok Shop Academy Italy — affiliate program / seller-set creator commissions, 2026
- Council of the European Union — temporary €3 customs duty on small parcels from 1 July 2026
