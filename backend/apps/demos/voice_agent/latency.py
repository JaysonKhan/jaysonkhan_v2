"""Turn timing.

The Realtime API reports VAD events as positions in the input audio stream ("ms since the
first audio byte of the session"). To turn that into a latency, the relay needs to know when
each position *arrived* at the server, and where in the audio the user really stopped talking.
`AudioClock` keeps both: arrival times per chunk and the last few seconds of PCM.
"""

import math
from array import array
from collections import deque
from dataclasses import dataclass

SAMPLE_RATE = 24_000
BYTES_PER_MS = SAMPLE_RATE * 2 // 1000  # PCM16 mono: 48 bytes per millisecond
FRAME_MS = 10
VOICE_DBFS = -45.0  # a 10 ms frame louder than this counts as speech


def frame_levels(pcm: bytes) -> list[float]:
    """RMS level (dBFS) of each full 10 ms frame."""
    samples = array("h")
    samples.frombytes(pcm[: len(pcm) - len(pcm) % 2])
    n = SAMPLE_RATE * FRAME_MS // 1000
    levels = []
    for i in range(0, len(samples) - n + 1, n):
        rms = math.sqrt(sum(s * s for s in samples[i : i + n]) / n)
        levels.append(20 * math.log10(rms / 32768) if rms > 0 else -120.0)
    return levels


class AudioClock:
    def __init__(self, keep_ms: int = 10_000):
        self._keep_bytes = keep_ms * BYTES_PER_MS
        self._chunks: deque[tuple[int, float]] = deque()  # (end byte offset, arrival time)
        self._pcm = bytearray()
        self._pcm_start = 0  # stream offset of self._pcm[0]
        self.total_bytes = 0

    @property
    def total_ms(self) -> float:
        return self.total_bytes / BYTES_PER_MS

    def push(self, chunk: bytes, arrived_at: float) -> None:
        self.total_bytes += len(chunk)
        self._chunks.append((self.total_bytes, arrived_at))
        self._pcm += chunk
        excess = len(self._pcm) - self._keep_bytes
        if excess > 0:
            excess -= excess % 2
            del self._pcm[:excess]
            self._pcm_start += excess
        while self._chunks and self._chunks[0][0] <= self._pcm_start:
            self._chunks.popleft()

    def arrival_time(self, ms: float) -> float | None:
        """When the chunk holding stream position `ms` reached the server."""
        pos = ms * BYTES_PER_MS
        if pos < self._pcm_start:
            return None
        for end, arrived_at in self._chunks:
            if pos <= end:
                return arrived_at
        return None

    def _levels(self, start_ms: float, end_ms: float) -> tuple[float, list[float]]:
        start = max(int(start_ms * BYTES_PER_MS), self._pcm_start)
        start -= start % 2
        end = min(int(end_ms * BYTES_PER_MS), self.total_bytes)
        pcm = self._pcm[start - self._pcm_start : end - self._pcm_start] if end > start else b""
        return start / BYTES_PER_MS, frame_levels(bytes(pcm))

    def last_voiced_ms(self, start_ms: float, end_ms: float) -> float | None:
        """Stream position where the last speech frame in [start_ms, end_ms) ends."""
        offset, levels = self._levels(start_ms, end_ms)
        for i in range(len(levels) - 1, -1, -1):
            if levels[i] > VOICE_DBFS:
                return offset + (i + 1) * FRAME_MS
        return None

    def first_voiced_ms(self, start_ms: float, end_ms: float) -> float | None:
        """Stream position where the first speech frame in [start_ms, end_ms) starts."""
        offset, levels = self._levels(start_ms, end_ms)
        for i, level in enumerate(levels):
            if level > VOICE_DBFS:
                return offset + i * FRAME_MS
        return None


@dataclass
class Turn:
    number: int
    speech_end_at: float  # server arrival time of the user's last speech frame
    vad_stop_at: float  # when input_audio_buffer.speech_stopped reached the server
    speech_end_from_vad: bool = False  # True if no speech frame was found and the VAD position was used
    first_audio_at: float | None = None  # first response.output_audio.delta of the reply

    def metrics(self) -> dict:
        assert self.first_audio_at is not None
        vad_wait_ms = round((self.vad_stop_at - self.speech_end_at) * 1000)
        response_ms = round((self.first_audio_at - self.vad_stop_at) * 1000)
        return {
            "turn": self.number,
            "latency_ms": vad_wait_ms + response_ms,
            "vad_wait_ms": vad_wait_ms,
            "response_ms": response_ms,
            "speech_end_from_vad": self.speech_end_from_vad,
        }
