# -*- coding: utf-8 -*-
"""script.txt / captions.json / voice.wav から縦型ショート動画(1080x1920)を組み立てる。

構成:
- 冒頭2秒: 記事タイトルのカード
- 以降: captions.json の各行を、音声の長さを行数で均等割りした時間だけ表示
- 上部: ヨル教授アイコン(丸抜き) + 「よっちゃんのFX」
- 下部: 日付 + yocchan-fx.com
- 背景: 紺のグラデーション。BGM無し

Pillowで静止画スライドを書き出し、ffmpeg(concat demuxer)で音声と結合する。
1本あたりのスライド枚数は少ない(intro+8〜12枚程度)ので数秒で終わる。

使い方:
    python tools/shorts/make_video.py
"""
import subprocess
import wave

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

from common import (
    load_latest_article,
    article_out_dir,
    BRAND_NAVY_DARK,
    BRAND_NAVY,
    BRAND_SKY,
    BRAND_WHITE,
    SITE_URL,
    ROOT,
)

W, H = 1080, 1920
FPS = 30
INTRO_SEC = 2.0

WIN_FONTS = "C:/Windows/Fonts"
FONT_CANDIDATES = {
    "bold": [f"{WIN_FONTS}/NotoSansJP-Bold.ttf", f"{WIN_FONTS}/meiryob.ttc"],
    "semibold": [f"{WIN_FONTS}/NotoSansJP-SemiBold.ttf", f"{WIN_FONTS}/meiryo.ttc"],
}

ASSETS_IMG = ROOT / "assets" / "img"


def _load_font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES[kind]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def make_gradient_bg() -> Image.Image:
    """紺の縦グラデーション背景。1px幅の列を作ってから横に引き伸ばす。"""
    top = hex_to_rgb(BRAND_NAVY_DARK)
    bottom = hex_to_rgb(BRAND_NAVY)
    column = Image.new("RGB", (1, H))
    px = column.load()
    for y in range(H):
        t = y / (H - 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        px[0, y] = (r, g, b)
    return column.resize((W, H), Image.NEAREST)


def circular_icon(path, diameter: int) -> Image.Image:
    im = Image.open(path).convert("RGB").resize((diameter * 4, diameter * 4), Image.LANCZOS)
    mask = Image.new("L", im.size, 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((0, 0, im.size[0], im.size[1]), fill=255)
    im.putalpha(mask)
    im = im.resize((diameter, diameter), Image.LANCZOS)
    # 縁取り
    ring = Image.new("RGBA", im.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse((1, 1, diameter - 2, diameter - 2), outline=hex_to_rgb(BRAND_SKY) + (255,), width=4)
    im.alpha_composite(ring)
    return im


def wrap_text(draw, text, font, max_width):
    if draw.textlength(text, font=font) <= max_width:
        return [text]
    # 折り返し: 文字単位で詰めていく(日本語は単語区切りが無いため)
    lines = []
    cur = ""
    for ch in text:
        test = cur + ch
        if draw.textlength(test, font=font) > max_width and cur:
            lines.append(cur)
            cur = ch
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def draw_header_footer(canvas: Image.Image, icon: Image.Image, date_str: str):
    draw = ImageDraw.Draw(canvas)
    # ヘッダー
    icon_pos = (56, 64)
    canvas.paste(icon, icon_pos, icon)
    header_font = _load_font("bold", 44)
    draw.text(
        (icon_pos[0] + icon.width + 24, icon_pos[1] + icon.height // 2),
        "よっちゃんのFX",
        font=header_font,
        fill=hex_to_rgb(BRAND_WHITE),
        anchor="lm",
    )
    # フッター
    footer_font = _load_font("semibold", 32)
    draw.text(
        (56, H - 90),
        date_str,
        font=footer_font,
        fill=hex_to_rgb(BRAND_SKY),
        anchor="lm",
    )
    draw.text(
        (W - 56, H - 90),
        SITE_URL,
        font=footer_font,
        fill=hex_to_rgb(BRAND_SKY),
        anchor="rm",
    )
    # フッター上の細い区切り線
    draw.line((56, H - 130, W - 56, H - 130), fill=hex_to_rgb(BRAND_NAVY_DARK), width=2)


def make_intro_slide(bg: Image.Image, icon: Image.Image, article: dict) -> Image.Image:
    canvas = bg.copy()
    draw_header_footer(canvas, icon, article.get("date", ""))
    draw = ImageDraw.Draw(canvas)

    title = article.get("title", "")
    title_font = _load_font("bold", 66)
    max_w = W - 140
    lines = []
    for raw_line in wrap_text(draw, title, title_font, max_w):
        lines.append(raw_line)
    line_h = 88
    total_h = line_h * len(lines)
    start_y = (H - total_h) // 2 - 60

    # タイトル背後にうっすらパネル
    panel_top = start_y - 60
    panel_bottom = start_y + total_h + 60
    panel = Image.new("RGBA", (W, panel_bottom - panel_top), (0, 0, 0, 90))
    canvas.paste(panel, (0, panel_top), panel)

    draw = ImageDraw.Draw(canvas)
    for i, line in enumerate(lines):
        draw.text(
            (W // 2, start_y + i * line_h + line_h // 2),
            line,
            font=title_font,
            fill=hex_to_rgb(BRAND_WHITE),
            anchor="mm",
        )

    hero = article.get("hero") or {}
    if hero.get("pair") and hero.get("price"):
        sub = f"{hero['pair']}  {hero['price']}"
        sub_font = _load_font("semibold", 40)
        draw.text(
            (W // 2, start_y + total_h + 40),
            sub,
            font=sub_font,
            fill=hex_to_rgb(BRAND_SKY),
            anchor="mm",
        )
    return canvas


def make_caption_slide(bg: Image.Image, icon: Image.Image, article: dict, caption: str) -> Image.Image:
    canvas = bg.copy()
    draw_header_footer(canvas, icon, article.get("date", ""))
    draw = ImageDraw.Draw(canvas)

    cap_font = _load_font("bold", 78)
    max_w = W - 120
    lines = wrap_text(draw, caption, cap_font, max_w)
    line_h = 104
    total_h = line_h * len(lines)
    start_y = (H - total_h) // 2

    for i, line in enumerate(lines):
        y = start_y + i * line_h + line_h // 2
        # 縁取り(可読性のための黒フチ)
        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-3, -3), (3, 3), (-3, 3), (3, -3)):
            draw.text((W // 2 + dx, y + dy), line, font=cap_font, fill=(0, 0, 0), anchor="mm")
        draw.text((W // 2, y), line, font=cap_font, fill=hex_to_rgb(BRAND_WHITE), anchor="mm")
    return canvas


def get_wav_duration(path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def build_frames(article, out_dir):
    captions = __import__("json").loads((out_dir / "captions.json").read_text(encoding="utf-8"))
    audio_dur = get_wav_duration(out_dir / "voice.wav")

    intro_dur = min(INTRO_SEC, max(0.8, audio_dur * 0.2))
    remain = max(audio_dur - intro_dur, len(captions) * 1.0)
    per_caption = remain / len(captions)

    bg = make_gradient_bg()
    icon = circular_icon(ASSETS_IMG / "fx_icon.png", 120)

    frames_dir = out_dir / "frames"
    frames_dir.mkdir(exist_ok=True)
    for f in frames_dir.glob("*.png"):
        f.unlink()

    entries = []  # (filename, duration)
    intro = make_intro_slide(bg, icon, article)
    intro_path = frames_dir / "frame_00_intro.png"
    intro.save(intro_path)
    entries.append((intro_path.name, intro_dur))

    for i, cap in enumerate(captions, 1):
        slide = make_caption_slide(bg, icon, article, cap)
        path = frames_dir / f"frame_{i:02d}.png"
        slide.save(path)
        entries.append((path.name, per_caption))

    total = sum(d for _, d in entries)
    return frames_dir, entries, total, audio_dur


def write_concat_file(frames_dir, entries) -> "pathlib.Path":
    lines = []
    for name, dur in entries:
        lines.append(f"file '{name}'")
        lines.append(f"duration {dur:.3f}")
    # concat demuxerの仕様: 最後の画像はdurationが反映されないため同じファイルをもう一度書く
    lines.append(f"file '{entries[-1][0]}'")
    concat_path = frames_dir / "concat.txt"
    concat_path.write_text("\n".join(lines), encoding="utf-8")
    return concat_path


def run_ffmpeg(frames_dir, concat_path, audio_path, out_path, target_duration):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg_exe,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-c:a", "aac",
        "-b:a", "160k",
        "-t", f"{target_duration:.3f}",
        "-movflags", "+faststart",
        str(out_path),
    ]
    result = subprocess.run(cmd, cwd=str(frames_dir), capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout[-3000:])
        print(result.stderr[-3000:])
        raise RuntimeError("ffmpeg でのエンコードに失敗しました")


def main():
    article = load_latest_article()
    out_dir = article_out_dir(article)

    for req in ("script.txt", "captions.json", "voice.wav"):
        if not (out_dir / req).exists():
            raise FileNotFoundError(f"先に make_script.py / make_audio.py を実行してください: {out_dir / req}")

    print("フレームを生成中...")
    frames_dir, entries, slides_total, audio_dur = build_frames(article, out_dir)
    concat_path = write_concat_file(frames_dir, entries)

    target_duration = min(slides_total, audio_dur) if audio_dur > 0 else slides_total
    out_path = out_dir / "short.mp4"
    print(f"ffmpegでエンコード中... (スライド長={slides_total:.1f}s / 音声長={audio_dur:.1f}s)")
    run_ffmpeg(frames_dir, concat_path, out_dir / "voice.wav", out_path, target_duration)

    print(f"  -> {out_path} ({target_duration:.1f}秒)")


if __name__ == "__main__":
    main()
