(() => {
  "use strict";

  const startButton = document.getElementById("start-button");
  const stopButton = document.getElementById("stop-button");
  const personaInput = document.getElementById("persona-id");
  const contextInput = document.getElementById("task-context");
  const status = document.getElementById("status");
  const elapsed = document.getElementById("elapsed");
  const events = document.getElementById("events");
  const player = document.getElementById("audio-player");

  let socket = null;
  let recorder = null;
  let mediaStream = null;
  let microphoneContext = null;
  let microphoneSource = null;
  let microphoneProcessor = null;
  let microphoneSilence = null;
  let startedAt = 0;
  let elapsedTimer = null;
  let mediaSource = null;
  let mediaSourceUrl = null;
  let audioSourceBuffer = null;
  const mediaQueue = [];
  let mediaEndRequested = false;
  let streamedText = "";
  let eventPrefix = "";

  function setStatus(message) {
    status.textContent = message;
  }

  function appendEvent(message) {
    events.textContent += `${message}\n`;
    events.scrollTop = events.scrollHeight;
  }

  function updateElapsed() {
    const seconds = startedAt ? Math.max(0, Math.floor((Date.now() - startedAt) / 1000)) : 0;
    const minutes = String(Math.floor(seconds / 60)).padStart(2, "0");
    const remainder = String(seconds % 60).padStart(2, "0");
    elapsed.textContent = `${minutes}:${remainder}`;
    elapsed.dateTime = `PT${seconds}S`;
  }

  function startElapsed() {
    startedAt = Date.now();
    updateElapsed();
    window.clearInterval(elapsedTimer);
    elapsedTimer = window.setInterval(updateElapsed, 1000);
  }

  function stopElapsed() {
    startedAt = 0;
    window.clearInterval(elapsedTimer);
    elapsedTimer = null;
    updateElapsed();
  }

  function websocketUrl() {
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    return `${scheme}://${window.location.host}`;
  }

  function toBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    const blockSize = 0x8000;
    for (let offset = 0; offset < bytes.length; offset += blockSize) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + blockSize));
    }
    return window.btoa(binary);
  }

  function resampleTo16k(input, sourceRate) {
    if (sourceRate === 16000) return input;
    const ratio = sourceRate / 16000;
    const outputLength = Math.max(1, Math.round(input.length / ratio));
    const output = new Float32Array(outputLength);
    for (let i = 0; i < outputLength; i += 1) {
      const position = i * ratio;
      const left = Math.floor(position);
      const right = Math.min(left + 1, input.length - 1);
      const weight = position - left;
      output[i] = input[left] * (1 - weight) + input[right] * weight;
    }
    return output;
  }

  function floatToPcm16(input) {
    const output = new Int16Array(input.length);
    for (let i = 0; i < input.length; i += 1) {
      const sample = Math.max(-1, Math.min(1, input[i]));
      output[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    }
    return output.buffer;
  }

  async function enqueueAudio(encoded) {
    if (typeof encoded !== "string" || !encoded) return;
    try {
      const binary = window.atob(encoded);
      const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
      if (!window.MediaSource || !MediaSource.isTypeSupported("audio/mpeg")) {
        appendEvent("This browser does not support streaming MP3 playback.");
        return;
      }
      if (!mediaSource) {
        mediaSource = new MediaSource();
        mediaSourceUrl = URL.createObjectURL(mediaSource);
        player.src = mediaSourceUrl;
        mediaSource.addEventListener("sourceopen", () => {
          try {
            audioSourceBuffer = mediaSource.addSourceBuffer("audio/mpeg");
            audioSourceBuffer.mode = "sequence";
            audioSourceBuffer.addEventListener("updateend", drainMediaQueue);
            drainMediaQueue();
          } catch (_error) {
            appendEvent("Streaming audio could not be initialized.");
          }
        }, { once: true });
      }
      mediaQueue.push(bytes);
      drainMediaQueue();
    } catch (_error) {
      appendEvent("Received audio could not be decoded by this browser.");
    }
  }

  function drainMediaQueue() {
    if (!audioSourceBuffer || audioSourceBuffer.updating) return;
    if (mediaQueue.length) {
      try {
        audioSourceBuffer.appendBuffer(mediaQueue.shift());
        void player.play().catch(() => {});
      } catch (_error) {
        appendEvent("Streaming audio could not be appended.");
        mediaQueue.length = 0;
      }
      return;
    }
    if (mediaEndRequested && mediaSource && mediaSource.readyState === "open") {
      try {
        mediaSource.endOfStream();
      } catch (_error) {
        // The stream may already have ended while the final chunk was queued.
      }
    }
  }

  function finishAudioStream() {
    mediaEndRequested = true;
    drainMediaQueue();
  }

  function resetAudioStream() {
    mediaEndRequested = false;
    mediaQueue.length = 0;
    audioSourceBuffer = null;
    if (mediaSourceUrl) URL.revokeObjectURL(mediaSourceUrl);
    mediaSourceUrl = null;
    mediaSource = null;
    player.removeAttribute("src");
    player.load();
    streamedText = "";
    eventPrefix = "";
  }

  function appendTextDelta(text) {
    if (typeof text !== "string" || !text) return;
    streamedText += text;
    events.textContent = `${eventPrefix}${streamedText}`;
    events.scrollTop = events.scrollHeight;
  }

  function stopRecorder() {
    if (microphoneProcessor) microphoneProcessor.disconnect();
    if (microphoneSource) microphoneSource.disconnect();
    if (microphoneSilence) microphoneSilence.disconnect();
    if (microphoneContext) void microphoneContext.close();
    microphoneProcessor = null;
    microphoneSource = null;
    microphoneSilence = null;
    microphoneContext = null;
    recorder = null;
    if (mediaStream) mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }

  async function startRecorder() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      appendEvent("This browser does not provide microphone capture.");
      return;
    }
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      microphoneContext = new AudioContext({ latencyHint: "interactive" });
      microphoneSource = microphoneContext.createMediaStreamSource(mediaStream);
      microphoneProcessor = microphoneContext.createScriptProcessor(4096, 1, 1);
      microphoneSilence = microphoneContext.createGain();
      microphoneSilence.gain.value = 0;
      microphoneProcessor.addEventListener("audioprocess", (event) => {
        if (!socket || socket.readyState !== WebSocket.OPEN) return;
        const input = event.inputBuffer.getChannelData(0);
        const pcm = floatToPcm16(resampleTo16k(input, microphoneContext.sampleRate));
        socket.send(JSON.stringify({ type: "audio", data: toBase64(pcm) }));
      });
      microphoneSource.connect(microphoneProcessor);
      microphoneProcessor.connect(microphoneSilence);
      microphoneSilence.connect(microphoneContext.destination);
      await microphoneContext.resume();
      recorder = microphoneProcessor;
    } catch (_error) {
      stopRecorder();
      appendEvent("Microphone permission was not granted.");
    }
  }

  function handleEvent(event) {
    if (!event || typeof event.type !== "string") {
      appendEvent("Received an invalid server event.");
      return;
    }
    switch (event.type) {
      case "ready":
        setStatus(event.audio_input_supported ? "Ready" : "Ready (audio unavailable)");
        eventPrefix = "Session ready.\n";
        appendEvent("Session ready.");
        break;
      case "text_delta":
        appendTextDelta(event.text);
        break;
      case "audio_chunk":
        void enqueueAudio(event.data);
        break;
      case "timing":
        if (typeof event.total_duration_seconds === "number") {
          appendEvent(`Timing: ${event.total_duration_seconds.toFixed(2)}s`);
        }
        break;
      case "error":
        setStatus("Error");
        appendEvent(typeof event.message === "string" ? event.message : "The server reported an error.");
        break;
      case "stopped":
        setStatus("Stopped");
        stopRecorder();
        stopElapsed();
        finishAudioStream();
        startButton.disabled = false;
        stopButton.disabled = true;
        break;
      default:
        appendEvent("Received an unsupported server event.");
    }
  }

  function closeSocket() {
    stopRecorder();
    if (socket) socket.close();
    socket = null;
  }

  async function startSession() {
    if (socket && socket.readyState === WebSocket.OPEN) return;
    const personaId = personaInput.value.trim();
    if (!personaId) {
      setStatus("Enter a persona ID");
      personaInput.focus();
      return;
    }
    setStatus("Connecting");
    events.textContent = "";
    resetAudioStream();
    try {
      socket = new WebSocket(websocketUrl());
      socket.addEventListener("open", async () => {
        const context = contextInput.value.trim();
        socket.send(JSON.stringify({
          type: "start",
          persona_id: personaId,
          ...(context ? { task_context: context } : {}),
        }));
        startButton.disabled = true;
        stopButton.disabled = false;
        startElapsed();
        await startRecorder();
      });
      socket.addEventListener("message", (message) => {
        try {
          handleEvent(JSON.parse(message.data));
        } catch (_error) {
          appendEvent("Received invalid data from the server.");
        }
      });
      socket.addEventListener("error", () => setStatus("Connection error"));
      socket.addEventListener("close", () => {
        stopRecorder();
        socket = null;
        if (stopButton.disabled === false) {
          setStatus("Disconnected");
          startButton.disabled = false;
          stopButton.disabled = true;
          stopElapsed();
        }
      });
    } catch (_error) {
      closeSocket();
      setStatus("Connection error");
    }
  }

  function stopSession() {
    if (socket && socket.readyState === WebSocket.OPEN) {
      // Stop capturing immediately; the server finalizes the turn separately.
      stopRecorder();
      socket.send(JSON.stringify({ type: "stop" }));
      setStatus("Processing");
      stopButton.disabled = true;
      stopElapsed();
    } else {
      closeSocket();
      setStatus("Disconnected");
      startButton.disabled = false;
      stopButton.disabled = true;
      stopElapsed();
    }
  }

  startButton.addEventListener("click", () => { void startSession(); });
  stopButton.addEventListener("click", stopSession);
})();
