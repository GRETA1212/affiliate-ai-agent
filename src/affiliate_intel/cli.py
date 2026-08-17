from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .db import Repository
from .scanner import load_candidates, normalize_candidates
from .scoring import score_program


def main() -> None:
    parser = argparse.ArgumentParser(prog="affiliate-intel")
    parser.add_argument("--db", default="affiliate_intel.db")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db")

    ingest = sub.add_parser("ingest")
    ingest.add_argument("path")

    score = sub.add_parser("score-file")
    score.add_argument("path")

    args = parser.parse_args()
    repo = Repository(args.db)

    if args.command == "init-db":
        repo.init()
        print(args.db)
        return

    if args.command == "ingest":
        repo.init()
        programs = normalize_candidates(load_candidates(args.path))
        for program in programs:
            repo.upsert_program(program)
        print(json.dumps({"ingested": len(programs)}, indent=2))
        return

    if args.command == "score-file":
        programs = normalize_candidates(load_candidates(args.path))
        ranked = sorted(
            ((program, score_program(program)) for program in programs),
            key=lambda pair: pair[1].total,
            reverse=True,
        )
        print(
            json.dumps(
                [
                    {
                        "slug": program.slug,
                        "name": program.name,
                        "verification_status": program.verification_status,
                        "score": asdict(score),
                    }
                    for program, score in ranked
                ],
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
