// Voice agent demo audio worklets (loaded by voice-agent.js via audioWorklet.addModule).
// The AudioContext runs at 24 kHz, the Realtime API PCM rate, so no resampling here.

const FRAME = 480; // 20 ms at 24 kHz

// Microphone -> PCM16 frames of 20 ms, plus their level for the meter.
class Capture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.frame = new Int16Array(FRAME);
    this.n = 0;
    this.sumSq = 0;
  }

  process(inputs) {
    const input = inputs[0][0];
    if (!input) return true;
    for (let i = 0; i < input.length; i++) {
      const s = Math.max(-1, Math.min(1, input[i]));
      this.frame[this.n++] = s < 0 ? s * 0x8000 : s * 0x7fff;
      this.sumSq += s * s;
      if (this.n === FRAME) {
        const rms = Math.sqrt(this.sumSq / FRAME);
        this.port.postMessage({ pcm: this.frame.buffer, rms }, [this.frame.buffer]);
        this.frame = new Int16Array(FRAME);
        this.n = 0;
        this.sumSq = 0;
      }
    }
    return true;
  }
}

// Agent audio queue. Knows exactly how many samples of the current item reached the speakers,
// which is what the server needs to truncate the agent's message after a barge-in.
class Playback extends AudioWorkletProcessor {
  constructor() {
    super();
    this.reset(null);
    this.levelSumSq = 0;
    this.levelN = 0;
    this.port.onmessage = ({ data }) => {
      if (data.type === "start") this.reset(data.itemId);
      else if (data.type === "chunk") this.queue.push(new Int16Array(data.pcm));
      else if (data.type === "done") this.complete = true;
      else if (data.type === "stop") {
        this.port.postMessage({
          type: "stopped",
          itemId: this.itemId,
          playedMs: this.playedMs(),
        });
        this.reset(null);
      }
    };
  }

  reset(itemId) {
    this.itemId = itemId;
    this.queue = [];
    this.offset = 0;
    this.played = 0;
    this.complete = false;
  }

  playedMs() {
    return this.played / 24;
  }

  process(_inputs, outputs) {
    const out = outputs[0][0];
    let i = 0;
    while (i < out.length && this.queue.length) {
      const chunk = this.queue[0];
      const take = Math.min(out.length - i, chunk.length - this.offset);
      for (let k = 0; k < take; k++) {
        const s = chunk[this.offset + k] / 32768;
        out[i + k] = s;
        this.levelSumSq += s * s;
      }
      i += take;
      this.offset += take;
      this.played += take;
      if (this.offset === chunk.length) {
        this.queue.shift();
        this.offset = 0;
      }
    }
    out.fill(0, i);
    this.levelN += out.length;
    if (this.levelN >= FRAME) {
      this.port.postMessage({
        type: "level",
        rms: Math.sqrt(this.levelSumSq / this.levelN),
      });
      this.levelSumSq = 0;
      this.levelN = 0;
    }
    if (this.itemId && this.complete && !this.queue.length) {
      this.port.postMessage({
        type: "drained",
        itemId: this.itemId,
        playedMs: this.playedMs(),
      });
      this.reset(null);
    }
    return true;
  }
}

registerProcessor("capture", Capture);
registerProcessor("playback", Playback);
