import React, {useState, useEffect, useRef, useCallback} from "react";
import "./App.css";
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome";
import {
  faMicrophone,
  faMicrophoneSlash,
  faStop,
  faPaperPlane,
  faPlay,
  faWifi,
  faPowerOff,
} from "@fortawesome/free-solid-svg-icons";

// Constants
const INPUT_SAMPLE_RATE = 16000;
const OUTPUT_SAMPLE_RATE = 24000;
const MIC_BUFFER_SIZE = 2048;
const AUDIO_WORKLET_URL = '/audio-processor.js';
const MAX_AUDIO_QUEUE_SIZE = 50; // Maximum audio chunks in queue
const WEBSOCKET_SEND_BUFFER_LIMIT = 65536; // 64KB buffer limit
const MAX_RETRY_ATTEMPTS = 3; // Maximum retry attempts for failed transmissions
const RETRY_DELAY_BASE = 100; // Base delay in ms for exponential backoff
const MAX_AUDIO_CONTEXT_RECOVERY_ATTEMPTS = 5; // Maximum AudioContext recovery attempts
const AUDIO_CONTEXT_RECOVERY_DELAY = 1000; // Base delay for AudioContext recovery

const LANGUAGES = [
  {code: "en-IN", name: "English (Hinglish)"},
  {code: "hi-IN", name: "हिंदी (Hindi)"},
  {code: "mr-IN", name: "मराठी (Marathi)"},
  {code: "ta-IN", name: "தமிழ் (Tamil)"},
  {code: "bn-IN", name: "বাংলা (Bengali)"},
  {code: "te-IN", name: "తెలుగు (Telugu)"},
  {code: "gu-IN", name: "ગુજરાતી (Gujarati)"},
  {code: "kn-IN", name: "ಕನ್ನಡ (Kannada)"},
  {code: "ml-IN", name: "മലയാളം (Malayalam)"},
  {code: "pa-IN", name: "ਪੰਜਾਬੀ (Punjabi)"},
];

// const BACKEND_HOST =  'gemini-backend-service-1018963165306.us-central1.run.app';
const BACKEND_HOST = "localhost:8000";
const generateUniqueId = () =>
  `${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 7)}`;

const App = () => {
  const [isRecording, setIsRecording] = useState(false); // Is microphone actively sending audio
  const [isSessionActive, setIsSessionActive] = useState(false); // Is the overall session (WS + mic) active
  const [isMuted, setIsMuted] = useState(false); // Is microphone muted
  const [messages, setMessages] = useState([]);
  const [textInputValue, setTextInputValue] = useState("");
  const [transcriptionMessages, setTranscriptionMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState(LANGUAGES[0].code);
  const [toolCallLogs, setToolCallLogs] = useState([]);
  const [webSocketStatus, setWebSocketStatus] = useState("N/A");

  const isRecordingRef = useRef(isRecording);
  const isSessionActiveRef = useRef(isSessionActive);
  const isMutedRef = useRef(isMuted);
  const playbackAudioContextRef = useRef(null);
  const localAudioContextRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const audioWorkletNodeRef = useRef(null);
  const audioChunkSentCountRef = useRef(0);
  const socketRef = useRef(null);
  const pendingAudioChunks = useRef([]);
  const audioMetricsRef = useRef({ dropouts: 0, latency: 0, quality: 1.0, retryCount: 0, failedTransmissions: 0 });
  const lastSendTimeRef = useRef(0);
  const retryQueueRef = useRef([]);
  const audioQueueRef = useRef([]);
  const audioContextRecoveryAttempts = useRef(0);
  const audioWorkletSupported = useRef(true);
  const isPlayingRef = useRef(false);
  const currentAudioSourceRef = useRef(null);
  const logsAreaRef = useRef(null);
  const chatAreaRef = useRef(null);

  useEffect(() => {
    isRecordingRef.current = isRecording;
  }, [isRecording]);
  useEffect(() => {
    isSessionActiveRef.current = isSessionActive;
  }, [isSessionActive]);
  useEffect(() => {
    isMutedRef.current = isMuted;
  }, [isMuted]);

  // Synchronize AudioWorklet with state changes
  useEffect(() => {
    if (audioWorkletNodeRef.current) {
      audioWorkletNodeRef.current.port.postMessage({
        type: 'SET_MUTED',
        data: { muted: isMuted }
      });
    }
  }, [isMuted]);

  useEffect(() => {
    if (audioWorkletNodeRef.current) {
      audioWorkletNodeRef.current.port.postMessage({
        type: 'SET_RECORDING',
        data: { recording: isRecording }
      });
    }
  }, [isRecording]);

  // Note: We'll update system playing state directly in the playback functions

  // Audio metrics monitoring
  useEffect(() => {
    const interval = setInterval(() => {
      if (audioWorkletNodeRef.current && isRecording) {
        audioWorkletNodeRef.current.port.postMessage({
          type: 'GET_METRICS'
        });
      }
    }, 5000); // Get metrics every 5 seconds

    return () => clearInterval(interval);
  }, [isRecording]);

  const addLogEntry = useCallback((type, content) => {
    // Only show tool calls and errors in the console
    const allowedTypes = ["toolcall", "error"];
    if (!allowedTypes.includes(type)) {
      return;
    }
    const newEntry = {
      id: generateUniqueId(),
      type,
      content,
      timestamp: new Date().toLocaleTimeString(),
    };
    setMessages((prev) => [...prev, newEntry]);
  }, []);

  const fetchToolCallLogs = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`http://${BACKEND_HOST}/api/logs`);
      if (!response.ok)
        throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      const toolLogs = data.filter(
        (log) =>
          typeof log === "object" &&
          log !== null &&
          (log.operation || log.tool_function_name)
      );

      const newLogEntries = toolLogs.map((log) => ({
        id: generateUniqueId(),
        type: "toolcall",
        content: JSON.stringify(log),
        timestamp: log.timestamp
          ? new Date(log.timestamp).toLocaleTimeString()
          : new Date().toLocaleTimeString(),
      }));
      newLogEntries.forEach((logEntry) => {
        const logContentString = String(logEntry.content);
        const contentLowerCase = logContentString.toLowerCase();
        const errorKeywords = [
          "error",
          "failed",
          "exception",
          "traceback",
          "critical",
          "err:",
          "warn:",
          "warning",
        ];
        let isError =
          (logEntry.status &&
            String(logEntry.status).toLowerCase().includes("error")) ||
          errorKeywords.some((keyword) => contentLowerCase.includes(keyword));
        console.log(
          `%c[Tool Call ${isError ? "ERROR" : "Log"}] ${
            logEntry.timestamp
          }: ${logContentString}`,
          isError ? "color: #FF3131; font-weight: bold;" : "color: #39FF14;"
        );
      });
      setMessages((prevMessages) => {
        const existingLogContents = new Set(
          prevMessages
            .filter((m) => m.type === "toolcall")
            .map((m) => m.content)
        );
        const uniqueNewEntries = newLogEntries.filter(
          (newLog) => !existingLogContents.has(newLog.content)
        );
        return [...prevMessages, ...uniqueNewEntries].sort(
          (a, b) =>
            new Date("1970/01/01 " + a.timestamp) -
            new Date("1970/01/01 " + b.timestamp)
        );
      });
      setToolCallLogs((prevLogs) => [...prevLogs, ...newLogEntries]);
    } catch (error) {
      console.error("Failed to fetch tool call logs:", error);
      addLogEntry("error", `Failed to fetch tool call logs: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  }, [addLogEntry]);

  useEffect(() => {
    fetchToolCallLogs();
    const intervalId = setInterval(fetchToolCallLogs, 15000);
    return () => clearInterval(intervalId);
  }, [fetchToolCallLogs]);

  useEffect(() => {
    if (logsAreaRef.current)
      logsAreaRef.current.scrollTop = logsAreaRef.current.scrollHeight;
  }, [messages]);
  useEffect(() => {
    if (chatAreaRef.current)
      chatAreaRef.current.scrollTop = chatAreaRef.current.scrollHeight;
  }, [transcriptionMessages]);

  // Recover suspended AudioContext (moved up to fix dependency order)
  const recoverAudioContext = useCallback(async (context, contextName) => {
    if (!context || context.state === 'closed') return false;
    
    if (audioContextRecoveryAttempts.current >= MAX_AUDIO_CONTEXT_RECOVERY_ATTEMPTS) {
      addLogEntry("error", `${contextName} recovery failed after ${MAX_AUDIO_CONTEXT_RECOVERY_ATTEMPTS} attempts`);
      return false;
    }

    audioContextRecoveryAttempts.current++;
    
    try {
      if (context.state === 'suspended') {
        addLogEntry("info", `Attempting to resume ${contextName} (attempt ${audioContextRecoveryAttempts.current})`);
        await context.resume();
        
        if (context.state === 'running') {
          addLogEntry("success", `${contextName} successfully resumed`);
          audioContextRecoveryAttempts.current = 0;
          return true;
        }
      }
    } catch (error) {
      addLogEntry("error", `Failed to resume ${contextName}: ${error.message}`);
    }

    // Schedule another recovery attempt
    if (audioContextRecoveryAttempts.current < MAX_AUDIO_CONTEXT_RECOVERY_ATTEMPTS) {
      const delay = AUDIO_CONTEXT_RECOVERY_DELAY * audioContextRecoveryAttempts.current;
      setTimeout(() => {
        recoverAudioContext(context, contextName);
      }, delay);
    }
    
    return false;
  }, [addLogEntry]);

  // Reinitialize AudioContext when closed (moved up to fix dependency order)
  const reinitializeAudioContext = useCallback(async () => {
    if (!isSessionActiveRef.current) return;

    addLogEntry("info", "Reinitializing AudioContext after closure");
    
    try {
      // Clean up existing context
      if (localAudioContextRef.current) {
        if (audioWorkletNodeRef.current) {
          audioWorkletNodeRef.current.disconnect();
          audioWorkletNodeRef.current = null;
        }
        localAudioContextRef.current = null;
      }

      // Restart audio processing
      if (mediaStreamRef.current && isRecordingRef.current) {
        addLogEntry("info", "Restarting audio processing after context recovery");
        // Use setTimeout to avoid dependency issues during recovery
        setTimeout(() => {
          handleStartListening(true); // Resume listening
        }, 100);
      }
    } catch (error) {
      addLogEntry("error", `AudioContext reinitialization failed: ${error.message}`);
      setIsSessionActive(false);
    }
  }, [addLogEntry]);

  // AudioContext state monitoring and recovery (moved up to fix dependency order)
  const monitorAudioContextState = useCallback((context, contextName) => {
    if (!context) return;

    const handleStateChange = () => {
      const state = context.state;
      addLogEntry("audio_context", `${contextName} state changed to: ${state}`);
      
      if (state === 'suspended') {
        addLogEntry("warning", `${contextName} suspended - attempting recovery`);
        recoverAudioContext(context, contextName);
      } else if (state === 'interrupted') {
        addLogEntry("warning", `${contextName} interrupted - scheduling recovery`);
        setTimeout(() => {
          recoverAudioContext(context, contextName);
        }, AUDIO_CONTEXT_RECOVERY_DELAY);
      } else if (state === 'closed') {
        addLogEntry("error", `${contextName} closed - reinitializing required`);
        if (contextName === 'LocalAudioContext' && isRecordingRef.current) {
          // Use setTimeout to avoid dependency issues
          setTimeout(() => {
            reinitializeAudioContext();
          }, 100);
        }
      } else if (state === 'running') {
        addLogEntry("success", `${contextName} successfully running`);
        audioContextRecoveryAttempts.current = 0; // Reset recovery attempts on success
      }
    };

    context.addEventListener('statechange', handleStateChange);
    
    return () => {
      context.removeEventListener('statechange', handleStateChange);
    };
  }, [addLogEntry, isRecording]);

  const getPlaybackAudioContext = useCallback(
    async (triggeredByAction) => {
      if (
        !playbackAudioContextRef.current ||
        playbackAudioContextRef.current.state === "closed"
      ) {
        try {
          addLogEntry("audio", "Attempting to create Playback AudioContext.");
          playbackAudioContextRef.current = new (window.AudioContext ||
            window.webkitAudioContext)({sampleRate: OUTPUT_SAMPLE_RATE});
            
          // Set up enhanced state monitoring for playback context
          monitorAudioContextState(playbackAudioContextRef.current, 'PlaybackAudioContext');
            
          playbackAudioContextRef.current.onstatechange = () =>
            addLogEntry(
              "audio",
              `PlaybackCTX state changed to: ${playbackAudioContextRef.current?.state}`
            );
          addLogEntry(
            "audio",
            `Playback AudioContext CREATED. Initial state: ${playbackAudioContextRef.current.state}, SampleRate: ${playbackAudioContextRef.current.sampleRate}`
          );
        } catch (e) {
          console.error(
            "[CTX_PLAYBACK_MGR] FAILED to CREATE Playback AudioContext",
            e
          );
          addLogEntry("error", `FATAL PlaybackCTX ERROR: ${e.message}`);
          playbackAudioContextRef.current = null;
          return null;
        }
      }
      if (playbackAudioContextRef.current.state === "suspended") {
        if (
          triggeredByAction &&
          (triggeredByAction.toLowerCase().includes("user_action") ||
            triggeredByAction.toLowerCase().includes("systemaction"))
        ) {
          addLogEntry(
            "audio",
            `PlaybackCTX State 'suspended'. Attempting RESUME by: ${triggeredByAction}.`
          );
          try {
            await playbackAudioContextRef.current.resume();
            addLogEntry(
              "audio",
              `PlaybackCTX Resume attempt finished. State: ${playbackAudioContextRef.current.state}`
            );
          } catch (e) {
            console.error(`[CTX_PLAYBACK_MGR] FAILED to RESUME PlaybackCTX`, e);
            addLogEntry("error", `FAILED to RESUME PlaybackCTX: ${e.message}`);
          }
        }
      }
      if (playbackAudioContextRef.current?.state !== "running")
        addLogEntry(
          "warning",
          `PlaybackCTX not 'running'. State: ${playbackAudioContextRef.current?.state}`
        );
      return playbackAudioContextRef.current;
    },
    [addLogEntry, monitorAudioContextState]
  );

  const playNextGeminiChunk = useCallback(async () => {
    if (isPlayingRef.current || audioQueueRef.current.length === 0) return;
    isPlayingRef.current = true;
    
    // Notify AudioWorklet that system audio is now playing
    if (audioWorkletNodeRef.current) {
      audioWorkletNodeRef.current.port.postMessage({
        type: 'SET_SYSTEM_PLAYING',
        data: { playing: true }
      });
    }
    const arrayBuffer = audioQueueRef.current.shift();
    const audioCtx = await getPlaybackAudioContext(
      "playNextGeminiChunk_SystemAction"
    );
    if (!audioCtx || audioCtx.state !== "running") {
      addLogEntry(
        "error",
        `Playback FAIL: Audio system not ready (${audioCtx?.state})`
      );
      isPlayingRef.current = false;
      
      // Notify AudioWorklet that system audio has stopped
      if (audioWorkletNodeRef.current) {
        audioWorkletNodeRef.current.port.postMessage({
          type: 'SET_SYSTEM_PLAYING',
          data: { playing: false }
        });
      }
      return;
    }
    try {
      if (
        !arrayBuffer ||
        arrayBuffer.byteLength === 0 ||
        arrayBuffer.byteLength % 2 !== 0
      ) {
        addLogEntry(
          "warning",
          "Received empty or invalid audio chunk. Skipping."
        );
        isPlayingRef.current = false;
        
        // Notify AudioWorklet that system audio has stopped
        if (audioWorkletNodeRef.current) {
          audioWorkletNodeRef.current.port.postMessage({
            type: 'SET_SYSTEM_PLAYING',
            data: { playing: false }
          });
        }
        if (audioQueueRef.current.length > 0) playNextGeminiChunk();
        return;
      }
      const pcm16Data = new Int16Array(arrayBuffer);
      const float32Data = new Float32Array(pcm16Data.length);
      for (let i = 0; i < pcm16Data.length; i++)
        float32Data[i] = pcm16Data[i] / 32768.0;
      if (float32Data.length === 0) {
        addLogEntry(
          "warning",
          "Received empty audio chunk (after conversion). Skipping."
        );
        isPlayingRef.current = false;
        
        // Notify AudioWorklet that system audio has stopped
        if (audioWorkletNodeRef.current) {
          audioWorkletNodeRef.current.port.postMessage({
            type: 'SET_SYSTEM_PLAYING',
            data: { playing: false }
          });
        }
        if (audioQueueRef.current.length > 0) playNextGeminiChunk();
        return;
      }
      const audioBuffer = audioCtx.createBuffer(
        1,
        float32Data.length,
        OUTPUT_SAMPLE_RATE
      );
      audioBuffer.copyToChannel(float32Data, 0);
      const source = audioCtx.createBufferSource();
      source.buffer = audioBuffer;
      const gainNode = audioCtx.createGain();
      gainNode.gain.setValueAtTime(0.8, audioCtx.currentTime);
      source.connect(gainNode);
      gainNode.connect(audioCtx.destination);
      source.onended = () => {
        addLogEntry("gemini_audio", "Audio chunk finished playing.");
        isPlayingRef.current = false;
        
        // Notify AudioWorklet that system audio has stopped
        if (audioWorkletNodeRef.current) {
          audioWorkletNodeRef.current.port.postMessage({
            type: 'SET_SYSTEM_PLAYING',
            data: { playing: false }
          });
        }
        
        currentAudioSourceRef.current = null;
        if (audioQueueRef.current.length > 0) playNextGeminiChunk();
        source.disconnect();
        gainNode.disconnect();
      };
      currentAudioSourceRef.current = source;
      addLogEntry("gemini_audio", "Starting playback of Gemini audio chunk...");
      source.start();
    } catch (error) {
      currentAudioSourceRef.current = null;
      addLogEntry("error", `Playback Error: ${error.message}`);
      isPlayingRef.current = false;
      
      // Notify AudioWorklet that system audio has stopped
      if (audioWorkletNodeRef.current) {
        audioWorkletNodeRef.current.port.postMessage({
          type: 'SET_SYSTEM_PLAYING',
          data: { playing: false }
        });
      }
      if (audioQueueRef.current.length > 0) playNextGeminiChunk();
    }
  }, [getPlaybackAudioContext, addLogEntry]);

  const stopSystemAudioPlayback = useCallback(() => {
    if (currentAudioSourceRef.current) {
      try {
        currentAudioSourceRef.current.stop();
        addLogEntry(
          "gemini_audio",
          "System audio playback stopped by barge-in."
        );
      } catch (e) {
        addLogEntry(
          "warning",
          `Could not stop current audio source for barge-in: ${e.message}`
        );
      }
      currentAudioSourceRef.current = null;
    }
    audioQueueRef.current = [];
    isPlayingRef.current = false;
    
    // Notify AudioWorklet that system audio has stopped (barge-in)
    if (audioWorkletNodeRef.current) {
      audioWorkletNodeRef.current.port.postMessage({
        type: 'SET_SYSTEM_PLAYING',
        data: { playing: false }
      });
    }
    
    addLogEntry("gemini_audio", "Gemini audio queue cleared due to barge-in.");
  }, [addLogEntry]);

  // WebSocket backpressure handling (moved up to fix dependency order)
  const checkWebSocketBackpressure = useCallback(() => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      return true; // Indicate backpressure if the socket is not open
    }

    const sendBufferSize = socketRef.current.bufferedAmount || 0;
    const latency = lastSendTimeRef.current > 0 ? Date.now() - lastSendTimeRef.current : 0;

    if (sendBufferSize > WEBSOCKET_SEND_BUFFER_LIMIT) {
      addLogEntry("backpressure", `High buffer: ${sendBufferSize} bytes`);
      return true;
    }

    if (latency > 500) { // 500ms latency threshold
      addLogEntry("backpressure", `High latency: ${latency}ms`);
      return true;
    }

    return false;
  }, [addLogEntry]);

  // Exponential backoff delay function
  const getRetryDelay = useCallback((attempt) => {
    return RETRY_DELAY_BASE * Math.pow(2, attempt) + Math.random() * 100; // Add jitter
  }, []);

  // Retry mechanism for audio chunks
  const retryAudioChunk = useCallback(async (audioData, attempt = 0) => {
    if (attempt >= MAX_RETRY_ATTEMPTS) {
      audioMetricsRef.current.failedTransmissions++;
      addLogEntry("error", `Audio chunk transmission failed after ${MAX_RETRY_ATTEMPTS} attempts`);
      return false;
    }

    try {
      if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
        // WebSocket not available, schedule retry
        const delay = getRetryDelay(attempt);
        addLogEntry("warning", `WebSocket not ready, retrying in ${delay.toFixed(0)}ms (attempt ${attempt + 1}/${MAX_RETRY_ATTEMPTS})`);
        
        setTimeout(() => {
          retryAudioChunk(audioData, attempt + 1);
        }, delay);
        return false;
      }

      // Check backpressure before retry
      if (checkWebSocketBackpressure()) {
        const delay = getRetryDelay(attempt);
        addLogEntry("warning", `WebSocket backpressure on retry, waiting ${delay.toFixed(0)}ms (attempt ${attempt + 1}/${MAX_RETRY_ATTEMPTS})`);
        
        setTimeout(() => {
          retryAudioChunk(audioData, attempt + 1);
        }, delay);
        return false;
      }

      socketRef.current.send(audioData);
      audioChunkSentCountRef.current++;
      lastSendTimeRef.current = Date.now();
      audioMetricsRef.current.retryCount += attempt; // Track total retry attempts
      
      if (attempt > 0) {
        addLogEntry("success", `Audio chunk sent successfully on retry attempt ${attempt + 1}`);
      }
      
      return true;
    } catch (error) {
      const delay = getRetryDelay(attempt);
      addLogEntry("warning", `Audio send error on attempt ${attempt + 1}: ${error.message}, retrying in ${delay.toFixed(0)}ms`);
      
      setTimeout(() => {
        retryAudioChunk(audioData, attempt + 1);
      }, delay);
      return false;
    }
  }, [addLogEntry, getRetryDelay, checkWebSocketBackpressure]);

  // Enhanced audio chunk sender with retry logic
  const sendAudioChunkWithBackpressure = useCallback(async (audioData) => {
    // First try immediate send
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN && !checkWebSocketBackpressure()) {
      try {
        socketRef.current.send(audioData);
        audioChunkSentCountRef.current++;
        lastSendTimeRef.current = Date.now();
        return true;
      } catch (error) {
        addLogEntry("warning", `Immediate send failed: ${error.message}, starting retry mechanism`);
        // Fall through to retry mechanism
      }
    }

    // If immediate send fails or backpressure detected, use retry mechanism
    if (checkWebSocketBackpressure()) {
      addLogEntry("warning", "WebSocket backpressure detected, adding to retry queue");
      
      // Add to pending queue (with size limit)
      if (pendingAudioChunks.current.length < MAX_AUDIO_QUEUE_SIZE) {
        pendingAudioChunks.current.push(audioData);
      } else {
        // Drop oldest chunk if queue is full
        pendingAudioChunks.current.shift();
        pendingAudioChunks.current.push(audioData);
        audioMetricsRef.current.dropouts++;
        addLogEntry("warning", "Audio buffer overflow - dropping oldest chunk");
      }
      return false;
    }

    // Use retry mechanism for failed sends
    return await retryAudioChunk(audioData, 0);
  }, [addLogEntry, checkWebSocketBackpressure, retryAudioChunk]);

  // Handle messages from AudioWorklet (moved up to fix dependency order)
  const handleAudioWorkletMessage = useCallback((event) => {
    const { type, data } = event.data;
    
    switch (type) {
      case 'AUDIO_DATA':
        sendAudioChunkWithBackpressure(data.audioData);
        break;
        
      case 'BARGE_IN_DETECTED':
        addLogEntry("vad_activation", `VAD Activated: User speech detected during playback.`);
        if (isPlayingRef.current) {
          addLogEntry(
            "barge_in", 
            `User speech detected during playback (amplitude: ${data.maxAmplitude.toFixed(3)})`
          );
          stopSystemAudioPlayback();
        }
        break;
        
      case 'METRICS':
        audioMetricsRef.current = { ...audioMetricsRef.current, ...data };
        break;
        
      default:
        console.log('Unknown AudioWorklet message:', type, data);
    }
  }, [addLogEntry, stopSystemAudioPlayback, sendAudioChunkWithBackpressure]);

  // Initialize AudioWorklet for modern audio processing (moved up to fix dependency order)
  const initializeAudioWorklet = useCallback(async () => {
    try {
      if (localAudioContextRef.current && localAudioContextRef.current.state === "closed") {
        localAudioContextRef.current = null;
      }
      
      if (!localAudioContextRef.current) {
        localAudioContextRef.current = new (window.AudioContext || window.webkitAudioContext)({
          sampleRate: INPUT_SAMPLE_RATE
        });
        
        // Set up state monitoring for the new context
        monitorAudioContextState(localAudioContextRef.current, 'LocalAudioContext');
      }
      
      // Load AudioWorklet module
      await localAudioContextRef.current.audioWorklet.addModule(AUDIO_WORKLET_URL);
      
      // Create AudioWorklet node
      audioWorkletNodeRef.current = new AudioWorkletNode(
        localAudioContextRef.current,
        'audio-processor'
      );
      
      // Set up message handling
      audioWorkletNodeRef.current.port.onmessage = handleAudioWorkletMessage;
      
      addLogEntry("mic", "AudioWorklet initialized successfully");
      return true;
    } catch (error) {
      addLogEntry("error", `Failed to initialize AudioWorklet: ${error.message}`);
      console.error("AudioWorklet initialization error:", error);
      return false;
    }
  }, [addLogEntry, handleAudioWorkletMessage, monitorAudioContextState]);

  // Fallback ScriptProcessorNode implementation (moved up to fix dependency order)
  const initializeScriptProcessorFallback = useCallback(() => {
    try {
      addLogEntry("info", "Initializing ScriptProcessorNode fallback");
      // This would implement the old ScriptProcessorNode approach if needed
      // For now, we'll indicate that fallback is not implemented
      addLogEntry("error", "ScriptProcessorNode fallback not implemented - please use a modern browser");
      return false;
    } catch (error) {
      addLogEntry("error", `ScriptProcessorNode fallback failed: ${error.message}`);
      return false;
    }
  }, [addLogEntry]);

  // Check AudioWorklet support with fallback
  const checkAudioWorkletSupport = useCallback(async () => {
    try {
      if (typeof AudioWorkletNode === 'undefined' || !window.AudioContext) {
        throw new Error('AudioWorklet not supported');
      }

      // Test AudioWorklet creation
      const testContext = new AudioContext();
      await testContext.audioWorklet.addModule(AUDIO_WORKLET_URL);
      testContext.close();
      
      audioWorkletSupported.current = true;
      addLogEntry("success", "AudioWorklet support confirmed");
      return true;
    } catch (error) {
      audioWorkletSupported.current = false;
      addLogEntry("warning", `AudioWorklet not supported: ${error.message}`);
      addLogEntry("info", "Falling back to ScriptProcessorNode (deprecated)");
      return false;
    }
  }, [addLogEntry]);

  // Enhanced AudioWorklet initialization with fallback
  const initializeAudioWorkletWithFallback = useCallback(async () => {
    // First check if AudioWorklet is supported
    const isSupported = await checkAudioWorkletSupport();
    
    if (isSupported) {
      return await initializeAudioWorklet();
    } else {
      // Fallback to ScriptProcessorNode (for older browsers)
      addLogEntry("warning", "Using deprecated ScriptProcessorNode as fallback");
      return initializeScriptProcessorFallback();
    }
  }, [addLogEntry, checkAudioWorkletSupport, initializeAudioWorklet, initializeScriptProcessorFallback]);




  // Process pending audio chunks
  const processPendingAudioChunks = useCallback(async () => {
    while (pendingAudioChunks.current.length > 0 && !checkWebSocketBackpressure()) {
      const chunk = pendingAudioChunks.current.shift();
      const sent = await sendAudioChunkWithBackpressure(chunk);
      if (!sent) break; // If we couldn't send, put it back and stop
    }
  }, [sendAudioChunkWithBackpressure, checkWebSocketBackpressure]);

  // Periodic processing of pending audio chunks
  useEffect(() => {
    const interval = setInterval(() => {
      if (pendingAudioChunks.current.length > 0) {
        processPendingAudioChunks();
      }
    }, 100); // Check every 100ms

    return () => clearInterval(interval);
  }, [processPendingAudioChunks]);



  const handleStartListening = useCallback(
    async (isResuming = false) => {
      if (isRecordingRef.current && !isResuming) {
        addLogEntry(
          "mic_control",
          "Mic already active. Start request ignored."
        );
        return;
      }
      if (!isSessionActiveRef.current) {
        addLogEntry(
          "mic_control",
          "Session not active. Cannot start microphone."
        );
        return;
      }
      addLogEntry(
        "mic_control",
        isResuming
          ? "Resume Microphone Input requested."
          : "Start Microphone Input requested as part of session."
      );

      if (!isResuming) {
        await getPlaybackAudioContext("handleStartListening_UserAction");
      }

      if (
        !mediaStreamRef.current ||
        !localAudioContextRef.current ||
        localAudioContextRef.current.state === "closed" ||
        !audioWorkletNodeRef.current
      ) {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          addLogEntry("error", "getUserMedia not supported on your browser!");
          setIsSessionActive(false);
          return;
        }
        try {
          addLogEntry("mic", "Requesting microphone access for new stream...");
          mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({
            audio: {sampleRate: INPUT_SAMPLE_RATE, channelCount: 1},
          });
          addLogEntry("mic", "Microphone access GRANTED.");

          // Initialize AudioWorklet with fallback support
          const audioWorkletInitialized = await initializeAudioWorkletWithFallback();
          if (!audioWorkletInitialized) {
            addLogEntry("error", "Failed to initialize AudioWorklet");
            setIsSessionActive(false);
            return;
          }

          // Create media stream source and connect to AudioWorklet
          const source = localAudioContextRef.current.createMediaStreamSource(
            mediaStreamRef.current
          );
          source.connect(audioWorkletNodeRef.current);
          
          // Send initial configuration to AudioWorklet
          audioWorkletNodeRef.current.port.postMessage({
            type: 'UPDATE_CONFIG',
            data: {
              bufferSize: MIC_BUFFER_SIZE,
              bargeInThreshold: 0.04,
              noiseSuppression: true
            }
          });
          
          addLogEntry("mic", "AudioWorklet processing chain established.");
        } catch (err) {
          console.error("Failed to start microphone:", err);
          addLogEntry(
            "error",
            `Mic Setup Error: ${err.message}. Please check permissions.`
          );
          setIsSessionActive(false);
          if (
            socketRef.current &&
            socketRef.current.readyState === WebSocket.OPEN
          ) {
            socketRef.current.close(
              1000,
              "Mic setup failed during session start"
            );
          }
          return;
        }
      } else if (localAudioContextRef.current.state === "suspended") {
        try {
          await localAudioContextRef.current.resume();
          addLogEntry("mic", "Local AudioContext for microphone resumed.");
        } catch (e) {
          addLogEntry(
            "error",
            `Could not resume local audio context for mic: ${e.message}`
          );
          return;
        }
      }
      // Notify AudioWorklet that recording has started
      if (audioWorkletNodeRef.current) {
        audioWorkletNodeRef.current.port.postMessage({
          type: 'SET_RECORDING',
          data: { recording: true }
        });
      }
      
      setIsRecording(true);
      addLogEntry("mic_status", "Microphone is NOW actively sending data.");
    },
    [addLogEntry, initializeAudioWorkletWithFallback, getPlaybackAudioContext]
  );

  const handlePauseListening = useCallback(() => {
    if (!isRecordingRef.current) {
      addLogEntry(
        "mic_control",
        "Not currently sending mic data. Pause request ignored."
      );
      return;
    }
    addLogEntry("mic_control", "Pause Microphone Input requested by user.");
    
    // Notify AudioWorklet to stop recording
    if (audioWorkletNodeRef.current) {
      audioWorkletNodeRef.current.port.postMessage({
        type: 'SET_RECORDING',
        data: { recording: false }
      });
    }
    
    setIsRecording(false);
    addLogEntry("mic_status", "Microphone is NOW paused (not sending data).");
  }, [addLogEntry]);

  const handleStopListeningAndCleanupMic = useCallback(() => {
    addLogEntry(
      "mic_control",
      "Full Microphone Stop and Resource Cleanup requested."
    );
    setIsRecording(false);

    // Stop AudioWorklet recording
    if (audioWorkletNodeRef.current) {
      audioWorkletNodeRef.current.port.postMessage({
        type: 'SET_RECORDING',
        data: { recording: false }
      });
      audioWorkletNodeRef.current.disconnect();
      audioWorkletNodeRef.current = null;
      addLogEntry(
        "mic_resource",
        "AudioWorklet disconnected and nullified."
      );
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
      addLogEntry("mic_resource", "MediaStream tracks stopped and nullified.");
    }
    if (localAudioContextRef.current) {
      if (localAudioContextRef.current.state !== "closed") {
        localAudioContextRef.current
          .close()
          .then(() => {
            addLogEntry("mic_resource", "Local AudioContext for mic closed.");
          })
          .catch((e) => {
            addLogEntry(
              "error",
              `Error closing Local AudioContext for mic: ${e.message}`
            );
          });
      }
      localAudioContextRef.current = null;
    }
    audioChunkSentCountRef.current = 0;
    addLogEntry("mic_status", "Microphone resources cleaned up.");
  }, [addLogEntry]);

  const connectWebSocket = useCallback(
    (language) => {
      if (
        socketRef.current &&
        (socketRef.current.readyState === WebSocket.OPEN ||
          socketRef.current.readyState === WebSocket.CONNECTING)
      ) {
        if (socketRef.current.url.includes(`lang=${language}`)) {
          addLogEntry(
            "ws",
            `WebSocket already open or connecting with ${language}.`
          );
          if (isSessionActiveRef.current && !isRecordingRef.current) {
            handleStartListening(false);
          }
          return;
        }
        addLogEntry(
          "ws",
          `Closing existing WebSocket (url: ${socketRef.current.url}, state: ${socketRef.current.readyState}) before new connection for lang ${language}.`
        );
        socketRef.current.close(
          1000,
          "New connection with different language initiated by connectWebSocket"
        );
      }

      addLogEntry(
        "ws",
        `Attempting to connect to WebSocket with language: ${language}...`
      );
      setWebSocketStatus("Connecting...");
      socketRef.current = new WebSocket(
        `ws://${BACKEND_HOST}/listen?lang=${language}`
      );
      socketRef.current.binaryType = "arraybuffer";

      socketRef.current.onopen = () => {
        setWebSocketStatus("Open");
        addLogEntry("ws", `WebSocket Connected (Lang: ${language}).`);
        if (isSessionActiveRef.current) {
          addLogEntry(
            "session_flow",
            "Session is active. Proceeding to start microphone input via handleStartListening."
          );
          handleStartListening(false); // This will set isRecording to true
          setIsMuted(false); // Ensure mic is unmuted when session starts/restarts
        } else {
          addLogEntry(
            "ws_warn",
            "WebSocket opened, but session is NOT marked active. Mic not started."
          );
        }
      };

      socketRef.current.onmessage = (event) => {
        if (typeof event.data === "string") {
          try {
            const receivedData = JSON.parse(event.data);
            if (receivedData.type && receivedData.type.endsWith("_update")) {
              addLogEntry(
                receivedData.type,
                `${receivedData.sender}: ${receivedData.text} (Final: ${receivedData.is_final})`
              );
              setTranscriptionMessages((prevMessages) => {
                const existingMessageIndex = prevMessages.findIndex(
                  (msg) => msg.id === receivedData.id
                );
                if (existingMessageIndex !== -1) {
                  return prevMessages.map((msg) =>
                    msg.id === receivedData.id
                      ? {
                          ...msg,
                          text: receivedData.text,
                          is_final: receivedData.is_final,
                        }
                      : msg
                  );
                } else {
                  return [
                    ...prevMessages,
                    {
                      id: receivedData.id,
                      text: receivedData.text,
                      sender: receivedData.sender,
                      is_final: receivedData.is_final,
                    },
                  ];
                }
              });
            } else if (receivedData.type === "error") {
              addLogEntry(
                "error",
                `Server Error via WS: ${receivedData.message}`
              );
            } else {
              addLogEntry(
                "ws_json_unhandled",
                `Unhandled JSON: ${event.data.substring(0, 150)}...`
              );
            }
          } catch (e) {
            addLogEntry(
              "error",
              `Failed to parse JSON from WS: ${
                e.message
              }. Raw: ${event.data.substring(0, 150)}...`
            );
          }
        } else if (event.data instanceof ArrayBuffer) {
          audioQueueRef.current.push(event.data);
          if (!isPlayingRef.current) playNextGeminiChunk();
        } else {
          addLogEntry(
            "ws_unknown_type",
            `Received unknown data type from WS: ${typeof event.data}`
          );
        }
      };

      socketRef.current.onerror = (error) => {
        console.error("WebSocket Error:", error);
        setWebSocketStatus("Error");
        addLogEntry("error", `WebSocket error. Details in console.`);
        if (isSessionActiveRef.current) {
          addLogEntry(
            "session_flow",
            "Session active during WebSocket error. Terminating session."
          );
          setIsSessionActive(false);
          handleStopListeningAndCleanupMic();
        }
      };

      socketRef.current.onclose = (event) => {
        setWebSocketStatus("Closed");
        addLogEntry(
          "ws",
          `WebSocket Disconnected. Code: ${event.code}, Reason: "${
            event.reason || "No reason given"
          }"`
        );
        const intentionalCloseReasons = [
          "User stopped session",
          "Language changed during active session - stopping session",
          "Component unmounting",
          "New connection with different language initiated by connectWebSocket",
          "Mic setup failed during session start",
          "getUserMedia not supported",
        ];
        if (
          !intentionalCloseReasons.includes(event.reason) &&
          event.code !== 1000 &&
          event.code !== 1005
        ) {
          addLogEntry(
            "error",
            `WebSocket closed unexpectedly (Code: ${event.code}, Reason: "${event.reason}"). Session terminated if active.`
          );
          if (isSessionActiveRef.current) {
            setIsSessionActive(false);
            handleStopListeningAndCleanupMic();
          }
        } else {
          addLogEntry(
            "ws_info",
            `WebSocket closed intentionally or expectedly (Reason: "${event.reason}", Code: ${event.code}).`
          );
        }
        if (
          isSessionActiveRef.current &&
          !intentionalCloseReasons.includes(event.reason) &&
          event.code !== 1000
        ) {
          addLogEntry(
            "session_flow_warn",
            "Unexpected WS close during active session. Ensuring session is marked inactive."
          );
          setIsSessionActive(false);
        }
      };
    },
    [
      addLogEntry,
      playNextGeminiChunk,
      handleStartListening,
      handleStopListeningAndCleanupMic,
    ]
  );

  const handleToggleSession = useCallback(async () => {
    if (isSessionActiveRef.current) {
      addLogEntry("session_control", "User requested to STOP session.");
      handleStopListeningAndCleanupMic();
      if (
        socketRef.current &&
        (socketRef.current.readyState === WebSocket.OPEN ||
          socketRef.current.readyState === WebSocket.CONNECTING)
      ) {
        addLogEntry(
          "ws_control",
          "Closing WebSocket due to session stop request."
        );
        socketRef.current.close(1000, "User stopped session");
      }
      setIsSessionActive(false);
      setIsMuted(false); // Reset mute state when session stops
      addLogEntry("session_status", "Session INACTIVE.");
    } else {
      addLogEntry("session_control", "User requested to START session.");
      await getPlaybackAudioContext("handleToggleSession_UserAction_Start");

      const currentLangName =
        LANGUAGES.find((l) => l.code === selectedLanguage)?.name ||
        selectedLanguage;
      addLogEntry(
        "session_flow",
        `Attempting to connect WebSocket for session start (Language: ${currentLangName}).`
      );

      setIsSessionActive(true);
      setIsMuted(false); // Ensure mic is unmuted when starting a new session
      connectWebSocket(selectedLanguage);
      addLogEntry(
        "session_status",
        "Session PENDING (WebSocket connecting, Mic to start on WS open)."
      );
    }
  }, [
    selectedLanguage,
    connectWebSocket,
    handleStopListeningAndCleanupMic,
    addLogEntry,
    getPlaybackAudioContext,
  ]);

  const handleMicMuteToggle = useCallback(() => {
    if (!isSessionActiveRef.current) return;

    if (isRecordingRef.current) {
      setIsMuted((prevMuted) => {
        const newMutedState = !prevMuted;
        addLogEntry(
          "mic_control",
          `Microphone ${newMutedState ? "MUTED" : "UNMUTED"}.`
        );
        return newMutedState;
      });
    } else {
      // If session is active but not recording (e.g., after explicit pause, or initial state)
      addLogEntry(
        "mic_control",
        "Mic button (unmute/start) pressed while not recording in active session. Attempting to start mic."
      );
      setIsMuted(false); // Ensure unmuted
      handleStartListening(); // This will set isRecording to true
    }
  }, [addLogEntry, handleStartListening]);

  useEffect(() => {
    const currentLangName =
      LANGUAGES.find((l) => l.code === selectedLanguage)?.name ||
      selectedLanguage;
    addLogEntry(
      "system_event",
      `Language selection changed to: ${currentLangName} (${selectedLanguage}).`
    );

    if (isSessionActiveRef.current) {
      addLogEntry(
        "session_control",
        `Language changed during an active session. Stopping current session.`
      );
      handleStopListeningAndCleanupMic();
      if (
        socketRef.current &&
        (socketRef.current.readyState === WebSocket.OPEN ||
          socketRef.current.readyState === WebSocket.CONNECTING)
      ) {
        socketRef.current.close(
          1000,
          "Language changed during active session - stopping session"
        );
      }
      setIsSessionActive(false);
      addLogEntry(
        "system_message",
        `Session stopped due to language change. Please click "Start Session" again if you wish to continue with ${currentLangName}.`
      );
    }

    return () => {
      addLogEntry("system_event", "App component unmounting.");
      if (isSessionActiveRef.current) {
        addLogEntry(
          "session_control",
          "Unmounting with active session. Cleaning up resources."
        );
        handleStopListeningAndCleanupMic();
        if (
          socketRef.current &&
          (socketRef.current.readyState === WebSocket.OPEN ||
            socketRef.current.readyState === WebSocket.CONNECTING)
        ) {
          addLogEntry("ws_control", `Component unmounting: Closing WebSocket.`);
          socketRef.current.close(1000, "Component unmounting");
        }
      }
    };
  }, [selectedLanguage, addLogEntry, handleStopListeningAndCleanupMic]);

  const handleSendTextMessage = useCallback(() => {
    if (!textInputValue.trim()) return;
    const currentLangName =
      LANGUAGES.find((l) => l.code === selectedLanguage)?.name ||
      selectedLanguage;
    addLogEntry(
      "user_text",
      `User typed (Lang: ${currentLangName}): "${textInputValue}"`
    );
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      const messagePayload = {
        type: "text_message",
        text: textInputValue,
        language: selectedLanguage,
        timestamp: new Date().toISOString(),
        id: generateUniqueId(),
      };
      socketRef.current.send(JSON.stringify(messagePayload));
      setTranscriptionMessages((prev) => [
        ...prev,
        {
          id: messagePayload.id,
          sender: "user",
          text: textInputValue,
          is_final: true,
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
      setTextInputValue("");
    } else {
      addLogEntry(
        "error",
        "Cannot send text: WebSocket not connected or not open."
      );
    }
  }, [textInputValue, addLogEntry, selectedLanguage]);

  const handleClearConsole = () => {
    setMessages([]);
    addLogEntry("console", "Console cleared by user.");
  };

  useEffect(() => {
    addLogEntry("status", 'Welcome! Click "Start Session" or type your query.');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="app-container">
      <div className="console-panel">
        <div className="console-header">
          <h2>Console</h2>
          <div className="console-header-controls">
            <select
              className="console-dropdown"
              defaultValue="conversations">
              <option value="conversations">Conversations</option>
            </select>
            {/* console-paused-button removed as its info is now in control-bar */}
          </div>
        </div>
        <div
          className="logs-area"
          ref={logsAreaRef}>
          {isLoading && <p className="loading-indicator">Loading...</p>}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`log-entry log-entry-${msg.type} ${
                msg.type === "toolcall" ? "log-entry-toolcall" : ""
              }`}>
              <span className="log-timestamp">[{msg.timestamp}] </span>
              <span className="log-prefix">{msg.type.toUpperCase()}: </span>
              <span className="log-message">{msg.content}</span>
            </div>
          ))}
        </div>
        <div className="text-input-area console-text-input-area">
          <input
            type="text"
            className="text-input"
            value={textInputValue}
            onChange={(e) => setTextInputValue(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSendTextMessage()}
            placeholder="Type something..."
            disabled={!isSessionActive}
          />
          <button
            onClick={handleSendTextMessage}
            className="control-button send-button"
            disabled={!textInputValue.trim() || !isSessionActive}>
            <FontAwesomeIcon icon={faPaperPlane} />
          </button>
        </div>
      </div>

      <div className="main-panel">
        <div className="main-panel-header">
          <h2>Transcriptions</h2>
        </div>
        <div
          className="results-content chat-area"
          ref={chatAreaRef}>
          {transcriptionMessages.length === 0 && (
            <div className="results-content-placeholder">
              <p>
                Audio transcriptions will appear here when a session is active.
              </p>
            </div>
          )}
          {transcriptionMessages.map((msg) => (
            <div
              key={msg.id}
              className={`chat-bubble ${
                msg.sender === "user" ? "user-bubble" : "ai-bubble"
              }`}>
              <div className="chat-bubble-text">{msg.text}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="control-bar">
        <div className="control-tray main-controls">
          <button
            onClick={handleToggleSession}
            className="control-button icon-button session-button"
            title={
              isSessionActive ? "Stop Current Session" : "Start a New Session"
            }>
            <div className="icon-button-content">
              <FontAwesomeIcon icon={isSessionActive ? faStop : faPlay} />
              <span className="icon-button-text">
                {isSessionActive ? "Stop" : "Start"}
              </span>
            </div>
          </button>
          <button
            onClick={handleMicMuteToggle}
            className={`control-button icon-button mic-button ${
              isRecording && !isMutedRef.current ? "active" : ""
            } ${isMutedRef.current ? "muted" : ""}`}
            disabled={!isSessionActiveRef.current}
            title={
              isMutedRef.current
                ? "Unmute Microphone"
                : isRecordingRef.current
                ? "Mute Microphone"
                : "Start Microphone"
            }>
            <div className="icon-button-content">
              <FontAwesomeIcon
                icon={isMutedRef.current ? faMicrophoneSlash : faMicrophone}
              />
              <span className="icon-button-text">
                {isMutedRef.current ? "Muted" : "Unmuted"}
              </span>
            </div>
          </button>
          <div className="audio-signal-placeholder">
            {isRecording && !isMuted && (
              <div className="audio-wave">
                <span></span>
                <span></span>
                <span></span>
                <span></span>
                <span></span>
              </div>
            )}
          </div>
        </div>
        <div className="control-tray secondary-controls">
          <select
            value={selectedLanguage}
            onChange={(e) => setSelectedLanguage(e.target.value)}
            disabled={isSessionActiveRef.current}
            className="language-selector-dropdown"
            title="Select Language (Session restarts on change if active)">
            {LANGUAGES.map((lang) => (
              <option
                key={lang.code}
                value={lang.code}>
                {lang.name}
              </option>
            ))}
          </select>
          <div
            className="status-indicator icon-status-indicator websocket-status"
            title="WebSocket Connection Status">
            <div className="icon-status-content">
              <FontAwesomeIcon icon={faWifi} />
              <span className="icon-status-text">WS: {webSocketStatus}</span>
            </div>
          </div>
          <div
            className="status-indicator icon-status-indicator session-active-status"
            title="Session Status">
            <div className="icon-status-content">
              <FontAwesomeIcon icon={faPowerOff} />
              <span className="icon-status-text">
                {isSessionActiveRef.current
                  ? "Session: Active"
                  : "Session: Inactive"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
