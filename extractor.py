from __future__ import annotations

import asyncio
from typing import Any

import yt_dlp
from fastapi.concurrency import run_in_threadpool


class ExtractorError(Exception):
    pass


class YtdlpExtractor:
    def __init__(self) -> None:
        self.ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "geo_bypass": True,
            "cachedir": False,
            "socket_timeout": 25,
            "retries": 1,
        }

    async def video_info(self, url: str) -> dict[str, Any]:
        info = await self._extract(url)
        formats = self._formats(info)
        resolutions = sorted({f"{f['height']}p" for f in formats if f.get("height")}, key=lambda x: int(x[:-1]))
        return {
            "title": info.get("title", ""),
            "thumbnail": info.get("thumbnail", ""),
            "tags": info.get("tags") or [],
            "duration": self._format_duration(info.get("duration")),
            "available_resolutions": resolutions,
        }

    async def video_download(self, url: str, resolution: str) -> dict[str, str]:
        target_height = self._parse_resolution(resolution)
        info = await self._extract(url)
        selected = self._select_video_format(info, target_height)
        direct_url = selected.get("url")
        if not direct_url:
            raise ExtractorError("missing formats")
        return {
            "download_url": direct_url,
            "resolution": f"{selected.get('height')}p" if selected.get("height") else resolution,
        }

    async def audio_download(self, url: str) -> dict[str, str]:
        info = await self._extract(url)
        selected = self._select_audio_format(info)
        direct_url = selected.get("url")
        if not direct_url:
            raise ExtractorError("missing formats")
        return {"download_url": direct_url, "type": "mp3"}

    async def call_preview(self, url: str) -> dict[str, Any]:
        info = await self._extract(url)
        return {
            "title": info.get("title", ""),
            "thumbnail": info.get("thumbnail", ""),
            "tags": info.get("tags") or [],
        }

    async def _extract(self, url: str) -> dict[str, Any]:
        try:
            return await asyncio.wait_for(run_in_threadpool(self._extract_sync, url), timeout=55)
        except asyncio.TimeoutError as exc:
            raise ExtractorError("timeout") from exc
        except yt_dlp.utils.DownloadError as exc:
            message = str(exc).lower()
            if "unsupported" in message:
                raise ExtractorError("unsupported platform") from exc
            if "url" in message:
                raise ExtractorError("invalid url") from exc
            raise ExtractorError("unable to extract media") from exc
        except ExtractorError:
            raise
        except Exception as exc:
            raise ExtractorError("unable to extract media") from exc

    def _extract_sync(self, url: str) -> dict[str, Any]:
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            data = ydl.extract_info(url, download=False)

        if not data:
            raise ExtractorError("unsupported platform")

        if isinstance(data, dict) and data.get("entries"):
            data = next((item for item in data["entries"] if item), None)

        if not data:
            raise ExtractorError("unsupported platform")

        return data

    def _formats(self, info: dict[str, Any]) -> list[dict[str, Any]]:
        return [f for f in (info.get("formats") or []) if f.get("url")]

    def _select_video_format(self, info: dict[str, Any], target_height: int) -> dict[str, Any]:
        formats = self._formats(info)
        muxed = [
            f
            for f in formats
            if f.get("height") and f.get("vcodec") not in (None, "none") and f.get("acodec") not in (None, "none")
        ]
        if not muxed:
            raise ExtractorError("missing formats")
        eligible = [f for f in muxed if int(f.get("height") or 0) <= target_height]
        pool = eligible or muxed
        return sorted(pool, key=lambda x: int(x.get("height") or 0), reverse=True)[0]

    def _select_audio_format(self, info: dict[str, Any]) -> dict[str, Any]:
        formats = self._formats(info)
        audio_only = [
            f for f in formats if f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none")
        ]
        if audio_only:
            return sorted(audio_only, key=lambda x: float(x.get("abr") or 0), reverse=True)[0]
        fallback = [f for f in formats if f.get("acodec") not in (None, "none")]
        if not fallback:
            raise ExtractorError("missing formats")
        return sorted(fallback, key=lambda x: float(x.get("abr") or 0), reverse=True)[0]

    @staticmethod
    def _parse_resolution(value: str) -> int:
        try:
            return int(value.rstrip("p"))
        except Exception as exc:
            raise ExtractorError("invalid resolution") from exc

    @staticmethod
    def _format_duration(seconds: int | None) -> str:
        if not seconds:
            return ""
        minutes, sec = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02}:{minutes:02}:{sec:02}"
        return f"{minutes:02}:{sec:02}"
