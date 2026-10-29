#!/usr/bin/env python3
"""Transcribe an audio file (phone call, voice memo) to timestamped text,
locally, with faster-whisper. Only the one-time model download touches the
network; the audio never leaves the machine.

Usage:  python3 agent/transcribe.py AUDIO OUT.txt [--model small] [--lang pt]
Setup:  pip install faster-whisper   (kept out of requirements.txt: heavy,
        installed on demand)
"""

import argparse
import sys


def main():
    ap = argparse.ArgumentParser(description="Transcribe audio to timestamped text.")
    ap.add_argument("audio")
    ap.add_argument("out")
    ap.add_argument("--model", default="small",
                    help="tiny|base|small|medium (bigger = better, slower)")
    ap.add_argument("--lang", default=None,
                    help="force a language code (pt, en); default: detect")
    args = ap.parse_args()

    from faster_whisper import WhisperModel  # optional dependency

    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    segments, info = model.transcribe(args.audio, language=args.lang,
                                      beam_size=1, vad_filter=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(f"# language={info.language} p={info.language_probability:.2f} "
                f"duration={info.duration:.0f}s\n")
        for s in segments:
            m, sec = divmod(int(s.start), 60)
            f.write(f"[{m:02d}:{sec:02d}] {s.text.strip()}\n")
            f.flush()
    print(f"done: {args.out}")


if __name__ == "__main__":
    sys.exit(main())
