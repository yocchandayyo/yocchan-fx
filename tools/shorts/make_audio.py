# -*- coding: utf-8 -*-
"""script.txt を Gemini TTS で読み上げ、voice.wav を作る。

使用モデル: gemini-2.5-flash-preview-tts
声: Charon(落ち着いた・informative寄りの男性寄りボイス)

使い方:
    python tools/shorts/make_audio.py
"""
import wave

from google import genai
from google.genai import types

from common import load_api_key, load_latest_article, article_out_dir

TTS_MODEL = "gemini-2.5-flash-preview-tts"
VOICE_NAME = "Charon"  # 落ち着いた・informative寄り。男性寄りの声

# Gemini TTS は 24kHz / 16bit / mono の raw PCM を返す
PCM_RATE = 24000
PCM_SAMPLE_WIDTH = 2
PCM_CHANNELS = 1

STYLE_PREFIX = (
    "落ち着いた声で、ゆっくりはっきりと、日本語のナレーションとして読んでください。"
    "感情を込めすぎず、講義のように静かなトーンで: "
)


def synthesize(script_text: str) -> bytes:
    client = genai.Client(api_key=load_api_key())
    resp = client.models.generate_content(
        model=TTS_MODEL,
        contents=STYLE_PREFIX + script_text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE_NAME)
                )
            ),
        ),
    )
    part = resp.candidates[0].content.parts[0]
    return part.inline_data.data


def write_wav(pcm_bytes: bytes, out_path):
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(PCM_CHANNELS)
        wf.setsampwidth(PCM_SAMPLE_WIDTH)
        wf.setframerate(PCM_RATE)
        wf.writeframes(pcm_bytes)


def main():
    article = load_latest_article()
    out_dir = article_out_dir(article)
    script_path = out_dir / "script.txt"
    if not script_path.exists():
        raise FileNotFoundError(f"先に make_script.py を実行してください: {script_path}")

    script_text = script_path.read_text(encoding="utf-8").strip()
    print(f"台本を読み上げ中... ({len(script_text)}字, voice={VOICE_NAME})")

    pcm = synthesize(script_text)
    wav_path = out_dir / "voice.wav"
    write_wav(pcm, wav_path)

    duration_sec = len(pcm) / (PCM_RATE * PCM_SAMPLE_WIDTH * PCM_CHANNELS)
    print(f"  -> {wav_path} ({duration_sec:.1f}秒)")


if __name__ == "__main__":
    main()
