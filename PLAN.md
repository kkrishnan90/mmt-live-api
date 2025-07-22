# Plan of Approach to Fix Issues in Make My Trip AI Assistant

This document outlines a detailed plan to address the challenges identified in the `GEMINI.md` file. The plan is broken down by each challenge and follows the critical instructions provided.

### 1. Fix Choppy Audio on the Frontend

This is likely a client-side issue, so the focus will be on the frontend code.

*   **Step 1: Analyze Frontend Code:** Read `frontend/src/App.js` and `frontend/public/audio-processor.js` to understand how audio is captured, processed, and sent to the backend. Look for potential bottlenecks or inefficient code causing choppiness.
*   **Step 2: Analyze `nginx.conf`:** Analyze the `nginx.conf` file to check for any configurations that could be affecting audio streaming.
*   **Step 3: Check for Large Payloads:** Investigate the size of the audio chunks being sent. If they are too large, it could cause delays. Also, check for any unnecessary data being sent with the audio.
*   **Step 4: Implement and Test Fixes:** Based on the analysis, propose and implement fixes. This could involve optimizing audio processing code, adjusting audio chunk size, or implementing a more efficient audio encoding format.

### 2. MUST always prefer Hindi and Indian English ONLY as the audio output

This is a configuration issue in the `tool_call.json` file.

*   **Step 1: Modify `tool_call.json`:** Modify the `speechConfig` in `tool_call.json` to ensure the `languageCode` is set to `en-IN` and the `voiceConfig` uses an appropriate Indian English voice. Research alternatives to the current `Zephyr` voice if more suitable ones are available.
*   **Step 2: Verify in `system_instructions.txt`:** Ensure that `system_instructions.txt` also reinforces the use of Hindi and Indian English.

### 3. Sometimes the model is speaking those that are being thought

This is a critical issue to prevent the model from revealing its internal reasoning.

*   **Step 1: Analyze `tool_call.json`:** Examine `tool_call.json` for a `thinkingConfig` or similar setting that can be adjusted. Research the Gemini Live API documentation to confirm the correct setting to disable thinking output, as suggested by `GEMINI.md` (`NONE`).
*   **Step 2: Modify `system_instructions.txt`:** Add a stronger, more prominent instruction in `system_instructions.txt` to explicitly forbid the model from revealing its thinking process.

### 4. The tool calling fails at times

This is a broad issue requiring systematic investigation.

*   **Step 1: Analyze `tool_call.json` and `system_instructions.txt`:** Carefully review the function definitions in `tool_call.json` and the instructions in `system_instructions.txt` to ensure they are clear, consistent, and optimized for tool calling. Identify and resolve any ambiguities or contradictions.
*   **Step 2: Clean Up and Modularize Function Calls:** As per `GEMINI.md`, clean up existing function calls and ensure they strictly adhere to the definitions in `tool_call.json`. Look for opportunities to modularize the code to improve clarity and maintainability.
*   **Step 3: Implement Mock API Endpoints:** Create mock endpoints for each function defined in `tool_call.json`. This will allow for isolated testing of the tool-calling functionality.
*   **Step 4: Rigorous Testing:** Create a comprehensive test suite to rigorously test the tool-calling functionality, covering various scenarios, especially those known to fail.

### 5. VAD configuration to be fine tuned

This is key to improving the user experience by ignoring filler words.

*   **Step 1: Analyze `tool_call.json`:** Examine the `realtimeInputConfig` in `tool_call.json` to understand the current Voice Activity Detection (VAD) configuration.
*   **Step 2: Research VAD Best Practices:** Research best practices for configuring VAD for this specific use case, focusing on tuning it to be less sensitive to filler words and background noise.
*   **Step 3: Propose and Test New Configurations:** Based on the research, propose and test new VAD configurations using a variety of audio samples to ensure they effectively filter out unwanted noise.

### Critical Instructions Adherence

Throughout this process, all critical instructions from `GEMINI.md` will be strictly followed. The work will be meticulous, prioritizing clean, modular, and well-documented code. The `context7` MCP server will be used for any required documentation lookups.
