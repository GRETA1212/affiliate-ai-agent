"""Guarded Postiz publisher for Maya.exe.

Examples:

    python run_postiz_social.py integrations

    python run_postiz_social.py publish \
        --mode draft \
        --integration-id <tiktok-id> \
        --integration-id <youtube-id> \
        --title "AI picked my 10-minute makeup look" \
        --caption "The first Maya.exe test." \
        --media-url https://cdn.example.com/maya-v001.mp4

Scheduled or immediate publication requires --confirm-publish deliberately.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime

from app.connectors import postiz


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maya.exe Postiz social publishing buffer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    integrations = subparsers.add_parser(
        "integrations",
        help="List social channels connected to Postiz.",
    )
    integrations.add_argument("--group", default=None, help="Optional Postiz customer/group ID")

    publish = subparsers.add_parser(
        "publish",
        help="Create a Maya social draft, schedule, or immediate post.",
    )
    publish.add_argument(
        "--integration-id",
        action="append",
        required=True,
        dest="integration_ids",
        help="Postiz integration/channel ID. Repeat for multiple channels.",
    )
    publish.add_argument("--title", required=True, help="Platform title; required for YouTube")
    publish.add_argument("--caption", required=True, help="Master caption/description")
    publish.add_argument(
        "--mode",
        choices=["draft", "schedule", "now"],
        default="draft",
        help="Draft is the safe default. Schedule/now require --confirm-publish.",
    )
    publish.add_argument(
        "--scheduled-at",
        default=None,
        help="Timezone-aware ISO 8601 datetime for schedule mode, e.g. 2026-09-08T19:00:00+02:00",
    )
    media_group = publish.add_mutually_exclusive_group()
    media_group.add_argument(
        "--media-url",
        default=None,
        help="Public HTTPS video/image URL that Postiz can ingest.",
    )
    media_group.add_argument(
        "--media-file",
        default=None,
        help="Local video/image file to upload to Postiz.",
    )
    publish.add_argument(
        "--commercial-disclosure",
        default=None,
        help="Verified disclosure text to append, e.g. an affiliate disclosure.",
    )
    publish.add_argument(
        "--branded-content",
        action="store_true",
        help="Enable TikTok branded-content toggles only when the relationship is verified.",
    )
    publish.add_argument(
        "--tiktok-upload-only",
        action="store_true",
        help="Send TikTok media to the TikTok app inbox instead of DIRECT_POST.",
    )
    publish.add_argument(
        "--youtube-visibility",
        choices=["public", "unlisted", "private"],
        default="public",
    )
    publish.add_argument(
        "--confirm-publish",
        action="store_true",
        help="Required for mode=schedule or mode=now. Not needed for drafts.",
    )
    publish.add_argument(
        "--content-id",
        default=None,
        help="Optional Maya V###/EXP-* identifier included in command output for auditability.",
    )
    return parser


def parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise SystemExit("--scheduled-at must be a valid ISO 8601 datetime") from exc
    if parsed.tzinfo is None:
        raise SystemExit("--scheduled-at must include a timezone offset")
    return parsed


def list_connected_integrations(group: str | None) -> int:
    integrations = postiz.list_integrations(group=group)
    payload = [
        {
            "id": item.id,
            "name": item.name,
            "provider": item.identifier,
            "profile": item.profile,
            "disabled": item.disabled,
            "maya_supported": item.identifier in postiz.MAYA_SUPPORTED_PROVIDERS,
        }
        for item in integrations
    ]
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def publish(args: argparse.Namespace) -> int:
    if args.mode in {"schedule", "now"} and not args.confirm_publish:
        raise SystemExit(
            "Refusing public publication without --confirm-publish. "
            "Use --mode draft for review-first operation."
        )
    scheduled_at = parse_datetime(args.scheduled_at)
    if args.mode == "schedule" and scheduled_at is None:
        raise SystemExit("--scheduled-at is required when --mode schedule is used")
    if args.mode != "schedule" and scheduled_at is not None:
        raise SystemExit("--scheduled-at is only valid with --mode schedule")

    integrations = postiz.list_integrations()
    by_id = {item.id: item for item in integrations}
    selected = []
    for integration_id in args.integration_ids:
        integration = by_id.get(integration_id)
        if integration is None:
            raise SystemExit(
                f"Integration {integration_id!r} was not returned by Postiz. "
                "Run `python run_postiz_social.py integrations` first."
            )
        selected.append(integration)

    media: list[postiz.PostizMedia] = []
    if args.media_url:
        media.append(postiz.upload_from_url(args.media_url))
    elif args.media_file:
        media.append(postiz.upload_file(args.media_file))

    caption = args.caption.strip()
    if args.commercial_disclosure:
        caption = f"{caption.rstrip()}\n\n{args.commercial_disclosure.strip()}"

    posts = [
        postiz.build_maya_channel_post(
            integration,
            content=caption,
            title=args.title,
            media=media,
            branded_content=args.branded_content,
            tiktok_upload_only=args.tiktok_upload_only,
            youtube_visibility=args.youtube_visibility,
        )
        for integration in selected
    ]
    results = postiz.create_posts(
        posts,
        mode=args.mode,
        scheduled_at=scheduled_at,
    )
    output = {
        "content_id": args.content_id,
        "mode": args.mode,
        "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
        "channels": [
            {
                "integration_id": item.id,
                "provider": item.identifier,
                "profile": item.profile,
            }
            for item in selected
        ],
        "postiz_results": [item.model_dump(by_alias=True) for item in results],
        "ai_disclosure_enforced": True,
        "public_publish_confirmed": bool(args.confirm_publish),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "integrations":
            return list_connected_integrations(args.group)
        if args.command == "publish":
            return publish(args)
        parser.error(f"Unknown command: {args.command}")
    except (postiz.PostizConfigurationError, postiz.PostizAPIError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
