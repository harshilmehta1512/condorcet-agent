"""Encode a short narrated walkthrough of captured UI screens; not a live screen recording."""
import json
from pathlib import Path
import subprocess
import wave
import textwrap

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = ROOT / "cache/video"
WORK.mkdir(parents=True, exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FLAGS = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}


def stamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def font(size, bold=False):
    return ImageFont.truetype("C:/Windows/Fonts/" + ("segoeuib.ttf" if bold else "segoeui.ttf"), size)


def main():
    scenes = json.loads((HERE / "scenes.json").read_text(encoding="utf-8"))
    segments, captions, elapsed = [], [], 0.0
    title_font, sub_font, footer_font = font(21, True), font(12), font(18, True)
    for index, scene in enumerate(scenes, 1):
        audio = WORK / "audio" / f"{index:02}.wav"
        with wave.open(str(audio)) as wav:
            duration = max(scene["minimum"], wav.getnframes() / wav.getframerate() + .45)
        frame = Image.open(HERE / "screens" / scene["image"]).convert("RGB")
        assert frame.size == (1280, 720), frame.size
        draw = ImageDraw.Draw(frame)
        draw.rectangle((0, 0, 1280, 46), fill="#183C33")
        draw.text((20, 3), scene["title"], font=title_font, fill="#ffffff")
        draw.text((20, 28), "Condorcet · narrated UI screenshots · saved results · synthetic voice", font=sub_font, fill="#D2E2D5")
        # One brief takeaway in a footer; full spoken captions are supplied in SRT.
        draw.rectangle((0, 685, 1280, 720), fill="#183C33")
        draw.text((20, 691), scene["takeaway"], font=footer_font, fill="#ffffff")
        frame_path = WORK / f"frame_{index:02}.png"
        frame.save(frame_path)
        segment = WORK / f"segment_{index:02}.mp4"
        subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-loop", "1", "-framerate", "24", "-i", str(frame_path),
                        "-i", str(audio), "-t", str(duration), "-vf", "format=yuv420p", "-c:v", "libx264",
                        "-preset", "fast", "-crf", "20", "-c:a", "aac", "-b:a", "128k", "-af", "apad",
                        "-movflags", "+faststart", str(segment)], check=True, **FLAGS)
        segments.append(segment)
        # Short caption chunks can be read at normal playback speed.
        words = scene["say"].split()
        chunks = [" ".join(words[i:i + 12]) for i in range(0, len(words), 12)]
        for i, chunk in enumerate(chunks):
            start = elapsed + duration * i / len(chunks)
            end = elapsed + duration * (i + 1) / len(chunks)
            captions.append(f"{len(captions)+1}\n{stamp(start)} --> {stamp(end)}\n" + "\n".join(textwrap.wrap(chunk, 64)) + "\n")
        scene.update(start_seconds=elapsed, duration_seconds=duration)
        elapsed += duration
        print(f"Scene {index}: {duration:.2f}s", flush=True)
    assert 60 <= elapsed <= 120, f"Duration outside 1–2 minute brief: {elapsed}"
    assert sum(s["duration_seconds"] for s in scenes[4:6]) >= 20
    listing = WORK / "concat.txt"
    listing.write_text("\n".join(f"file '{p.name}'" for p in segments), encoding="utf-8")
    video = HERE / "condorcet_demo_corrected.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                    "-c", "copy", "-movflags", "+faststart", str(video)], check=True, **FLAGS)
    (HERE / "condorcet_demo_corrected.srt").write_text("\n".join(captions), encoding="utf-8")
    (HERE / "timeline.json").write_text(json.dumps({"duration_seconds": elapsed, "scenes": scenes,
        "recording_type": "Narrated walkthrough of actual browser screenshots, not a continuous live recording.",
        "nuclear_seconds": sum(s['duration_seconds'] for s in scenes[4:6]), "new_inference_calls": 0}, indent=2, ensure_ascii=False), encoding="utf-8")
    Image.open(WORK / "frame_01.png").save(HERE / "poster.jpg")
    print(f"Ready: {elapsed:.2f}s, 1280×720, H.264/AAC, subtitles, two reports.")


if __name__ == "__main__":
    main()
