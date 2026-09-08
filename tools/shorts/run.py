# -*- coding: utf-8 -*-
"""make_script -> make_audio -> make_video を順番に実行し、
tools/shorts/out/<記事id>/short.mp4 を作る。

使い方:
    python tools/shorts/run.py
"""
import time

import make_script
import make_audio
import make_video
from common import load_latest_article, article_out_dir


def main():
    article = load_latest_article()
    out_dir = article_out_dir(article)
    print(f"=== {article.get('date')} {article.get('title')} ===")
    print(f"出力先: {out_dir}\n")

    t0 = time.time()

    print("[1/3] 台本生成 (make_script)")
    make_script.main()
    print()

    print("[2/3] 音声生成 (make_audio)")
    make_audio.main()
    print()

    print("[3/3] 動画生成 (make_video)")
    make_video.main()
    print()

    elapsed = time.time() - t0
    print(f"完了: {out_dir / 'short.mp4'} ({elapsed:.1f}秒で生成)")


if __name__ == "__main__":
    main()
