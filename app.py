"""ROAST MY GITHUB - Flask backend.

GitHub facts -> Jev judgments -> template roast -> ElevenLabs voice.
All API keys are read server-side from the environment; nothing is exposed
to the browser.
"""

from __future__ import annotations

import os
import time
from collections import OrderedDict
from threading import Lock

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file
from werkzeug.exceptions import HTTPException

import github_facts
import jev
import roast
import tts

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="/static")

CACHE_SIZE = 10
CACHE_TTL_SECONDS = 15 * 60
_cache: "OrderedDict[tuple[str, str], tuple[float, dict]]" = OrderedDict()
_cache_lock = Lock()


def _cache_get(key: tuple[str, str]) -> dict | None:
    with _cache_lock:
        entry = _cache.get(key)
        if not entry:
            return None
        created, payload = entry
        if time.time() - created > CACHE_TTL_SECONDS:
            del _cache[key]
            return None
        _cache.move_to_end(key)
        return payload


def _cache_put(key: tuple[str, str], payload: dict) -> None:
    with _cache_lock:
        _cache[key] = (time.time(), payload)
        _cache.move_to_end(key)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)


@app.get("/")
def index():
    return send_file("templates/index.html")


@app.get("/api/health")
def health():
    return jsonify(
        {
            "ok": True,
            "jev_key": bool(os.environ.get("TYPESAFE_API_KEY")),
            "elevenlabs_key": bool(os.environ.get("ELEVENLABS_API_KEY")),
            "github_token": bool(os.environ.get("GITHUB_TOKEN")),
            "cached_roasts": len(_cache),
        }
    )


@app.post("/api/roast")
def create_roast():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip().lstrip("@")
    spice = (body.get("spice") or roast.DEFAULT_SPICE).lower()

    if not username or len(username) > 39 or not username.replace("-", "").isalnum():
        return (
            jsonify(
                {
                    "error": "That's not a GitHub username. That's a keyboard accident.",
                }
            ),
            400,
        )

    key = (username.lower(), spice)
    cached = _cache_get(key)
    if cached:
        return jsonify({**cached, "cached": True})

    try:
        facts = github_facts.collect_facts(username)
    except github_facts.GitHubError as exc:
        return jsonify({"error": exc.message}), exc.status

    try:
        verdicts = jev.judge(facts)
    except jev.JevError as exc:
        app.logger.warning("Jev failed: %s", exc)
        return (
            jsonify(
                {
                    "error": "Jev is unavailable, and without Jev this is just a "
                    "stranger reading your repo names out loud. Try again shortly.",
                }
            ),
            503,
        )

    lines = roast.generate_roast(facts, verdicts, spice)
    payload = {
        "username": facts["username"],
        "spice": spice if spice in roast.SPICE_LEVELS else roast.DEFAULT_SPICE,
        "facts": facts,
        "jev": verdicts,
        "roast": lines,
        "tombstone": _tombstone(facts, verdicts),
        "cached": False,
    }
    _cache_put(key, payload)
    return jsonify(payload)


@app.errorhandler(Exception)
def unexpected(exc):
    if isinstance(exc, HTTPException):
        return exc
    app.logger.exception("Unhandled error", exc_info=exc)
    return (
        jsonify(
            {
                "error": "Something in our roasting machinery caught fire. "
                "Ironic. Try again.",
            }
        ),
        500,
    )


def _tombstone(facts: dict, verdicts: dict) -> dict | None:
    name = verdicts["most_embarrassing_repo"]["repo"]
    if not name:
        return None
    repo = next((r for r in facts["recent_repos"] if r["name"] == name), None)
    if not repo:
        return None

    def month_year(stamp: str | None) -> str:
        if not stamp:
            return "???"
        return f"{stamp[5:7]}/{stamp[0:4]}"

    return {
        "repo": name,
        "born": month_year(repo.get("created_at")),
        "died": month_year(repo.get("pushed_at")),
        "commits": repo.get("commits_seen"),
        "confidence": verdicts["most_embarrassing_repo"]["confidence"],
    }


@app.post("/api/voice")
def voice():
    body = request.get_json(silent=True) or {}
    lines = body.get("lines") or []
    if not isinstance(lines, list) or not lines:
        return jsonify({"error": "Nothing to read out loud."}), 400

    text = "\n\n".join(str(line) for line in lines)[:4000]
    try:
        audio, voice_id = tts.speak(text)
    except tts.VoiceError as exc:
        return jsonify({"error": str(exc)}), 503

    response = send_file(audio, mimetype="audio/mpeg", download_name="roast.mp3")
    response.headers["X-Voice-Id"] = voice_id
    return response


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
