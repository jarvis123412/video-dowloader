from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from extractor import ExtractorError, YtdlpExtractor

app = FastAPI(title="video-api", version="1.0.0")
extractor = YtdlpExtractor()


class UrlRequest(BaseModel):
    url: HttpUrl


class VideoDownloadRequest(BaseModel):
    url: HttpUrl
    resolution: str = Field(default="720p", pattern=r"^\d+p$")


@app.get("/")
async def root() -> dict[str, str]:
    return {"status": "running"}


@app.post("/api/video/info")
async def video_info(payload: UrlRequest) -> dict:
    try:
        return await extractor.video_info(str(payload.url))
    except ExtractorError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc


@app.post("/api/video/download")
async def video_download(payload: VideoDownloadRequest) -> dict:
    try:
        return await extractor.video_download(str(payload.url), payload.resolution)
    except ExtractorError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc


@app.post("/api/audio/download")
async def audio_download(payload: UrlRequest) -> dict:
    try:
        return await extractor.audio_download(str(payload.url))
    except ExtractorError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc


@app.post("/api/video/call-preview")
async def call_preview(payload: UrlRequest) -> dict:
    try:
        return await extractor.call_preview(str(payload.url))
    except ExtractorError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)}) from exc
