from __future__ import annotations

import argparse
import json

from affiliate_agent.content_agent import generate_content_pack
from affiliate_agent.hunter import rank_opportunities, top_opportunities


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Affiliate AI opportunity hunter")
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate a TikTok/YouTube Shorts content test pack for the top opportunity using local Ollama.",
    )
    parser.add_argument(
        "--model",
        default="qwen3:4b",
        help="Local Ollama model to use when --generate is enabled (default: qwen3:4b).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
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

    winners = top_opportunities(3, 20)
    print("\nTOP 3 TO TEST FIRST\n" + "-" * 38)
    for index, (opportunity, score) in enumerate(winners, start=1):
        print(f"{index}. {opportunity.name} — {score}/100")
        print(
            f"   Demand {opportunity.demand}/100 | Competition {opportunity.competition}/100 | "
            f"Content {opportunity.content_potential}/100 | Recurring {opportunity.recurring_revenue}/100"
        )

    if args.generate:
        winner, winner_score = winners[0]
        print(f"\nGenerating content for: {winner.name} ({winner_score}/100) using {args.model}...\n")
        content_pack = generate_content_pack(winner, model=args.model)
        print(json.dumps(content_pack, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
