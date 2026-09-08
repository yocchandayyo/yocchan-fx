# -*- coding: utf-8 -*-
"""最新記事から、ヨル教授のショート動画台本(60秒以内)を作る。

articles.json の先頭(=最新)記事の points / leadPara の範囲だけを使って
Gemini(gemini-2.5-flash)に台本を書かせる。本文の数値やエピソードを
勝手に足さないよう、モデルに渡す材料自体を points と leadPara に絞る。

出力:
    tools/shorts/out/<記事id>/script.txt   ... 読み上げ用の台本(地の文)
    tools/shorts/out/<記事id>/captions.json ... 画面表示用の短い字幕リスト

使い方:
    python tools/shorts/make_script.py
"""
import json

from google import genai
from google.genai import types

from common import load_api_key, load_latest_article, article_out_dir

SCRIPT_MIN_CHARS = 210
SCRIPT_MAX_CHARS = 300
CAPTION_MAX_CHARS = 20
CAPTION_MIN_LINES = 8
CAPTION_MAX_LINES = 12

SYSTEM_RULES = """あなたは「よっちゃんのFX」というFXメディアのマスコット、ヨル教授(眼鏡のフクロウ)です。
YouTube Shorts / TikTok用の縦型ショート動画(45〜60秒でナレーターが読み上げる想定)の台本を書きます。

## ヨル教授の口調ルール(必ず守る)
- 一人称は「私」。読者は「皆さん」
- です・ます調が基本
- 断定しない。「〜と見ています」「〜になりやすい」「〜を見ておきたい」の温度で止める
- 事実は伝聞で書く(「〜と報じられています」「〜だそうです」)。ただし今回渡す材料は
  すでに事実確認された要点なので、そのまま噛み砕いて話してよい
- 数字は銭単位まで律儀に言う(例: 159円48銭)
- 皮肉やウィットは一滴だけ。嫌味にはしない

## コンプライアンス(絶対厳守)
- 「必ず」「絶対」「勝てる」「爆益」などの断定・煽り表現は禁止
- 「今すぐ買い」「ここでショート」のような具体的な売買指示は禁止
- 相場の断定(「〜するのは確実」)は禁止
- 台本の最後に必ず「投資は自己判断で」という趣旨の一言を自然な形で入れる

## 台本の構成(この順番を守る)
1. 冒頭は必ずこの一文から始める: 「おはようございます、ヨル教授です。」
2. 渡された要点(points)を、視聴者に語りかけるように噛み砕いて説明する。数値は要点にある表記をそのまま使う
3. 締めの一言。断定・煽り・売買指示はせず、「投資は自己判断で」という趣旨を自然に添えて終える

## 厳守事項
- 台本に書いてよい事実は、渡された leadPara と points の範囲だけ。そこに無い数値やエピソードを新しく作らない
- 全体で210〜300文字程度(日本語の文字数)。60秒で読み切れる分量に収める
- 音声合成でそのまま読み上げるので、絵文字・記号・見出し記号("1."など)は入れない。自然な話し言葉の文章だけを書く

## 字幕(captions)の作り方
- 台本の内容を、画面に大きく出す字幕用に短く区切る
- 1行は全角20文字以内。8〜12行になるように分割する
- 台本と同じ順番で、台本の意味をそのまま短くしたもの(要約しすぎて意味を変えない)
- 字幕にも絵文字や記号は入れない
"""

RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "script": types.Schema(type=types.Type.STRING),
        "captions": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
        ),
    },
    required=["script", "captions"],
)


def build_prompt(article: dict) -> str:
    points = article.get("points") or []
    lead = article.get("leadPara") or article.get("lead") or ""
    title = article.get("title") or ""
    date = article.get("date") or ""
    lines = [
        f"記事タイトル: {title}",
        f"日付: {date}",
        f"leadPara: {lead}",
        "points:",
    ]
    for i, p in enumerate(points, 1):
        lines.append(f"  {i}. {p}")
    return "\n".join(lines)


def generate(article: dict) -> dict:
    client = genai.Client(api_key=load_api_key())
    prompt = build_prompt(article)
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_RULES,
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
            temperature=0.8,
        ),
    )
    data = json.loads(resp.text)
    return data


def validate(data: dict) -> list:
    """明らかにおかしい場合だけ警告を返す(厳密なリトライループはしない)。"""
    warnings = []
    script = data.get("script", "")
    n = len(script)
    if not (SCRIPT_MIN_CHARS - 40 <= n <= SCRIPT_MAX_CHARS + 60):
        warnings.append(f"台本の文字数が想定外: {n}字")
    captions = data.get("captions", [])
    if not (CAPTION_MIN_LINES - 2 <= len(captions) <= CAPTION_MAX_LINES + 2):
        warnings.append(f"字幕の行数が想定外: {len(captions)}行")
    for c in captions:
        if len(c) > CAPTION_MAX_CHARS + 4:
            warnings.append(f"字幕が長すぎる行: {c!r}")
    if "自己判断" not in script:
        warnings.append("台本に「投資は自己判断で」の趣旨が見当たらない")
    return warnings


def main():
    article = load_latest_article()
    out_dir = article_out_dir(article)
    print(f"記事: {article.get('title')} ({article.get('id')})")

    data = generate(article)
    warnings = validate(data)
    for w in warnings:
        print(f"  ! 警告: {w}")

    script_path = out_dir / "script.txt"
    captions_path = out_dir / "captions.json"
    script_path.write_text(data["script"].strip(), encoding="utf-8")
    captions_path.write_text(
        json.dumps(data["captions"], ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"  -> {script_path} ({len(data['script'])}字)")
    print(f"  -> {captions_path} ({len(data['captions'])}行)")


if __name__ == "__main__":
    main()
