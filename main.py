from affiliate_agent.hunter import rank_opportunities, top_opportunities


def main() -> None:
    ranked = rank_opportunities(20)

    print("\nAFFILIATE AI OPPORTUNITY HUNTER\n" + "=" * 38)
    print("Scanned 20 candidate opportunities.\n")

    for index, (opportunity, score) in enumerate(ranked, start=1):
        payout = opportunity.price * opportunity.commission_rate
        print(
            f"{index:>2}. {opportunity.name:<28} "
            f"score={score:>5.2f}  niche={opportunity.niche:<18} "
            f"est_payout=${payout:>6.2f}"
        )

    print("\nTOP 3 TO TEST FIRST\n" + "-" * 38)
    for index, (opportunity, score) in enumerate(top_opportunities(3, 20), start=1):
        print(f"{index}. {opportunity.name} — {score}/100")
        print(
            f"   Demand {opportunity.demand}/100 | Competition {opportunity.competition}/100 | "
            f"Content {opportunity.content_potential}/100 | Recurring {opportunity.recurring_revenue}/100"
        )


if __name__ == "__main__":
    main()
