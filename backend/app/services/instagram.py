"""Instagram Graph API — Reels posting with container polling."""
import asyncio, httpx, logging
from typing import Optional

logger = logging.getLogger(__name__)
IG_API = "https://graph.facebook.com/v18.0"


async def _create_container(client, ig_account_id, access_token, **params) -> Optional[str]:
    r = await client.post(f"{IG_API}/{ig_account_id}/media",
                          data={"access_token": access_token, **params})
    if r.status_code != 200:
        logger.error(f"Container create failed: {r.json()}")
        return None
    return r.json().get("id")


async def _wait_ready(client, container_id, access_token, max_wait=120) -> bool:
    import time
    t0 = time.time()
    while time.time() - t0 < max_wait:
        r = await client.get(f"{IG_API}/{container_id}",
                             params={"fields": "status_code", "access_token": access_token})
        if r.status_code == 200:
            sc = r.json().get("status_code", "")
            if sc == "FINISHED": return True
            if sc == "ERROR": return False
        await asyncio.sleep(5)
    return False


async def _publish(client, ig_account_id, container_id, access_token) -> Optional[str]:
    r = await client.post(f"{IG_API}/{ig_account_id}/media_publish",
                          data={"creation_id": container_id, "access_token": access_token})
    if r.status_code != 200:
        logger.error(f"Publish failed: {r.json()}")
        return None
    return r.json().get("id")


async def post_to_instagram(ig_account_id: str, access_token: str, image_url: str, caption: str) -> dict:
    async with httpx.AsyncClient(timeout=60) as client:
        cid = await _create_container(client, ig_account_id, access_token, image_url=image_url, caption=caption)
        if not cid: return {"success": False, "post_id": None, "error": "Container creation failed"}
        pid = await _publish(client, ig_account_id, cid, access_token)
        return {"success": bool(pid), "post_id": pid, "error": None if pid else "Publish failed"}


async def post_reel_to_instagram(ig_account_id: str, access_token: str, video_url: str, caption: str) -> dict:
    async with httpx.AsyncClient(timeout=180) as client:
        logger.info(f"Creating Reel container for {ig_account_id}")
        cid = await _create_container(client, ig_account_id, access_token,
                                      media_type="REELS", video_url=video_url,
                                      caption=caption, share_to_feed="true")
        if not cid: return {"success": False, "post_id": None, "error": "Container creation failed"}

        logger.info(f"Waiting for container {cid}…")
        if not await _wait_ready(client, cid, access_token):
            return {"success": False, "post_id": None, "error": "Container timed out"}

        pid = await _publish(client, ig_account_id, cid, access_token)
        if pid: logger.info(f"Reel published: {pid}")
        return {"success": bool(pid), "post_id": pid, "error": None if pid else "Publish failed"}
