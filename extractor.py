from __future__ import annotations

from typing import Any

import yt_dlp
from fastapi.concurrency import run_in_threadpool


class ExtractorError(Exception):
    """Raised when metadata extraction fails."""


class YtdlpExtractor:
    def __init__(self) -> None:
        self.base_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "extract_flat": False,
            "socket_timeout": 20,
            "nocheckcertificate": True,
            "geo_bypass": True,
            "cachedir": False,
        }

    async def get_video_info(self, url: str) -> dict[str, Any]:
        info = await self._extract(url)
        formats = self._valid_formats(info)

        resolutions = sorted({f"{f['height']}p" for f in formats if f.get("height")}, key=lambda r: int(r[:-1]))

        return {
            "title": info.get("title", ""),
            "thumbnail": info.get("thumbnail", ""),
            "duration": self._format_duration(info.get("duration")),
            "tags": info.get("tags") or [],
            "available_resolutions": resolutions,
            "formats": [
                {
                    "format_id": f.get("format_id"),
                    "ext": f.get("ext"),
                    "resolution": f"{f['height']}p" if f.get("height") else None,
                    "fps": f.get("fps"),
                    "vcodec": f.get("vcodec"),
                    "acodec": f.get("acodec"),
                    "filesize": f.get("filesize") or f.get("filesize_approx"),
                }
                for f in formats
            ],
        }

    async def get_video_download_url(self, url: str, resolution: str) -> dict[str, str]:
        info = await self._extract(url)
        target_height = self._resolution_to_height(resolution)
        selected = self._choose_video_format(info, target_height)
        stream_url = selected.get("url")

        if not stream_url:
            raise ExtractorError("No direct stream URL available for selected format.")

        return {
            "download_url": stream_url,
            "resolution": f"{selected['height']}p" if selected.get("height") else resolution,
        }

    async def get_audio_download_url(self, url: str) -> dict[str, str]:
        info = await self._extract(url)
        audio = self._choose_audio_format(info)
        stream_url = audio.get("url")

        if not stream_url:
            raise ExtractorError("No direct audio stream URL available.")

        return {
            "download_url": stream_url,
            "type": "mp3",
        }

    async def get_thumbnail(self, url: str) -> dict[str, str]:
        info = await self._extract(url)
        return {"thumbnail": info.get("thumbnail", "")}

    async def get_call_preview(self, url: str) -> dict[str, Any]:
        info = await self._extract(url)
        return {
            "title": info.get("title", ""),
            "thumbnail": info.get("thumbnail", ""),
            "tags": info.get("tags") or [],
        }

    async def _extract(self, url: str) -> dict[str, Any]:
        try:
            return await run_in_threadpool(self._extract_sync, url)
        except yt_dlp.utils.DownloadError as exc:
            raise ExtractorError("Unable to extract media info for this URL.") from exc
        except Exception as exc:
            raise ExtractorError("Unexpected extraction error.") from exc

    def _extract_sync(self, url: str) -> dict[str, Any]:
        with yt_dlp.YoutubeDL(self.base_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if "entries" in info and info["entries"]:
            info = next((entry for entry in info["entries"] if entry), None) or {}

        if not info:
            raise ExtractorError("No media information found.")

        return info

    def _valid_formats(self, info: dict[str, Any]) -> list[dict[str, Any]]:
        formats = info.get("formats") or []
        return [f for f in formats if f.get("url") and (f.get("height") or f.get("acodec") != "none")]

    def _choose_video_format(self, info: dict[str, Any], target_height: int) -> dict[str, Any]:
        formats = self._valid_formats(info)

        muxed = [
            f
            for f in formats
            if f.get("vcodec") not in (None, "none") and f.get("acodec") not in (None, "none") and f.get("height")
        ]

        if not muxed:
            raise ExtractorError("No downloadable muxed video format available.")

        eligible = [f for f in muxed if int(f.get("height", 0)) <= target_height]
        pool = eligible if eligible else muxed

        return sorted(pool, key=lambda f: int(f.get("height") or 0), reverse=True)[0]

    def _choose_audio_format(self, info: dict[str, Any]) -> dict[str, Any]:
        formats = self._valid_formats(info)

        audio_only = [f for f in formats if f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none")]

        if audio_only:
            # Higher abr is generally better for mp3 conversion quality.
            return sorted(audio_only, key=lambda f: float(f.get("abr") or 0), reverse=True)[0]

        muxed = [f for f in formats if f.get("acodec") not in (None, "none")]
        if not muxed:
            raise ExtractorError("No downloadable audio format available.")

        return sorted(muxed, key=lambda f: float(f.get("abr") or 0), reverse=True)[0]

    @staticmethod
    def _resolution_to_height(resolution: str) -> int:
        try:
            return int(resolution.rstrip("p"))
        except ValueError as exc:
            raise ExtractorError("Invalid resolution format. Use values like 720p.") from exc

    @staticmethod
    def _format_duration(seconds: int | None) -> str:
        if not seconds:
            return ""
        hours, rem = divmod(int(seconds), 3600)
        mins, secs = divmod(rem, 60)
        if hours:
            return f"{hours:02}:{mins:02}:{secs:02}"
        return f"{mins:02}:{secs:02}"
