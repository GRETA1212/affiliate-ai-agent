from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.services import business_controller as business
from app.services import campaign_workspace as workspace

MoviePlatform = Literal["tiktok", "youtube_shorts", "instagram_reels"]
MovieTone = Literal["cinematic", "mystery", "romance", "comedy", "luxury", "documentary"]
ProductPresence = Literal["none", "background", "natural", "focus"]


class MoviePlanRequest(BaseModel):
    campaign_id: str = Field(min_length=8, max_length=80)
    concept: str | None = Field(default=None, max_length=600)
    tone: MovieTone = "cinematic"
    duration_seconds: int = Field(default=70, ge=45, le=90)
    scene_count: int = Field(default=9, ge=6, le=14)
    platforms: list[MoviePlatform] = Field(
        default_factory=lambda: ["tiktok", "youtube_shorts", "instagram_reels"],
        min_length=1,
        max_length=3,
    )


class MovieJobRequest(MoviePlanRequest):
    priority: int = Field(default=70, ge=0, le=100)


class MovieScene(BaseModel):
    order: int
    seconds: int
    purpose: str
    visual_prompt: str
    dialogue_or_voiceover: str
    overlay_text: str | None = None
    product_presence: ProductPresence


class DistributionAsset(BaseModel):
    platform: MoviePlatform
    aspect_ratio: str = "9:16"
    tracking_path: str
    caption: str
    disclosure: str
    ai_label_required: bool = True


class MoviePlan(BaseModel):
    content_id: str
    campaign_id: str
    campaign_name: str
    product_name: str
    title: str
    concept: str
    hook: str
    tone: MovieTone
    target_duration_seconds: int
    scenes: list[MovieScene]
    call_to_action: str
    affiliate_disclosure: str
    distribution: list[DistributionAsset]
    production_notes: list[str]


class QueuedMovieJob(BaseModel):
    job_id: str
    plan: MoviePlan


def build_movie_plan(data: MoviePlanRequest) -> MoviePlan:
    detail = workspace.get_campaign(data.campaign_id)
    campaign = detail.campaign
    content_id = f"movie-{uuid4().hex[:10]}"

    audience = campaign.audience.strip() or "the target viewer"
    problem = campaign.problem.strip() or "a relatable everyday problem"
    concept = data.concept.strip() if data.concept else _default_concept(
        campaign.product_name,
        audience,
        problem,
    )
    hook = _hook(problem, data.tone)
    scenes = _build_scenes(
        product=campaign.product_name,
        audience=audience,
        problem=problem,
        concept=concept,
        tone=data.tone,
        duration_seconds=data.duration_seconds,
        scene_count=data.scene_count,
    )
    disclosure = (
        "Affiliate disclosure: this episode contains an affiliate link. "
        "A purchase may earn the publisher a commission at no extra cost to the viewer."
    )
    cta = (
        f"If {campaign.product_name} fits your needs, use the episode link to see the exact "
        "product. Check the details yourself before buying."
    )
    distribution = [
        DistributionAsset(
            platform=platform,
            tracking_path=(
                f"/go/{campaign.slug}?source={platform}&medium=affiliate_movie&content={content_id}"
            ),
            caption=(
                f"{_caption_lead(data.tone)} {campaign.product_name} appears naturally in this "
                f"episode. {disclosure}"
            ),
            disclosure=disclosure,
        )
        for platform in _dedupe_platforms(data.platforms)
    ]

    return MoviePlan(
        content_id=content_id,
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        product_name=campaign.product_name,
        title=_title(campaign.product_name, data.tone),
        concept=concept,
        hook=hook,
        tone=data.tone,
        target_duration_seconds=data.duration_seconds,
        scenes=scenes,
        call_to_action=cta,
        affiliate_disclosure=disclosure,
        distribution=distribution,
        production_notes=[
            "Keep the same character reference, wardrobe, and environment continuity across shots.",
            "Generate vertical 9:16 masters and keep key text inside mobile-safe margins.",
            "Do not invent product specifications, prices, medical claims, earnings claims, or guarantees.",
            "Keep product placement story-first: introduce the product after the conflict is established.",
            "Use the per-platform tracking path so clicks and conversions flow into Affiliate AI analytics.",
            "Apply the platform's AI-content disclosure/label when required before publishing.",
        ],
    )


def queue_movie_job(data: MovieJobRequest) -> QueuedMovieJob:
    plan = build_movie_plan(MoviePlanRequest(**data.model_dump(exclude={"priority"})))
    job_id = business.enqueue_content_job(
        business.ContentJobCreate(
            job_type="affiliate_movie",
            title=plan.title[:200],
            brief=plan.model_dump(mode="json"),
            campaign_id=plan.campaign_id,
            priority=data.priority,
        )
    )
    return QueuedMovieJob(job_id=job_id, plan=plan)


def _default_concept(product: str, audience: str, problem: str) -> str:
    return (
        f"A fast vertical mini-movie following {audience} through a believable situation involving "
        f"{problem}. The story introduces {product} only after the problem is clear, then ends on a "
        "small reveal or cliffhanger rather than a hard-sell advertisement."
    )


def _hook(problem: str, tone: MovieTone) -> str:
    prefixes = {
        "cinematic": "Everything looked normal until one small detail changed.",
        "mystery": "She noticed something nobody else in the room had seen.",
        "romance": "She thought the meeting was over, until he came back.",
        "comedy": "This was supposed to take two minutes. It did not.",
        "luxury": "The room looked expensive. The mistake was even more expensive.",
        "documentary": "This is the moment the original plan stopped working.",
    }
    return f"{prefixes[tone]} The tension centers on {problem}."


def _title(product: str, tone: MovieTone) -> str:
    labels = {
        "cinematic": "The Detail She Almost Missed",
        "mystery": "The Clue in Plain Sight",
        "romance": "One More Minute",
        "comedy": "The Simple Plan",
        "luxury": "The Last-Minute Upgrade",
        "documentary": "What Changed the Outcome",
    }
    return f"{labels[tone]} | {product}"[:200]


def _caption_lead(tone: MovieTone) -> str:
    leads = {
        "cinematic": "A 70-second story with one useful detail.",
        "mystery": "Watch closely; the useful detail appears late.",
        "romance": "The story changes in the final scene.",
        "comedy": "A tiny problem becomes the whole episode.",
        "luxury": "A polished mini-story built around one practical choice.",
        "documentary": "A short story built around a real buying decision.",
    }
    return leads[tone]


def _build_scenes(
    *,
    product: str,
    audience: str,
    problem: str,
    concept: str,
    tone: MovieTone,
    duration_seconds: int,
    scene_count: int,
) -> list[MovieScene]:
    durations = _scene_durations(duration_seconds, scene_count)
    product_intro = max(3, int(scene_count * 0.6))
    purposes = [
        "cold open / visual hook",
        "establish character and objective",
        "show the problem clearly",
        "raise the stakes",
        "attempt a first solution",
        "introduce the affiliate product naturally",
        "show the product in context without unsupported claims",
        "payoff or partial resolution",
        "cliffhanger plus soft call to action",
    ]

    scenes: list[MovieScene] = []
    for index in range(scene_count):
        order = index + 1
        purpose = purposes[min(index, len(purposes) - 1)]
        if index < product_intro:
            presence: ProductPresence = "none" if index < product_intro - 1 else "background"
            product_instruction = "Do not feature or name the product yet."
        elif index == product_intro:
            presence = "natural"
            product_instruction = (
                f"Introduce {product} as an ordinary object the character chooses to use; no logo close-up "
                "unless the source creative permits it."
            )
        elif index == scene_count - 1:
            presence = "focus"
            product_instruction = (
                f"Show {product} briefly and clearly, then return attention to the character/story."
            )
        else:
            presence = "natural"
            product_instruction = f"Keep {product} visible only when the action genuinely calls for it."

        voiceover = _scene_line(
            order=order,
            scene_count=scene_count,
            product=product,
            audience=audience,
            problem=problem,
            product_intro=product_intro + 1,
        )
        overlay = None
        if order == 1:
            overlay = "WAIT—WHAT JUST CHANGED?"
        elif order == scene_count:
            overlay = "Product from the episode → link"

        scenes.append(
            MovieScene(
                order=order,
                seconds=durations[index],
                purpose=purpose,
                visual_prompt=(
                    f"Vertical 9:16 {tone} mini-movie, scene {order}/{scene_count}. {concept} "
                    f"Current beat: {purpose}. Natural human motion, coherent lighting, consistent main "
                    f"character, cinematic composition, no baked-in captions. {product_instruction}"
                ),
                dialogue_or_voiceover=voiceover,
                overlay_text=overlay,
                product_presence=presence,
            )
        )
    return scenes


def _scene_line(
    *,
    order: int,
    scene_count: int,
    product: str,
    audience: str,
    problem: str,
    product_intro: int,
) -> str:
    if order == 1:
        return "I knew something was wrong before I could explain why."
    if order == 2:
        return f"I only wanted to handle {problem} and get on with my day."
    if order == product_intro:
        return f"That was when I reached for {product}."
    if order == product_intro + 1 and order < scene_count:
        return "It fit the situation, but I still needed to check whether it was actually right for me."
    if order == scene_count:
        return (
            f"That is what I used in the episode. If you are part of {audience}, check the details in "
            "the link before deciding for yourself."
        )
    if order >= scene_count - 1:
        return "The real surprise was what happened next."
    return "The first idea did not solve it, so I changed the plan."


def _scene_durations(total: int, count: int) -> list[int]:
    base, remainder = divmod(total, count)
    durations = [base] * count
    for index in range(remainder):
        durations[index] += 1
    if durations[0] > 5:
        shift = durations[0] - 5
        durations[0] = 5
        for index in range(shift):
            durations[1 + (index % (count - 1))] += 1
    return durations


def _dedupe_platforms(platforms: list[MoviePlatform]) -> list[MoviePlatform]:
    return list(dict.fromkeys(platforms))
