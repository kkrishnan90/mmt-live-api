# Project Overview

The project goal is to create an AI assistant that is voice based and can assistant Make My Trip in various parts of the post booking journey for its customer. Examples are,

- Flight confirmation
- Modifying booking

# Environment

- React frontend
- Python Backend
- use `uv` for package management
- ALWAYS activate the environment before installation or running any python commands
- Read the @system_instructions.txt and @tool_call.json
- The @system_instruction contains the persona of the AI assistant
- The @tool_call.json contains all the necessary function calls that needs to be programmed and used by the AI assistant
- For now, you can use mockup api endpoints to create the functions for tool calling

# Current Challanges to fix in the code

- Choppy audio on the frontend
- MUST always prefer Hindi and Indian english ONLY as the audio output
- Sometimes the model is speaking those that are being thought (Need to check and fix thinkingConfig to set to NONE or as per documentation)
- The tool calling fails at times
- VAD configuration (Voice Activity Detection) to be fine tuned for such a use case to avoid capturing filler words like uh, um, etc. spoken by the user

# CRITICAL INSTRUCTIONS

- You MUST ensure that you do not break the existing code but apply the fixes meticulously and carefully after analysing
- You MUST ensure that the @system_instructions.txt provided is fine tuned for optimised function calling and also not to bloat the tokens with explaining each scenario to the model
- You MUST ensure clean code always and modularised pattern
- You MUST STRICTLY clean up existing function calls and stick to the function calls provided by the user in @tool_call.json
- You MUST STRICTLY avoid hallucinations AND overengineering the codebase
- You MUST ALWAYS use context7 MCP server tool provided to you for any latest documentation

# Documentation References

- https://cloud.google.com/vertex-ai/generative-ai/docs/live-api
- https://ai.google.dev/gemini-api/docs/live
- https://ai.google.dev/gemini-api/docs/live-guide
- https://ai.google.dev/gemini-api/docs/live-tools
- https://ai.google.dev/gemini-api/docs/live-session
