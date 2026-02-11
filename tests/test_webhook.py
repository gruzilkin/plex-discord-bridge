from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import MultipartWriter, web
from aiohttp.test_utils import TestClient, TestServer

from plex_discord_bridge.handler import handle_webhook
from plex_discord_bridge.models import (
    PlexAccount,
    PlexGuid,
    PlexMetadata,
    PlexWebhookPayload,
)


@pytest.fixture
async def client():
    app = web.Application()
    app.router.add_post("/", handle_webhook)

    async with TestClient(TestServer(app)) as c:
        yield c


def _multipart(field_name: str, text: str) -> MultipartWriter:
    writer = MultipartWriter("form-data")
    part = writer.append(text)
    part.set_content_disposition("form-data", name=field_name)
    return writer


async def _post_payload(client: TestClient, payload: PlexWebhookPayload):
    mp = _multipart("payload", payload.model_dump_json())
    return await client.post("/", data=mp)


async def _post_raw(client: TestClient, field_name: str, text: str):
    mp = _multipart(field_name, text)
    return await client.post("/", data=mp)


# -- happy paths --


@pytest.mark.asyncio
@patch("plex_discord_bridge.handler._post_to_discord", new_callable=AsyncMock)
async def test_movie_play(mock_post, client: TestClient):
    payload = PlexWebhookPayload(
        event="media.play",
        Account=PlexAccount(title="Sergey"),
        Metadata=PlexMetadata(
            librarySectionType="movie",
            type="movie",
            title="Inception",
            Guid=[PlexGuid(id="imdb://tt1375666")],
        ),
    )
    resp = await _post_payload(client, payload)
    assert resp.status == 200

    mock_post.assert_called_once()
    msg = mock_post.call_args.args[0]
    assert "**Sergey** started watching **Inception**" in msg
    assert "https://www.imdb.com/title/tt1375666/" in msg


@pytest.mark.asyncio
@patch("plex_discord_bridge.handler._post_to_discord", new_callable=AsyncMock)
async def test_episode_scrobble(mock_post, client: TestClient):
    payload = PlexWebhookPayload(
        event="media.scrobble",
        Account=PlexAccount(title="Sergey"),
        Metadata=PlexMetadata(
            librarySectionType="show",
            type="episode",
            title="Más",
            grandparentTitle="Breaking Bad",
            parentIndex=3,
            index=5,
            Guid=[PlexGuid(id="imdb://tt1615547")],
        ),
    )
    resp = await _post_payload(client, payload)
    assert resp.status == 200

    msg = mock_post.call_args.args[0]
    assert "finished watching" in msg
    assert "Breaking Bad — S03E05 Más" in msg


@pytest.mark.asyncio
@patch("plex_discord_bridge.handler._post_to_discord", new_callable=AsyncMock)
async def test_library_new(mock_post, client: TestClient):
    payload = PlexWebhookPayload(
        event="library.new",
        Account=PlexAccount(title="Sergey"),
        Metadata=PlexMetadata(
            librarySectionType="movie",
            type="movie",
            title="The Bear",
        ),
    )
    resp = await _post_payload(client, payload)
    assert resp.status == 200

    msg = mock_post.call_args.args[0]
    assert msg.startswith("**The Bear** added to library")
    assert "Sergey" not in msg


# -- filtering --


@pytest.mark.asyncio
@patch("plex_discord_bridge.handler._post_to_discord", new_callable=AsyncMock)
async def test_disallowed_event_not_forwarded(mock_post, client: TestClient):
    payload = PlexWebhookPayload(
        event="media.pause",
        Account=PlexAccount(title="Sergey"),
        Metadata=PlexMetadata(
            librarySectionType="movie",
            type="movie",
            title="Inception",
        ),
    )
    resp = await _post_payload(client, payload)
    assert resp.status == 200
    mock_post.assert_not_called()


@pytest.mark.asyncio
@patch("plex_discord_bridge.handler._post_to_discord", new_callable=AsyncMock)
async def test_disallowed_library_type_not_forwarded(mock_post, client: TestClient):
    payload = PlexWebhookPayload(
        event="media.play",
        Account=PlexAccount(title="Sergey"),
        Metadata=PlexMetadata(
            librarySectionType="other",
            type="clip",
            title="Home Video",
        ),
    )
    resp = await _post_payload(client, payload)
    assert resp.status == 200
    mock_post.assert_not_called()


# -- error cases --


@pytest.mark.asyncio
async def test_bad_payload_returns_400(client: TestClient):
    resp = await _post_raw(client, "payload", '{"bad": "data"}')
    assert resp.status == 400


@pytest.mark.asyncio
async def test_missing_payload_part_returns_400(client: TestClient):
    resp = await _post_raw(client, "thumb", "binary-data-here")
    assert resp.status == 400


# -- edge cases --


@pytest.mark.asyncio
@patch("plex_discord_bridge.handler._post_to_discord", new_callable=AsyncMock)
async def test_no_imdb_guid_omits_link(mock_post, client: TestClient):
    payload = PlexWebhookPayload(
        event="media.play",
        Account=PlexAccount(title="Sergey"),
        Metadata=PlexMetadata(
            librarySectionType="movie",
            type="movie",
            title="Inception",
            Guid=[],
        ),
    )
    resp = await _post_payload(client, payload)
    assert resp.status == 200

    msg = mock_post.call_args.args[0]
    assert "imdb.com" not in msg
