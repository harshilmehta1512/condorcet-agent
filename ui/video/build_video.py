"""Encode the captured app screens with locally generated speech. No API calls."""
import json
from pathlib import Path
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".ui_deps"))
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
scenes = json.loads((HERE / "scenes.json").read_text(encoding="utf-8"))
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 23)
small = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 13)
segments, captions, elapsed = [], [], 0.0


def stamp(seconds):
    ms = round(seconds * 1000)
    return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"


for index, scene in enumerate(scenes, 1):
    audio = HERE / f"{index:02}.wav"
    with wave.open(str(audio)) as wav:
        speech_seconds = wav.getnframes() / wav.getframerate()
    duration = max(scene["minimum"], speech_seconds + 0.5)
    screenshot = Image.open(HERE / scene["image"]).convert("RGB")
    assert screenshot.size == (1280, 720), screenshot.size
    draw = ImageDraw.Draw(screenshot)
    draw.rectangle((0, 0, 1280, 58), fill="#162638")
    draw.text((32, 6), scene["title"], font=font, fill="white")
    draw.text((32, 36), "Condorcet Agent · narrated app screenshots · saved results · synthetic voice", font=small, fill="#c6d5e5")
    framed = HERE / f"frame_{index:02}.png"
    screenshot.save(framed)
    segment = HERE / f"segment_{index:02}.mp4"
    command = [ffmpeg, "-y", "-loglevel", "error", "-loop", "1", "-framerate", "24", "-i", str(framed),
               "-i", str(audio), "-t", str(duration), "-vf", "format=yuv420p", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
               "-c:a", "aac", "-b:a", "128k", "-af", "apad", "-movflags", "+faststart", str(segment)]
    subprocess.run(command, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    segments.append(segment)
    captions.append(f"{index}\n{stamp(elapsed)} --> {stamp(elapsed+duration)}\n{scene['say']}\n")
    scene["start_seconds"], scene["duration_seconds"] = elapsed, duration
    elapsed += duration
    print(f"Scene {index}: {duration:.2f}s", flush=True)

assert 60 <= elapsed <= 120, f"Video duration outside brief: {elapsed}"
assert scenes[5]["duration_seconds"] + scenes[6]["duration_seconds"] >= 20
concat = HERE / "concat.txt"
concat.write_text("\n".join(f"file '{p.name}'" for p in segments), encoding="utf-8")
subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
                "-c", "copy", "-movflags", "+faststart", str(HERE / "condorcet_streamlit_demo.mp4")], check=True,
               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
(HERE / "condorcet_streamlit_demo.srt").write_text("\n".join(captions), encoding="utf-8")
(HERE / "timeline.json").write_text(json.dumps({"duration_seconds":elapsed,"scenes":scenes},indent=2,ensure_ascii=False),encoding="utf-8")
print(f"Video ready: {elapsed:.2f}s, 1280x720, narrated. Nuclear duration exceeds the required second-report minimum.")
