(() => {
  "use strict";

  const body = document.body;
  if (!body) return;

  const metadata = {
    personaId: String(body.dataset.personaId || "").trim(),
    displayName: String(body.dataset.displayName || "").trim(),
    voiceId: String(body.dataset.voiceId || "").trim(),
  };
  const appsScriptUrl = String(body.dataset.appsScriptUrl || "").trim();
  const MODEL_ID = "model_1_deepgram_agent";
  const DEPLOYMENT_PATH = "deepgram_voice_agent";
  const MAX_TRANSCRIPT_CHARS = 4000;
  const parsedInputSampleRate = Number.parseInt(body.dataset.inputSampleRate, 10);
  const inputSampleRate = Number.isFinite(parsedInputSampleRate) && parsedInputSampleRate > 0
    ? parsedInputSampleRate
    : 16000;

  const startButton = document.getElementById("start-button");
  const stopButton = document.getElementById("stop-button");
  const onboarding = document.getElementById("onboarding-form");
  const degreeInput = document.getElementById("degree-level");
  const studentIdInput = document.getElementById("student-id");
  const status = document.getElementById("status");
  const connectionState = document.getElementById("connection-state");
  const microphoneState = document.getElementById("microphone-state");
  const speakerState = document.getElementById("speaker-state");
  const elapsed = document.getElementById("elapsed");
  const errorMessage = document.getElementById("error-message");
  const player = document.getElementById("audio-player");

  const requiredElements = [
    startButton,
    stopButton,
    onboarding,
    degreeInput,
    studentIdInput,
    status,
    connectionState,
    microphoneState,
    speakerState,
    elapsed,
    errorMessage,
    player,
  ];
  if (requiredElements.some((element) => !element)) return;
  if (!metadata.personaId || !metadata.displayName || !metadata.voiceId) {
    status.textContent = "This conversation page is not configured.";
    startButton.disabled = true;
    return;
  }

  document.querySelectorAll("[data-persona-display]").forEach((element) => {
    element.textContent = metadata.displayName;
  });

  const VALID_DEGREE_LEVELS = new Set(["undergraduate", "graduate"]);
  const state = {
    socket: null,
    mediaStream: null,
    audioContext: null,
    microphoneSource: null,
    microphoneProcessor: null,
    microphoneSilence: null,
    capturing: false,
    active: false,
    stopping: false,
    session: null,
    startedAt: 0,
    elapsedTimer: null,
    mediaSource: null,
    mediaSourceUrl: null,
    audioSourceBuffer: null,
    mediaQueue: [],
    mediaEndRequested: false,
    playbackAudioContext: null,
    pcmNextStartTime: 0,
    pcmScheduledSources: 0,
    pcmSources: new Set(),
    pcmAudioDone: false,
    dropAudioUntilAgent: false,
    dropAudioTimer: null,
    transcriptQueue: [],
    transcriptPosting: false,
  };

  function setStatus(message) {
    status.textContent = message;
  }

  function setConnectionState(message) {
    connectionState.textContent = message;
  }

  function setMicrophoneState(message) {
    microphoneState.textContent = message;
  }

  function setSpeakerState(message) {
    speakerState.textContent = message;
  }

  function setError(message) {
    const text = typeof message === "string" ? message.trim() : "";
    errorMessage.textContent = text;
    errorMessage.hidden = !text;
  }

  function clearError() {
    setError("");
  }

  function updateElapsed() {
    const seconds = state.startedAt
      ? Math.max(0, Math.floor((Date.now() - state.startedAt) / 1000))
      : 0;
    const minutes = String(Math.floor(seconds / 60)).padStart(2, "0");
    const remainder = String(seconds % 60).padStart(2, "0");
    elapsed.textContent = `${minutes}:${remainder}`;
    elapsed.dateTime = `PT${seconds}S`;
  }

  function startElapsed() {
    state.startedAt = Date.now();
    updateElapsed();
    window.clearInterval(state.elapsedTimer);
    state.elapsedTimer = window.setInterval(updateElapsed, 1000);
  }

  function stopElapsed() {
    state.startedAt = 0;
    window.clearInterval(state.elapsedTimer);
    state.elapsedTimer = null;
    updateElapsed();
  }

  function websocketUrl() {
    if (window.location.protocol === "file:") {
      return "ws://127.0.0.1:8765";
    }
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    return `${scheme}://${window.location.host}`;
  }

  function generateSessionId() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    const randomPart = Math.random().toString(36).slice(2, 12);
    return `session-${Date.now().toString(36)}-${randomPart}`;
  }

  function boundedText(value, maxLength) {
    if (typeof value !== "string") return "";
    return value.trim().slice(0, maxLength);
  }

  function setSaveError() {
    setError("Session data could not be saved.");
  }

  function postAppsScript(payload) {
    if (!appsScriptUrl || typeof window.fetch !== "function") {
      return Promise.resolve(false);
    }
    const options = {
      method: "POST",
      mode: "no-cors",
      headers: { "Content-Type": "text/plain;charset=utf-8" },
      body: JSON.stringify(payload),
      keepalive: true,
    };
    try {
      return window.fetch(appsScriptUrl, options).then(() => true).catch(() => {
        setSaveError();
        return false;
      });
    } catch (_error) {
      setSaveError();
      return Promise.resolve(false);
    }
  }

  async function flushTranscriptQueue() {
    if (state.transcriptPosting) return;
    state.transcriptPosting = true;
    try {
      while (state.transcriptQueue.length) {
        const payload = state.transcriptQueue.shift();
        await postAppsScript(payload);
      }
    } finally {
      state.transcriptPosting = false;
    }
  }

  function saveSessionStart(session) {
    if (!session || !appsScriptUrl) return;
    void postAppsScript({
      type: "session_start",
      persona_id: metadata.personaId,
      voice_id: session.voiceId,
      model_id: MODEL_ID,
      deployment_path: DEPLOYMENT_PATH,
      session_id: session.id,
      degree_level: session.degreeLevel,
      student_id: session.studentId,
      client_timestamp: new Date().toISOString(),
    });
  }

  function queueTranscript(role, text) {
    const session = state.session;
    if (!appsScriptUrl || !session || !["user", "assistant"].includes(role)) return;
    const transcript = boundedText(text, MAX_TRANSCRIPT_CHARS);
    if (!transcript) return;
    state.transcriptQueue.push({
      type: "agent_turn",
      persona_id: metadata.personaId,
      voice_id: session.voiceId,
      model_id: MODEL_ID,
      deployment_path: DEPLOYMENT_PATH,
      session_id: session.id,
      turn_id: generateSessionId(),
      degree_level: session.degreeLevel,
      student_id: session.studentId,
      role,
      content: transcript,
      transcript,
      client_timestamp: new Date().toISOString(),
    });
    void flushTranscriptQueue();
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

  function resampleToInputRate(input, sourceRate) {
    if (sourceRate === inputSampleRate) return input;
    const ratio = sourceRate / inputSampleRate;
    const outputLength = Math.max(1, Math.round(input.length / ratio));
    const output = new Float32Array(outputLength);
    for (let index = 0; index < outputLength; index += 1) {
      const position = index * ratio;
      const left = Math.floor(position);
      const right = Math.min(left + 1, input.length - 1);
      const weight = position - left;
      output[index] = input[left] * (1 - weight) + input[right] * weight;
    }
    return output;
  }

  function floatToPcm16(input) {
    const buffer = new ArrayBuffer(input.length * 2);
    const view = new DataView(buffer);
    for (let index = 0; index < input.length; index += 1) {
      const sample = Math.max(-1, Math.min(1, input[index]));
      const value = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      view.setInt16(index * 2, value, true);
    }
    return buffer;
  }

  function drainMediaQueue() {
    const sourceBuffer = state.audioSourceBuffer;
    if (!sourceBuffer || sourceBuffer.updating) return;
    if (state.mediaQueue.length) {
      try {
        sourceBuffer.appendBuffer(state.mediaQueue.shift());
        void player.play().catch(() => {});
      } catch (_error) {
        state.mediaQueue.length = 0;
        setSpeakerState("Unavailable");
        setError("Streaming audio could not be appended.");
      }
      return;
    }
    if (
      state.mediaEndRequested
      && state.mediaSource
      && state.mediaSource.readyState === "open"
    ) {
      try {
        state.mediaSource.endOfStream();
      } catch (_error) {
        // The stream may already have ended while the final chunk was queued.
      }
    }
  }

  function ensureMediaSource() {
    const MediaSourceConstructor = window.MediaSource;
    if (
      typeof MediaSourceConstructor !== "function"
      || typeof MediaSourceConstructor.isTypeSupported !== "function"
      || !MediaSourceConstructor.isTypeSupported("audio/mpeg")
    ) {
      setSpeakerState("Unavailable");
      setError("This browser does not support streaming MP3 playback.");
      return false;
    }
    if (state.mediaSource) return true;

    try {
      const mediaSource = new MediaSourceConstructor();
      state.mediaSource = mediaSource;
      state.mediaSourceUrl = URL.createObjectURL(mediaSource);
      player.src = state.mediaSourceUrl;
      mediaSource.addEventListener("sourceopen", () => {
        if (state.mediaSource !== mediaSource) return;
        try {
          state.audioSourceBuffer = mediaSource.addSourceBuffer("audio/mpeg");
          state.audioSourceBuffer.mode = "sequence";
          state.audioSourceBuffer.addEventListener("updateend", drainMediaQueue);
          drainMediaQueue();
        } catch (_error) {
          setSpeakerState("Unavailable");
          setError("Streaming audio could not be initialized.");
        }
      }, { once: true });
      return true;
    } catch (_error) {
      setSpeakerState("Unavailable");
      setError("Streaming audio could not be initialized.");
      return false;
    }
  }

  function enqueueAudio(encoded) {
    if (typeof encoded !== "string" || !encoded || !ensureMediaSource()) return;
    try {
      const binary = window.atob(encoded);
      const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
      state.mediaQueue.push(bytes);
      setSpeakerState("Speaking");
      drainMediaQueue();
    } catch (_error) {
      setSpeakerState("Unavailable");
      setError("Received audio could not be decoded by this browser.");
    }
  }

  function isRawPcmFormat(audioFormat) {
    return Boolean(
      audioFormat
      && audioFormat.encoding === "linear16"
      && audioFormat.sample_rate === 24000
      && audioFormat.container === "none"
    );
  }

  function ensurePlaybackAudioContext() {
    const AudioContextConstructor = window.AudioContext || window.webkitAudioContext;
    if (typeof AudioContextConstructor !== "function") {
      setSpeakerState("Unavailable");
      setError("This browser does not support raw PCM playback.");
      return null;
    }
    if (
      state.playbackAudioContext
      && state.playbackAudioContext.state !== "closed"
    ) {
      return state.playbackAudioContext;
    }
    try {
      state.playbackAudioContext = new AudioContextConstructor({ latencyHint: "interactive" });
      if (typeof state.playbackAudioContext.resume === "function") {
        const resumed = state.playbackAudioContext.resume();
        if (resumed && typeof resumed.catch === "function") {
          void resumed.catch(() => {});
        }
      }
      return state.playbackAudioContext;
    } catch (_error) {
      state.playbackAudioContext = null;
      setSpeakerState("Unavailable");
      setError("Raw PCM playback could not be initialized.");
      return null;
    }
  }

  function decodePcm16(encoded) {
    const binary = window.atob(encoded);
    const sampleCount = Math.floor(binary.length / 2);
    if (!sampleCount) return null;
    const samples = new Float32Array(sampleCount);
    for (let index = 0; index < sampleCount; index += 1) {
      let value = binary.charCodeAt(index * 2)
        | (binary.charCodeAt(index * 2 + 1) << 8);
      if (value & 0x8000) value -= 0x10000;
      samples[index] = value / 0x8000;
    }
    return samples;
  }

  function maybeFinishPcmAudio(context) {
    if (
      !context
      || state.playbackAudioContext !== context
      || !state.pcmAudioDone
      || state.pcmScheduledSources
    ) return;
    setSpeakerState("Idle");
  }

  function enqueuePcmAudio(encoded, sampleRate) {
    if (typeof encoded !== "string" || !encoded) return;
    let samples;
    try {
      samples = decodePcm16(encoded);
    } catch (_error) {
      setSpeakerState("Unavailable");
      setError("Received raw PCM audio could not be decoded.");
      return;
    }
    if (!samples) return;
    const context = ensurePlaybackAudioContext();
    if (!context) return;

    try {
      const buffer = context.createBuffer(1, samples.length, sampleRate);
      buffer.getChannelData(0).set(samples);
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(context.destination);
      const now = typeof context.currentTime === "number" ? context.currentTime : 0;
      const startTime = Math.max(state.pcmNextStartTime, now);
      const duration = buffer.duration || samples.length / sampleRate;
      state.pcmAudioDone = false;
      state.pcmScheduledSources += 1;
      state.pcmSources.add(source);
      let ended = false;
      source.onended = () => {
        if (ended) return;
        ended = true;
        state.pcmSources.delete(source);
        if (state.playbackAudioContext !== context) return;
        state.pcmScheduledSources = Math.max(0, state.pcmScheduledSources - 1);
        maybeFinishPcmAudio(context);
      };
      source.start(startTime);
      state.pcmNextStartTime = startTime + duration;
      setSpeakerState("Speaking");
    } catch (_error) {
      state.pcmScheduledSources = Math.max(0, state.pcmScheduledSources - 1);
      setSpeakerState("Unavailable");
      setError("Raw PCM playback could not be scheduled.");
    }
  }

  function finishPcmAudio() {
    state.pcmAudioDone = true;
    maybeFinishPcmAudio(state.playbackAudioContext);
  }

  function resetPcmAudio() {
    state.pcmNextStartTime = 0;
    state.pcmScheduledSources = 0;
    state.pcmAudioDone = false;
    for (const source of state.pcmSources) {
      try {
        source.stop();
      } catch (_error) {
        // A source may already have ended while interruption was requested.
      }
    }
    state.pcmSources.clear();
    const context = state.playbackAudioContext;
    state.playbackAudioContext = null;
    if (context) {
      try {
        const closed = context.close();
        if (closed && typeof closed.catch === "function") {
          void closed.catch(() => {});
        }
      } catch (_error) {
        // The context may already be closing during page teardown.
      }
    }
  }

  function finishAudioStream() {
    state.mediaEndRequested = true;
    drainMediaQueue();
    finishPcmAudio();
  }

  function resetAudioStream() {
    resetPcmAudio();
    state.mediaEndRequested = false;
    state.mediaQueue.length = 0;
    state.audioSourceBuffer = null;
    if (state.mediaSourceUrl) URL.revokeObjectURL(state.mediaSourceUrl);
    state.mediaSourceUrl = null;
    state.mediaSource = null;
    player.removeAttribute("src");
    player.load();
    setSpeakerState("Idle");
  }

  function interruptAudioPlayback() {
    resetAudioStream();
    // Deepgram may deliver the first assistant audio chunk before an
    // AgentStartedSpeaking event. Never discard that first chunk: stopping
    // the already-scheduled sources is sufficient for barge-in.
    state.dropAudioUntilAgent = false;
    window.clearTimeout(state.dropAudioTimer);
    setSpeakerState("Idle");
  }

  function stopRecorder() {
    state.capturing = false;
    if (state.microphoneProcessor) state.microphoneProcessor.disconnect();
    if (state.microphoneSource) state.microphoneSource.disconnect();
    if (state.microphoneSilence) state.microphoneSilence.disconnect();
    if (state.audioContext) void state.audioContext.close().catch(() => {});
    state.microphoneProcessor = null;
    state.microphoneSource = null;
    state.microphoneSilence = null;
    state.audioContext = null;
    if (state.mediaStream) state.mediaStream.getTracks().forEach((track) => track.stop());
    state.mediaStream = null;
    setMicrophoneState("Off");
  }

  async function startRecorder() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setMicrophoneState("Unavailable");
      setError("This browser does not provide microphone capture.");
      return false;
    }
    try {
      state.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      state.audioContext = new AudioContext({ latencyHint: "interactive" });
      state.microphoneSource = state.audioContext.createMediaStreamSource(state.mediaStream);
      state.microphoneProcessor = state.audioContext.createScriptProcessor(4096, 1, 1);
      state.microphoneSilence = state.audioContext.createGain();
      state.microphoneSilence.gain.value = 0;
      state.microphoneProcessor.addEventListener("audioprocess", (event) => {
        if (
          !state.capturing
          || !state.socket
          || state.socket.readyState !== WebSocket.OPEN
        ) return;
        const input = event.inputBuffer.getChannelData(0);
        const pcm = floatToPcm16(resampleToInputRate(input, state.audioContext.sampleRate));
        state.socket.send(JSON.stringify({ type: "audio", data: toBase64(pcm) }));
      });
      state.microphoneSource.connect(state.microphoneProcessor);
      state.microphoneProcessor.connect(state.microphoneSilence);
      state.microphoneSilence.connect(state.audioContext.destination);
      await state.audioContext.resume();
      state.capturing = true;
      setMicrophoneState("Listening");
      return true;
    } catch (_error) {
      stopRecorder();
      setMicrophoneState("Unavailable");
      setError("Microphone permission was not granted.");
      return false;
    }
  }

  function showOnboarding() {
    onboarding.hidden = false;
    degreeInput.focus();
  }

  function finalizeSession(message) {
    state.active = false;
    state.stopping = false;
    stopRecorder();
    stopElapsed();
    finishAudioStream();
    setConnectionState("Disconnected");
    setStatus(message);
    startButton.disabled = false;
    stopButton.disabled = true;
    state.session = null;
    showOnboarding();
    if (state.socket) {
      const socket = state.socket;
      state.socket = null;
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close();
      }
    }
  }

  function handleServerEvent(event) {
    if (!event || typeof event.type !== "string") {
      setError("Received an invalid server event.");
      return;
    }
    switch (event.type) {
      case "ready":
        setConnectionState("Connected");
        setStatus(event.audio_input_supported === false ? "Ready (audio unavailable)" : "Ready");
        if (event.audio_input_supported === false) {
          setMicrophoneState("Unavailable");
          setError("The server does not currently accept microphone audio.");
        } else if (!state.capturing && state.socket) {
          void startRecorder().then((recorderStarted) => {
            if (!recorderStarted && state.socket && state.socket.readyState === WebSocket.OPEN) {
              state.stopping = true;
              state.socket.send(JSON.stringify({ type: "stop" }));
              stopButton.disabled = true;
              stopElapsed();
              setStatus("Processing");
            }
          });
        }
        break;
      case "audio_chunk":
        if (isRawPcmFormat(event.audio_format)) {
          enqueuePcmAudio(event.data, event.audio_format.sample_rate);
        } else {
          enqueueAudio(event.data);
        }
        break;
      case "audio_done":
        finishPcmAudio();
        break;
      case "speaking":
        if (event.role === "user" && event.speaking === true) {
          interruptAudioPlayback();
        } else if (event.role === "agent" && event.speaking === true) {
          state.dropAudioUntilAgent = false;
          window.clearTimeout(state.dropAudioTimer);
        }
        break;
      case "error":
        setStatus("Error");
        setError(typeof event.message === "string" ? event.message : "The server reported an error.");
        break;
      case "stopped":
        finalizeSession("Stopped");
        break;
      case "text_delta":
        // Audio-first mode deliberately ignores server text events.
        break;
      case "transcript":
        // Hidden transcript events are persisted only; never expose their
        // text through status, aria-live, or any visible element.
        queueTranscript(
          event.role,
          typeof event.text === "string" ? event.text : event.content,
        );
        break;
      default:
        break;
    }
  }

  function readOnboarding() {
    const degreeLevel = degreeInput.value;
    if (!VALID_DEGREE_LEVELS.has(degreeLevel)) {
      setError("Choose undergraduate or graduate before starting.");
      degreeInput.focus();
      return null;
    }
    const studentId = studentIdInput.value.trim();
    if (!studentId || studentId.length > 128) {
      setError("Enter a valid student ID before starting.");
      studentIdInput.focus();
      return null;
    }
    return { degreeLevel, studentId };
  }

  async function startSession() {
    if (state.socket || state.active) return;
    clearError();
    const onboardingValues = readOnboarding();
    if (!onboardingValues) return;

    state.session = {
      id: generateSessionId(),
      degreeLevel: onboardingValues.degreeLevel,
      studentId: onboardingValues.studentId,
      voiceId: metadata.voiceId,
    };
    saveSessionStart(state.session);
    // The student ID is retained only in the in-memory session object and is
    // removed from the form before any provider-facing message is sent.
    studentIdInput.value = "";
    onboarding.hidden = true;
    resetAudioStream();
    // Create and resume the PCM playback context inside the submit gesture.
    // Mobile browsers may block an AudioContext created only after the first
    // asynchronous provider audio chunk arrives.
    ensurePlaybackAudioContext();
    state.dropAudioUntilAgent = false;
    window.clearTimeout(state.dropAudioTimer);
    setStatus("Connecting");
    setConnectionState("Connecting");
    setMicrophoneState("Off");
    setSpeakerState("Idle");
    startButton.disabled = true;
    stopButton.disabled = true;
    state.stopping = false;

    let socket;
    try {
      socket = new WebSocket(websocketUrl());
    } catch (_error) {
      state.session = null;
      showOnboarding();
      startButton.disabled = false;
      setConnectionState("Unavailable");
      setStatus("Connection error");
      setError("The conversation server could not be reached.");
      return;
    }
    state.socket = socket;
    socket.addEventListener("open", async () => {
      if (state.socket !== socket) return;
      state.active = true;
      startElapsed();
      try {
        socket.send(JSON.stringify({ type: "start", persona_id: metadata.personaId }));
      } catch (_error) {
        finalizeSession("Connection error");
        setError("The conversation server could not be reached.");
        return;
      }
      stopButton.disabled = false;
    });
    socket.addEventListener("message", (message) => {
      if (state.socket !== socket) return;
      try {
        handleServerEvent(JSON.parse(message.data));
      } catch (_error) {
        setError("Received invalid data from the server.");
      }
    });
    socket.addEventListener("error", () => {
      if (state.socket !== socket) return;
      setConnectionState("Error");
      setStatus("Connection error");
      setError("The conversation server reported a connection error.");
    });
    socket.addEventListener("close", () => {
      if (state.socket !== socket) return;
      state.socket = null;
      if (state.active || state.stopping) {
        finalizeSession(state.stopping ? "Stopped" : "Disconnected");
      } else {
        stopRecorder();
        stopElapsed();
        startButton.disabled = false;
        stopButton.disabled = true;
      }
    });
  }

  function stopSession() {
    if (!state.socket) {
      finalizeSession("Stopped");
      return;
    }
    if (state.socket.readyState === WebSocket.OPEN && !state.stopping) {
      stopRecorder();
      state.stopping = true;
      stopButton.disabled = true;
      stopElapsed();
      setStatus("Processing");
      try {
        state.socket.send(JSON.stringify({ type: "stop" }));
      } catch (_error) {
        finalizeSession("Stopped");
      }
      return;
    }
    if (state.socket.readyState === WebSocket.CONNECTING) {
      finalizeSession("Stopped");
    }
  }

  onboarding.addEventListener("submit", (event) => {
    event.preventDefault();
    void startSession();
  });
  stopButton.addEventListener("click", stopSession);
  player.addEventListener("playing", () => {
    if (!state.pcmScheduledSources) setSpeakerState("Speaking");
  });
  player.addEventListener("ended", () => {
    if (!state.pcmScheduledSources) setSpeakerState("Idle");
  });
  player.addEventListener("error", () => {
    if (state.mediaSource) {
      setSpeakerState("Unavailable");
      setError("Audio playback failed.");
    }
  });
  window.addEventListener("pagehide", () => {
    stopRecorder();
    stopElapsed();
    void flushTranscriptQueue();
    if (state.socket && state.socket.readyState === WebSocket.OPEN) {
      try {
        state.socket.send(JSON.stringify({ type: "stop" }));
      } catch (_error) {
        // The page is already closing; cleanup below is sufficient.
      }
    }
    if (state.socket) state.socket.close();
    window.clearTimeout(state.dropAudioTimer);
    state.socket = null;
    resetAudioStream();
  });
})();
