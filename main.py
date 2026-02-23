from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from extractor import YtdlpExtractor, ExtractorError

app = FastAPI(
    title="Video Downloader API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

extractor = YtdlpExtractor()


class URLRequest(BaseModel):
    url: HttpUrl


class VideoDownloadRequest(BaseModel):
    url: HttpUrl
    resolution: str = Field(default="720p", pattern=r"^\d+p$")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/video/info")
async def video_info(payload: URLRequest) -> dict:
    try:
        return await extractor.get_video_info(str(payload.url))
    except ExtractorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/video/download")
async def video_download(payload: VideoDownloadRequest) -> dict:
    try:
        return await extractor.get_video_download_url(str(payload.url), payload.resolution)
    except ExtractorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/audio/download")
async def audio_download(payload: URLRequest) -> dict:
    try:
        return await extractor.get_audio_download_url(str(payload.url))
    except ExtractorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/video/thumbnail")
async def video_thumbnail(payload: URLRequest) -> dict:
    try:
        return await extractor.get_thumbnail(str(payload.url))
    except ExtractorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/video/call-preview")
async def call_preview(payload: URLRequest) -> dict:
    try:
        return await extractor.get_call_preview(str(payload.url))
    except ExtractorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
