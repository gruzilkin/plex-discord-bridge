import logging

import aiohttp
from aiohttp import web
from pydantic import ValidationError

from .config import settings
from .models import PlexMetadata, PlexWebhookPayload

log = logging.getLogger(__name__)

ALLOWED_EVENTS = {"media.play", "media.scrobble", "library.new"}
ALLOWED_LIBRARY_TYPES = {"movie", "show"}

EVENT_VERBS = {
    "media.play": "started watching",
    "media.scrobble": "finished watching",
    "library.new": "added to library",
}


def _extract_imdb_url(metadata: PlexMetadata) -> str | None:
    if not metadata.Guid:
        return None
    for guid in metadata.Guid:
        if guid.id.startswith("imdb://"):
            imdb_id = guid.id.removeprefix("imdb://")
            return f"https://www.imdb.com/title/{imdb_id}/"
    return None


def _format_title(payload: PlexWebhookPayload) -> str:
    meta = payload.Metadata
    if meta.type == "episode":
        season = f"S{meta.parentIndex:02d}" if meta.parentIndex is not None else ""
        episode = f"E{meta.index:02d}" if meta.index is not None else ""
        show = meta.grandparentTitle or ""
        return f"{show} — {season}{episode} {meta.title}"
    return meta.title


def _build_message(payload: PlexWebhookPayload) -> str:
    verb = EVENT_VERBS.get(payload.event, payload.event)
    title = _format_title(payload)
    imdb_url = _extract_imdb_url(payload.Metadata)

    if payload.event == "library.new":
        parts = [f"**{title}** {verb}"]
    else:
        parts = [f"**{payload.Account.title}** {verb} **{title}**"]

    if imdb_url:
        parts.append(imdb_url)

    return "\n".join(parts)


async def _post_to_discord(message: str) -> None:
    try:
        async with aiohttp.ClientSession() as session:
            resp = await session.post(settings.discord_webhook_url, json={"content": message})
            if resp.status >= 300:
                body = await resp.text()
                log.error("Discord responded %s: %s", resp.status, body)
    except Exception:
        log.exception("Failed to post to Discord")


async def handle_webhook(request: web.Request) -> web.Response:
    try:
        reader = await request.multipart()
    except Exception:
        log.warning("Request is not valid multipart")
        return web.Response(status=400, text="expected multipart form data")

    payload_text = None
    async for part in reader:
        if part.name == "payload":
            payload_text = await part.text()
            break

    if payload_text is None:
        log.warning("No 'payload' part in multipart request")
        return web.Response(status=400, text="missing payload part")

    try:
        payload = PlexWebhookPayload.model_validate_json(payload_text)
    except ValidationError as exc:
        log.warning("Invalid payload: %s", exc)
        return web.Response(status=400, text="invalid payload")

    log.info("Plex webhook: %s", payload.model_dump_json())

    if payload.event not in ALLOWED_EVENTS:
        return web.Response(status=200)

    if payload.Metadata.librarySectionType not in ALLOWED_LIBRARY_TYPES:
        return web.Response(status=200)

    message = _build_message(payload)
    log.info("Discord message: %s", message)
    await _post_to_discord(message)
    return web.Response(status=200)
