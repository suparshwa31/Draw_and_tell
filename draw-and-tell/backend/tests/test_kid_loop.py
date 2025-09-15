import io
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.kid_loop import router


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestKidLoopRouter:
    def test_get_prompt_returns_valid_prompt_schema(self, client, mocker):
        mocker.patch(
            "backend.services.prompt_service.PromptService.generate_drawing_prompt",
            new=lambda: "Draw two happy cats."
        )
        resp = client.get("/prompt")
        assert resp.status_code == 200
        data = resp.json()
        assert "prompt" in data
        assert isinstance(data["prompt"], str)
        assert data["prompt"] != ""

    def test_post_asr_llm_returns_transcript_and_llm_response(self, client):
        files = {"audio": ("sample.wav", b"FAKE WAV DATA", "audio/wav")}
        resp = client.post("/asr-llm", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert "transcript" in data
        assert "llm_response" in data
        assert isinstance(data["transcript"], str)
        assert isinstance(data["llm_response"], str)

    def test_get_tts_stream_returns_audio_stream_with_wav_media_type(self, client):
        resp = client.get("/tts-stream", params={"text": "hello"})
        assert resp.status_code == 200
        assert "audio/wav" in resp.headers.get("content-type", "")
        assert resp.content == b"FAKE AUDIO DATA"

    def test_get_prompt_generation_error_returns_500(self, client, mocker):
        mocker.patch(
            "backend.services.prompt_service.PromptService.generate_drawing_prompt",
            side_effect=Exception("generation failed")
        )
        resp = client.get("/prompt")
        assert resp.status_code == 500

    def test_post_image_check_missing_file_returns_422(self, client):
        resp = client.post("/image-check")
        assert resp.status_code == 422

    def test_get_tts_stream_missing_text_returns_422(self, client):
        resp = client.get("/tts-stream")
        assert resp.status_code == 422