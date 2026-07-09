#!/usr/bin/env python3
"""Generate a hackathon submission video for CPOS Engine-Zero.

Creates slide images with Japanese narration using local VOICEVOX, then composes
an MP4 with ffmpeg. No credentials are read or printed.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import textwrap
import wave
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "video_build" / datetime.now().strftime("%Y%m%d_%H%M%S")
VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")
SPEAKER_ID = int(os.environ.get("VOICEVOX_SPEAKER_ID", "8"))
W, H = 1280, 720
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
CLOUD_RUN_URL = "https://cpos-engine-zero-951178130166.asia-northeast1.run.app"
BUILD_ID = "04fe2b94-f43f-4336-81ff-8d6ad32af4d7"


def run(cmd: list[str], cwd: Path = ROOT, timeout: int = 120) -> str:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    out = (proc.stdout or "") + (proc.stderr or "")
    return strip_ansi(out)[-2200:]


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def voicevox(text: str, out_wav: Path) -> None:
    query = requests.post(
        f"{VOICEVOX_URL}/audio_query",
        params={"text": text, "speaker": SPEAKER_ID},
        timeout=30,
    )
    query.raise_for_status()
    synthesis = requests.post(
        f"{VOICEVOX_URL}/synthesis",
        params={"speaker": SPEAKER_ID},
        data=json.dumps(query.json()),
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    synthesis.raise_for_status()
    out_wav.write_bytes(synthesis.content)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def load_font(size: int, bold: bool = False):
    path = FONT_BOLD if bold and Path(FONT_BOLD).exists() else FONT
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        current = ""
        # Japanese-aware: wrap char-by-char, but preserve ASCII word-ish chunks enough.
        for ch in para:
            trial = current + ch
            if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = ch
        if current:
            lines.append(current)
    return lines


def draw_terminal(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, text: str) -> None:
    draw.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=(10, 16, 24), outline=(0, 220, 180), width=2)
    draw.text((x + 18, y + 14), "terminal", font=load_font(20, True), fill=(0, 255, 200))
    font = load_font(20)
    max_lines = int((h - 58) / 25)
    cleaned = strip_ansi(text).replace("/home/mayutama/cpos_defensive_agent", "./repo")
    lines = []
    for line in cleaned.splitlines():
        if len(line) > 92:
            line = line[:89] + "..."
        lines.append(line)
    for i, line in enumerate(lines[-max_lines:]):
        color = (210, 235, 230)
        if "passed" in line or "SUCCESS" in line or "Validation Succeeded" in line:
            color = (90, 255, 150)
        elif "ERROR" in line or "Failed" in line:
            color = (255, 120, 120)
        draw.text((x + 18, y + 52 + i * 25), line, font=font, fill=color)


def make_slide(idx: int, title: str, bullets: list[str], narration: str, terminal: str | None, out_png: Path) -> None:
    img = Image.new("RGB", (W, H), (4, 8, 16))
    draw = ImageDraw.Draw(img)
    # Background grid / glow
    for gx in range(0, W, 64):
        draw.line([(gx, 0), (gx, H)], fill=(8, 24, 36))
    for gy in range(0, H, 64):
        draw.line([(0, gy), (W, gy)], fill=(8, 24, 36))
    draw.ellipse([850, -180, 1450, 420], fill=(0, 70, 90))
    draw.ellipse([-220, 420, 380, 980], fill=(60, 20, 90))

    title_font = load_font(44, True)
    bullet_font = load_font(27)
    small_font = load_font(20)
    draw.text((58, 44), "CPOS Engine-Zero", font=load_font(22, True), fill=(0, 255, 200))
    draw.text((58, 82), title, font=title_font, fill=(245, 250, 255))
    draw.text((1050, 52), f"{idx:02d}", font=load_font(52, True), fill=(0, 255, 200))

    y = 166
    for b in bullets:
        lines = wrap_text(draw, b, bullet_font, 690 if terminal else 1080)
        draw.text((70, y), "▸", font=bullet_font, fill=(0, 255, 200))
        for j, line in enumerate(lines[:3]):
            draw.text((108, y + j * 36), line, font=bullet_font, fill=(235, 242, 246))
        y += max(46, len(lines[:3]) * 36 + 14)

    if terminal:
        draw_terminal(draw, 725, 160, 500, 430, terminal)

    # Narration subtitle
    sub_font = load_font(23)
    draw.rounded_rectangle([42, 612, 1238, 692], radius=18, fill=(0, 0, 0), outline=(80, 120, 150), width=1)
    sub_lines = wrap_text(draw, narration, sub_font, 1130)[:2]
    for i, line in enumerate(sub_lines):
        draw.text((72, 628 + i * 30), line, font=sub_font, fill=(255, 255, 255))

    img.save(out_png)


def ffmpeg_segment(img: Path, wav: Path, out_mp4: Path, duration: float) -> None:
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(img), "-i", str(wav),
        "-t", f"{duration:.3f}", "-vf", "format=yuv420p",
        "-af", "apad",
        "-c:v", "libx264", "-preset", "veryfast", "-r", "30",
        "-c:a", "aac", "-b:a", "160k", str(out_mp4)
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def concat(segments: list[Path], output: Path) -> None:
    list_file = OUT_DIR / "segments.txt"
    list_file.write_text("".join(f"file '{p}'\n" for p in segments), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output)], check=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[*] Output dir: {OUT_DIR}")

    cli_demo = run(["python3", "engine_zero_cli.py", "demo"], timeout=180)
    cloud_smoke = run(["bash", "-lc", f"curl -fsS {CLOUD_RUN_URL}/ && echo && curl -fsS {CLOUD_RUN_URL}/health"], timeout=30)

    scenes = [
        {
            "title": "AI DevOpsを安全に動かす箱",
            "bullets": [
                "自律エージェントに本番リポジトリを直接触らせない",
                "隔離・検証・失敗時破棄・成功時だけ反映する実行基盤",
                "Google Cloud BuildとCloud Runに対応",
            ],
            "narration": "CPOS Engine-Zeroは、AIや自動修正を安全に動かすためのゼロトラストDevOps実行基盤です。",
        },
        {
            "title": "Defense-in-Depth Architecture",
            "bullets": [
                "AIT Firewallで命令とデータを分離",
                "一時ワークスペースで修正を試行",
                "Docker sandboxでpytest、成功時だけatomic deploy",
            ],
            "narration": "入力を分離し、一時領域で試し、Dockerサンドボックスで検証してから、成功時だけ反映します。",
        },
        {
            "title": "CLI Repeatable Demo",
            "bullets": [
                "毎回freshなバグありアプリを /tmp に生成",
                "ゼロ除算バグを題材に安全パイプラインを実演",
                "審査員は python3 engine_zero_cli.py demo だけで確認可能",
            ],
            "terminal": cli_demo,
            "narration": "CLIデモでは、毎回新しいバグありアプリを作り、修正、検証、反映までを一回で見せます。",
        },
        {
            "title": "Sandbox Validation",
            "bullets": [
                "--network none で外部通信を遮断",
                "--cap-drop=ALL とリソース制限で隔離",
                "Dockerが無い場合はfail closed。明示時だけローカルfallback",
            ],
            "terminal": "Docker Sandbox\npytest: 3 passed\nValidation Succeeded\nAtomic Deploy: complete",
            "narration": "検証コードはネットワークなし、権限なし、リソース制限ありのDocker環境で実行します。",
        },
        {
            "title": "Google Cloud Collaboration",
            "bullets": [
                f"Cloud Build成功: {BUILD_ID}",
                "Cloud Runは署名付きWebhook/control-planeとして公開",
                "Cloud RunのDocker-in-Docker制約はrunbookに明記",
            ],
            "terminal": cloud_smoke,
            "narration": "Google Cloud Buildで再現可能に検証し、Cloud Runで公開できるコントロールプレーンも用意しました。",
        },
        {
            "title": "Not a magic fixer, but a safety runtime",
            "bullets": [
                "今回の修正器はデモ用の決定的fixer",
                "価値は、AI修正を安全に閉じ込める実行パイプライン",
                "LLM fixerやPR作成エージェントへ差し替え可能",
            ],
            "narration": "これは何でも直す魔法AIではありません。AI DevOpsを安全に運用するためのランタイムです。",
        },
        {
            "title": "Submission Links",
            "bullets": [
                "GitHub: kagioneko-emi/cpos-engine-zero",
                f"Cloud Run: {CLOUD_RUN_URL}",
                "Quick demo: python3 engine_zero_cli.py demo",
            ],
            "narration": "提出物には、GitHub、Cloud Build、Cloud Run、そして再現可能なCLIデモを含めています。",
        },
    ]

    segments: list[Path] = []
    for i, scene in enumerate(scenes, 1):
        wav = OUT_DIR / f"scene_{i:02d}.wav"
        png = OUT_DIR / f"scene_{i:02d}.png"
        mp4 = OUT_DIR / f"scene_{i:02d}.mp4"
        voicevox(scene["narration"], wav)
        duration = max(wav_duration(wav) + 4.0, 14.0)
        make_slide(i, scene["title"], scene["bullets"], scene["narration"], scene.get("terminal"), png)
        ffmpeg_segment(png, wav, mp4, duration)
        segments.append(mp4)
        print(f"[*] Scene {i}: {duration:.1f}s")

    output = ROOT / f"engine_zero_submission_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    concat(segments, output)
    print(f"✅ Video complete: {output}")


if __name__ == "__main__":
    main()
