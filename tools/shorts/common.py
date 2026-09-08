# -*- coding: utf-8 -*-
"""shorts生成パイプライン共通ヘルパー。パス・APIキー・記事読み込みをここに集約する。"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent  # fx-compass/
SHORTS_DIR = pathlib.Path(__file__).resolve().parent  # tools/shorts/
OUT_ROOT = SHORTS_DIR / "out"
ARTICLES_JSON = ROOT / "data" / "articles.json"
API_KEY_FILE = ROOT.parent / "API" / "gemini_API.txt"

BRAND_NAVY_DARK = "#0A1E4E"
BRAND_NAVY = "#1E3A8A"
BRAND_SKY = "#9DB8F5"
BRAND_WHITE = "#FFFFFF"

SITE_URL = "yocchan-fx.com"


def load_api_key() -> str:
    if not API_KEY_FILE.exists():
        raise FileNotFoundError(f"Gemini APIキーが見つかりません: {API_KEY_FILE}")
    return API_KEY_FILE.read_text(encoding="utf-8").strip()


def load_latest_article() -> dict:
    articles = json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
    if not articles:
        raise ValueError("articles.json が空です")
    return articles[0]  # 先頭が最新


def article_out_dir(article: dict) -> pathlib.Path:
    art_id = article.get("id") or "untitled"
    out_dir = OUT_ROOT / art_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir
