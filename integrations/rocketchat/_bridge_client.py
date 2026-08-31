"""Minimal Rocket.Chat REST client used by the optional demo bridge."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request

from integrations.chat.rendering import split_markdown

from _bridge_common import USER_AGENT

class RocketChat:
    """Minimal Rocket.Chat REST client (login, read history, post message)."""

    def __init__(self, base: str, user: str, password: str) -> None:
        self.base = base.rstrip("/")
        self._user = user
        self._password = password
        self.token = ""
        self.user_id = ""

    def _call(self, path: str, data: dict | None = None, _retried: bool = False) -> dict:
        headers = {"User-Agent": USER_AGENT}
        if self.token:
            headers["X-Auth-Token"] = self.token
            headers["X-User-Id"] = self.user_id
        body = None
        if data is not None:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
        method = "POST" if data is not None else "GET"
        req = urllib.request.Request(self.base + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            # A 401 on an authenticated call usually means the session token expired.
            # Re-login once and retry so the poll loop does not go permanently deaf
            # (history() would otherwise return [] forever, indistinguishable from
            # "no new messages"). Guarded by _retried and by having a token, so the
            # unauthenticated login call itself can never recurse.
            if exc.code == 401 and self.token and not _retried:
                try:
                    self.login()
                except Exception:
                    return {"success": False, "http": 401, "body": "re-login failed"}
                return self._call(path, data, _retried=True)
            return {"success": False, "http": exc.code, "body": exc.read().decode()[:300]}

    def login(self) -> None:
        out = self._call("/api/v1/login", {"user": self._user, "password": self._password})
        if not out.get("success"):
            raise RuntimeError(f"Rocket.Chat login failed: {out}")
        self.token = out["data"]["authToken"]
        self.user_id = out["data"]["userId"]

    def resolve_room(self, name: str) -> tuple[str, str]:
        """Return (roomId, kind) for a channel by name; tries public then private."""
        q = urllib.parse.urlencode({"roomName": name})
        info = self._call(f"/api/v1/channels.info?{q}")
        if info.get("success"):
            return info["channel"]["_id"], "channels"
        info = self._call(f"/api/v1/groups.info?{q}")
        if info.get("success"):
            return info["group"]["_id"], "groups"
        raise RuntimeError(f"Channel '{name}' not found (as public or private). Detail: {info}")

    def resolve_dm(self, username: str) -> tuple[str, str]:
        """Return (roomId, 'im') for a direct message with `username`.

        Works without any channel-creation rights (im.create is allowed for normal
        users). Pass your own username for a self-DM ("Saved Messages") demo.
        """
        out = self._call("/api/v1/im.create", {"username": username})
        if out.get("success"):
            return out["room"]["_id"], "im"
        raise RuntimeError(f"Could not open DM with '{username}'. Detail: {out}")

    def history(self, kind: str, room_id: str, oldest: str) -> list[dict]:
        q = urllib.parse.urlencode({"roomId": room_id, "oldest": oldest, "count": 50})
        out = self._call(f"/api/v1/{kind}.history?{q}")
        if not out.get("success"):
            return []
        # Rocket.Chat returns newest-first; sort ascending by timestamp.
        return sorted(out.get("messages", []), key=lambda m: m.get("ts", ""))

    def post(self, room_id: str, text: str) -> None:
        for chunk in split_markdown(text, 4500):
            out = self._call("/api/v1/chat.postMessage", {"roomId": room_id, "text": chunk})
            # Surface a rejected post instead of silently dropping it: a swallowed
            # failure here is how a partial answer (e.g. a missing table) reaches the
            # user with no sign anything went wrong.
            if not out.get("success", True):
                sys.stderr.write(
                    f"[warn] post to {room_id} rejected: http={out.get('http')} "
                    f"{str(out.get('body', ''))[:160]}\n"
                )

    def delete_message(self, room_id: str, msg_id: str) -> dict:
        """Delete one message as the logged-in user (works for own messages when
        the server allows message deleting; others' need admin/force-delete)."""
        return self._call("/api/v1/chat.delete", {"roomId": room_id, "msgId": msg_id, "asUser": True})

    def _all_message_ids(self, kind: str, room_id: str, max_pages: int = 200) -> list[str]:
        """Collect every message id by paging backwards through history with the
        `latest` cursor (collect-then-delete avoids getting stuck on undeletable
        messages mid-sweep)."""
        ids: list[str] = []
        seen: set[str] = set()
        latest = ""
        for _ in range(max_pages):
            params = {"roomId": room_id, "count": 100}
            if latest:
                params["latest"] = latest
            out = self._call(f"/api/v1/{kind}.history?{urllib.parse.urlencode(params)}")
            batch = out.get("messages", []) if out.get("success") else []
            if not batch:
                break
            for m in batch:
                mid = m.get("_id")
                if mid and mid not in seen:
                    seen.add(mid)
                    ids.append(mid)
            oldest_ts = min(m.get("ts", "") for m in batch)
            if oldest_ts == latest:  # no progress -> stop
                break
            latest = oldest_ts
        return ids

    def clear_history(self, kind: str, room_id: str) -> tuple[int, int]:
        """Delete all messages the account can delete. Returns (deleted, skipped).
        In a self-DM every message is the account's own, so this clears it fully;
        in a shared channel only the account's own messages are removed."""
        deleted = skipped = 0
        for mid in self._all_message_ids(kind, room_id):
            if self.delete_message(room_id, mid).get("success"):
                deleted += 1
            else:
                skipped += 1
        return deleted, skipped

    def upload(self, room_id: str, filename: str, content: bytes, ctype: str, caption: str = "") -> dict:
        """Upload a file to a room. Rocket.Chat 7 removed the legacy
        `rooms.upload` in favor of the two-step `rooms.media` + `mediaConfirm`
        flow; use the modern flow and fall back to legacy on a 404 (old server)."""
        res = self._post_file(f"/api/v1/rooms.media/{room_id}", filename, content, ctype)
        file_id = (res.get("file") or {}).get("_id", "")
        if res.get("success") and file_id:
            return self._call(f"/api/v1/rooms.mediaConfirm/{room_id}/{file_id}",
                              {"msg": caption} if caption else {})
        if res.get("http") == 404:  # pre-6.x server without rooms.media
            return self._post_file(f"/api/v1/rooms.upload/{room_id}", filename, content, ctype, caption)
        return res

    def _post_file(self, path: str, filename: str, content: bytes, ctype: str, caption: str = "") -> dict:
        """One multipart/form-data POST of a file (plus an optional msg part)."""
        boundary = "----saleswikiBRIDGEboundary7e3a91"
        crlf = "\r\n"
        parts: list[bytes] = []
        if caption:
            parts.append(
                f'--{boundary}{crlf}Content-Disposition: form-data; name="msg"{crlf}{crlf}{caption}{crlf}'.encode()
            )
        parts.append(
            (f'--{boundary}{crlf}Content-Disposition: form-data; name="file"; filename="{filename}"{crlf}'
             f"Content-Type: {ctype}{crlf}{crlf}").encode()
            + content + crlf.encode()
        )
        parts.append(f"--{boundary}--{crlf}".encode())
        body = b"".join(parts)
        headers = {
            "User-Agent": USER_AGENT,
            "X-Auth-Token": self.token,
            "X-User-Id": self.user_id,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        req = urllib.request.Request(self.base + path, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            return {"success": False, "http": exc.code, "body": exc.read().decode()[:300]}
