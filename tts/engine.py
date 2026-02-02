from __future__ import annotations

import os
import platform
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional, Tuple

from locale_pack.loader import LocalePack


@dataclass
class TTSEngine:
    locale: LocalePack

    def synthesize(self, text: str) -> Tuple[bytes, str]:
        text = text.strip()
        if not text:
            return b"", "application/octet-stream"

        system = platform.system().lower()
        if system == "darwin":
            return self._say(text)
        if system == "linux":
            return self._espeak(text)
        return b"", "application/octet-stream"

    def _say(self, text: str) -> Tuple[bytes, str]:
        # macOS "say" can render to AIFF. Keep it simple and local.
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "tts.aiff")
            cmd = ["say", "-o", out, text]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                audio = open(out, "rb").read()
                return audio, "audio/aiff"
            except Exception:
                return b"", "application/octet-stream"

    def _espeak(self, text: str) -> Tuple[bytes, str]:
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "tts.wav")
            cmd = ["espeak", "-w", out, text]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                audio = open(out, "rb").read()
                return audio, "audio/wav"
            except Exception:
                return b"", "application/octet-stream"

