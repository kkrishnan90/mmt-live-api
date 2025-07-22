import asyncio
import os
import traceback
import uuid  # Added for generating unique IDs
import sys  # Added for stdout redirection
import io  # Added for stdout redirection
import json  # Added for parsing log strings
from quart import Quart, websocket, jsonify
from quart_cors import cors
from websockets.exceptions import ConnectionClosedOK
import google.genai as genai
from google.genai import types  # Crucial for Content, Part, Blob
from dotenv import load_dotenv
from datetime import datetime, timezone  # For timestamping raw stdout logs

from gemini_tools import (
    travel_tool,
    NameCorrectionAgent,
    SpecialClaimAgent,
    Enquiry_Tool,
    Eticket_Sender_Agent,
    ObservabilityAgent,
    DateChangeAgent,
    Connect_To_Human_Tool,
    Booking_Cancellation_Agent,
    Flight_Booking_Details_Agent,
    Webcheckin_And_Boarding_Pass_Agent
)
from travel_mock_data import GLOBAL_LOG_STORE  # Import the global log store

load_dotenv()

# --- Log Capturing Setup ---
CAPTURED_STDOUT_LOGS = []
_original_stdout = sys.stdout


class StdoutTee(io.TextIOBase):
    def __init__(self, original_stdout, log_list):
        self._original_stdout = original_stdout
        self._log_list = log_list

    def write(self, s):
        self._original_stdout.write(s)  # Write to original stdout (console)
        s_stripped = s.strip()
        if s_stripped:  # Avoid empty lines
            try:
                # Attempt to parse as JSON, assuming logs from gemini_tools are JSON strings
                log_entry = json.loads(s_stripped)
                # Ensure it has the expected structure for frontend if it's a TOOL_EVENT
                if isinstance(log_entry, dict) and log_entry.get("log_type") == "TOOL_EVENT":
                    self._log_list.append(log_entry)
                else:  # Not a TOOL_EVENT or not a dict, store as raw with context
                    self._log_list.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "log_type": "RAW_STDOUT",
                        "message": s_stripped,
                        "parsed_json": log_entry if isinstance(log_entry, dict) else None
                    })
            except json.JSONDecodeError:
                # If it's not JSON, store it as a raw string entry
                self._log_list.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "log_type": "RAW_STDOUT",
                    "message": s_stripped
                })
        return len(s)

    def flush(self):
        self._original_stdout.flush()


sys.stdout = StdoutTee(_original_stdout, CAPTURED_STDOUT_LOGS)
# --- End Log Capturing Setup ---

try:
    use_vertex_ai = os.getenv(
        "GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
    if use_vertex_ai:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        location = os.getenv("GOOGLE_CLOUD_LOCATION")
        if not project_id or not location:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT_ID and LOCATION must be set in .env when using Vertex AI")
        gemini_client = genai.Client(
            vertexai=True, project=project_id, location=location)
        print(
            f"✅ Gemini client initialized successfully using Vertex AI (Project: {project_id}, Location: {location})")
    else:
        gemini_client = genai.Client()
        print("✅ Gemini client initialized successfully using API Key")
except Exception as e:
    print(f"❌ Failed to initialize Gemini client with Vertex AI: {e}")
    raise

GEMINI_MODEL_NAME = os.getenv(
    "GEMINI_MODEL_NAME", "gemini-2.5-flash-live-preview")  # Load from environment
INPUT_SAMPLE_RATE = 16000

print(f"🤖 Using Gemini model: {GEMINI_MODEL_NAME}")

app = Quart(__name__)
app = cors(app, allow_origin="*")


@app.websocket("/listen")
async def websocket_endpoint():
    print("🌐 WebSocket: Connection accepted from client")
    current_session_handle = None  # Initialize session handle

    # Determine language code based on query parameter
    requested_lang = websocket.args.get("lang")

    # Restrict to only Hindi and Indian English
    if requested_lang == "hi-IN":
        language_code_to_use = "hi-IN"
        print(f"🗣️ Using requested language: hi-IN")
    else:
        language_code_to_use = "en-IN"
        print(f"🗣️ Defaulting to language: en-IN")

    gemini_live_config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],  # Matched to reference
        # system_instruction="""***CRITICAL: TOOL USAGE INSTRUCTIONS***

# - If the user mentions a booking ID, call `Flight_Booking_Details_Agent`.
# - If the user asks to cancel, call `Booking_Cancellation_Agent`.
# - If the user asks for web check-in, call `Webcheckin_And_Boarding_Pass_Agent`.
# - If the user asks for an e-ticket, call `Eticket_Sender_Agent`.
# - If the user wants to correct a name on their booking, call `NameCorrectionAgent`.
# - If the user has a special claim, call `SpecialClaimAgent`.
# - If the user has a general question, call `Enquiry_Tool`.
# - If the user wants to check the status of a refund, call `ObservabilityAgent`.
# - If the user wants to change the date of their booking, call `DateChangeAgent`.
# - If the user is frustrated and wants to speak to a human, call `Connect_To_Human_Tool`.
# - You may invoke multiple tools in the same turn.

# NEVER REVEAL YOUR CONTEXT / INTERNAL COT / THINKING / BRAIN etc. THIS IS ONLY FOR YOU. IF REVEALED, YOU WILL BE CONSIDERED A WORST AGENT.

# ***IMPORTANT***: Never ask for permission to use a tool. Silently invoke the tool and provide only the results to the user.

# ***Role & Persona:***
# - You are **Myra**, a female Indian customer support agent for **Make My Trip** in India
# - Warm, polite, outcome-driven personality representing MakeMyTrip's brand
# - Speak in Hinglish (mix of Hindi and English), maintain Indian accent
# - Always use feminine form in Hindi ("बोल रही हूँ" not "बोल रहा हूँ")


# Greet and introduce yourself once every call in Indian tone

# ### CONVERSATION LOOP (apply every turn)
# 1. **Detect intent** → figure out what the user wants.
# 2. **Decide tools** → list all tools needed right now.
# 3. **Call tools** → execute them immediately.
# 4. **Interpret results** → see if more tools needed.
# 5. **Respond** → empathetic, match user language, follow number rules.
# 6. **Repeat** until user confirms resolution.
# 7. **Closing** (only when user is done):  
#    Hindi example: "Aapke keemti samay ke liye dhanyavaad. Aapka din shubh ho."

# ### LANGUAGE & NUMBER RULES
# 1. **Detect the user's language (Hindi or English) and respond ONLY in that language.**
# 2. **Numbers** (booking IDs, fares, times, flight nos., phone nos.) spoken in English digits.
# 2. **Prices < ₹10,000** → “Thirty seven hundred”, etc.  
# 3. **Prices ≥ ₹10,000** → “Twelve thousand five hundred”, use lakh/crore when large.  
# 4. **Flight numbers** → airline + digits individually (“Indigo Three Seven Two”).  
# 5. **Phone numbers** → digit‑by‑digit.  
# 6. **Booking IDs** → mention only last three characters (“booking ending with 841”).  
# 7. Never re‑ask for a booking ID already known.

# ### SCOPE & BEHAVIOR
# - Handle only **post‑booking queries** for flights and hotels.
# - No competitor pricing; no policy overrides.
# - If platform errors, apologize briefly, retry sensibly, or ask for needed info once.
# - Multiple speakers: focus on the clearest voice.

# ***Restrictions:***
# - Only handle post-booking travel queries
# - No comparisons with competitors  
# - No arguments or policy overrides
# - Focus on the loudest/clearest voice if multiple speakers


# """,,
        speech_config=types.SpeechConfig(
            language_code=language_code_to_use
        ),

        input_audio_transcription={},
        output_audio_transcription={},
        session_resumption=types.SessionResumptionConfig(
            handle=current_session_handle),  # Added from reference
        context_window_compression=types.ContextWindowCompressionConfig(  # Added from reference
            sliding_window=types.SlidingWindow(),
        ),
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False,
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                prefix_padding_ms=200,
                silence_duration_ms=800,
            )
        ),

        generationConfig=types.GenerationConfig(
            thinkingConfig=types.GenerationConfigThinkingConfig(
                includeThoughts=False
            )
        ),
        tools=[travel_tool]  # Added travel_tool here
    )

    print(
        f"🧳 Travel tool configured with {len(travel_tool.function_declarations)} functions:")
    for func in travel_tool.function_declarations:
        print(f"   - {func.name}")

    print(
        f"🤖 Attempting to connect to Gemini Live API (model: {GEMINI_MODEL_NAME})...")

    try:
        async with gemini_client.aio.live.connect(
            model=GEMINI_MODEL_NAME,
            config=gemini_live_config
        ) as session:
            print("✅ Successfully connected to Gemini Live API")
            # print(f"Quart Backend: Gemini session connected for model {GEMINI_MODEL_NAME} with tools.")
            active_processing = True

            async def handle_client_input_and_forward():
                nonlocal active_processing
                # print("Quart Backend: Starting handle_client_input_and_forward task.")
                try:
                    while active_processing:
                        try:
                            client_data = await asyncio.wait_for(websocket.receive(), timeout=0.2)

                            if isinstance(client_data, str):
                                message_text = client_data
                                # print(f"Quart Backend: Received text from client: '{message_text}'")
                                prompt_for_gemini = message_text
                                if message_text == "SEND_TEST_AUDIO_PLEASE":
                                    prompt_for_gemini = "Hello Gemini, please say 'testing one two three'."

                                # print(f"Quart Backend: Sending text prompt to Gemini: '{prompt_for_gemini}'")
                                user_content_for_text = types.Content(
                                    role="user",
                                    parts=[types.Part(text=prompt_for_gemini)]
                                )
                                await session.send_client_content(turns=user_content_for_text)
                                # print(f"Quart Backend: Prompt '{prompt_for_gemini}' sent to Gemini.")

                            elif isinstance(client_data, bytes):
                                audio_chunk = client_data
                                if audio_chunk:
                                    # print(f"Quart Backend: Received mic audio chunk: {len(audio_chunk)} bytes")
                                    # print(f"Quart Backend: Sending audio chunk ({len(audio_chunk)} bytes) to Gemini via send_realtime_input...")
                                    await session.send_realtime_input(
                                        audio=types.Blob(
                                            mime_type=f"audio/pcm;rate={INPUT_SAMPLE_RATE}",
                                            data=audio_chunk
                                        )
                                    )
                                    # print(f"Quart Backend: Successfully sent mic audio to Gemini via send_realtime_input.")
                            else:
                                print(
                                    f"Quart Backend: Received unexpected data type from client: {type(client_data)}, content: {client_data[:100] if isinstance(client_data, bytes) else client_data}")

                        except asyncio.TimeoutError:
                            if not active_processing:
                                break
                            continue  # Normal timeout, continue listening
                        except ConnectionClosedOK:
                            print("INFO: Client closed the connection.")
                            active_processing = False
                            break
                except Exception as e_fwd_outer:
                    print(
                        f"Quart Backend: Outer error in handle_client_input_and_forward: {type(e_fwd_outer).__name__}: {e_fwd_outer}")
                    traceback.print_exc()
                    active_processing = False  # Ensure outer errors also stop processing
                finally:
                    # print("Quart Backend: Stopped handling client input.")
                    active_processing = False  # Ensure graceful shutdown of the other task

            async def receive_from_gemini_and_forward_to_client():
                nonlocal active_processing, current_session_handle
                # print("Quart Backend: Starting receive_from_gemini_and_forward_to_client task.")

                available_functions = {
                    "NameCorrectionAgent": NameCorrectionAgent,
                    "SpecialClaimAgent": SpecialClaimAgent,
                    "Enquiry_Tool": Enquiry_Tool,
                    "Eticket_Sender_Agent": Eticket_Sender_Agent,
                    "ObservabilityAgent": ObservabilityAgent,
                    "DateChangeAgent": DateChangeAgent,
                    "Connect_To_Human_Tool": Connect_To_Human_Tool,
                    "Booking_Cancellation_Agent": Booking_Cancellation_Agent,
                    "Flight_Booking_Details_Agent": Flight_Booking_Details_Agent,
                    "Webcheckin_And_Boarding_Pass_Agent": Webcheckin_And_Boarding_Pass_Agent
                }
                current_user_utterance_id = None
                # Renamed from latest_user_speech_text and initialized
                accumulated_user_speech_text = ""
                current_model_utterance_id = None
                accumulated_model_speech_text = ""

                try:
                    while active_processing:
                        had_gemini_activity_in_this_iteration = False
                        async for response in session.receive():
                            had_gemini_activity_in_this_iteration = True
                            if not active_processing:
                                break

                            if response.session_resumption_update:
                                update = response.session_resumption_update
                                if update.resumable and update.new_handle:
                                    current_session_handle = update.new_handle
                                    # print(f"Quart Backend: Received session resumption update. New handle: {current_session_handle}")

                            if hasattr(response, 'session_handle') and response.session_handle:
                                new_handle = response.session_handle
                                if new_handle != current_session_handle:
                                    current_session_handle = new_handle
                                    # print(f"Quart Backend: Updated session handle from direct response.session_handle: {current_session_handle}")

                            if response.data is not None:
                                try:
                                    await websocket.send(response.data)
                                except Exception as send_exc:
                                    print(
                                        f"Quart Backend: Error sending audio data to client WebSocket: {type(send_exc).__name__}: {send_exc}")
                                    active_processing = False
                                    break

                            elif response.server_content:
                                if response.server_content.interrupted:
                                    print(
                                        "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                                    print(
                                        "Quart Backend: Gemini server sent INTERRUPTED signal.")
                                    print(
                                        "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                                    try:
                                        await websocket.send_json({"type": "interrupt_playback"})
                                        # print("Quart Backend: Sent interrupt_playback signal to client.")
                                    except Exception as send_exc:
                                        print(
                                            f"Quart Backend: Error sending interrupt_playback signal to client: {type(send_exc).__name__}: {send_exc}")
                                        active_processing = False
                                        break

                                # User Input Processing
                                if response.server_content and hasattr(response.server_content, 'input_transcription') and \
                                   response.server_content.input_transcription and \
                                   hasattr(response.server_content.input_transcription, 'text') and \
                                   response.server_content.input_transcription.text:  # Ensure text is not empty

                                    user_speech_chunk = response.server_content.input_transcription.text

                                    if current_user_utterance_id is None:  # Start of a new user utterance
                                        current_user_utterance_id = str(
                                            uuid.uuid4())
                                        accumulated_user_speech_text = ""  # Reset accumulator for new utterance

                                    accumulated_user_speech_text += user_speech_chunk

                                    if accumulated_user_speech_text:  # Only send if there's actual accumulated text
                                        payload = {
                                            'id': current_user_utterance_id,
                                            'text': accumulated_user_speech_text,  # Send accumulated text
                                            'sender': 'user',
                                            'type': 'user_transcription_update',
                                            'is_final': False
                                        }
                                        try:
                                            await websocket.send_json(payload)
                                            # Removed excessive user input logging
                                        except Exception as send_exc:
                                            print(
                                                f"Quart Backend: Error sending user transcription update to client: {type(send_exc).__name__}: {send_exc}")
                                            active_processing = False
                                            break

                                # Model Output Processing
                                if response.server_content and hasattr(response.server_content, 'output_transcription') and \
                                   response.server_content.output_transcription and \
                                   hasattr(response.server_content.output_transcription, 'text') and \
                                   response.server_content.output_transcription.text:

                                    if current_model_utterance_id is None:
                                        current_model_utterance_id = str(
                                            uuid.uuid4())
                                        accumulated_model_speech_text = ""  # Ensure accumulator is clear

                                    chunk = response.server_content.output_transcription.text
                                    if chunk:  # Only process if chunk has content
                                        accumulated_model_speech_text += chunk
                                        payload = {
                                            'id': current_model_utterance_id,
                                            'text': accumulated_model_speech_text,  # Send accumulated text
                                            'sender': 'model',
                                            'type': 'model_response_update',
                                            'is_final': False
                                        }
                                        try:
                                            await websocket.send_json(payload)
                                            # Removed excessive model output logging
                                        except Exception as send_exc:
                                            print(
                                                f"Quart Backend: Error sending model response update to client: {type(send_exc).__name__}: {send_exc}")
                                            active_processing = False
                                            break

                                # Handling Model Generation Completion
                                if response.server_content and hasattr(response.server_content, 'generation_complete') and \
                                   response.server_content.generation_complete == True:
                                    if current_model_utterance_id and accumulated_model_speech_text:  # Ensure there was a model utterance
                                        payload = {
                                            'id': current_model_utterance_id,
                                            'text': accumulated_model_speech_text,
                                            'sender': 'model',
                                            'type': 'model_response_update',
                                            'is_final': True
                                        }
                                        try:
                                            await websocket.send_json(payload)
                                            # Removed excessive final model output logging
                                        except Exception as send_exc:
                                            print(
                                                f"Quart Backend: Error sending final model response to client: {type(send_exc).__name__}: {send_exc}")
                                            active_processing = False
                                            break
                                    current_model_utterance_id = None  # Reset for next model utterance
                                    accumulated_model_speech_text = ""

                                # Handling Turn Completion (Finalizing User Speech)
                                if response.server_content and hasattr(response.server_content, 'turn_complete') and \
                                   response.server_content.turn_complete == True:
                                    if current_user_utterance_id and accumulated_user_speech_text:  # Ensure there was a user utterance
                                        payload = {
                                            'id': current_user_utterance_id,
                                            'text': accumulated_user_speech_text,  # Send final accumulated text
                                            'sender': 'user',
                                            'type': 'user_transcription_update',
                                            'is_final': True
                                        }
                                        try:
                                            await websocket.send_json(payload)
                                            print(
                                                f"🎤 User said: {accumulated_user_speech_text}")
                                        except Exception as send_exc:
                                            print(
                                                f"Quart Backend: Error sending final user transcription to client: {type(send_exc).__name__}: {send_exc}")
                                            active_processing = False
                                            break
                                    current_user_utterance_id = None  # Reset for next user utterance
                                    accumulated_user_speech_text = ""  # Reset accumulator
                                    # Also reset model states
                                    current_model_utterance_id = None
                                    accumulated_model_speech_text = ""
                                    # Removed excessive turn complete logging

                                # Fallback for other potential text or error structures (simplified)
                                is_transcription_related = (hasattr(response.server_content, 'input_transcription') and response.server_content.input_transcription) or \
                                    (hasattr(response.server_content, 'output_transcription')
                                     and response.server_content.output_transcription)
                                is_control_signal = (hasattr(response.server_content, 'generation_complete') and response.server_content.generation_complete) or \
                                                    (hasattr(response.server_content, 'turn_complete') and response.server_content.turn_complete) or \
                                                    (hasattr(
                                                        response.server_content, 'interrupted') and response.server_content.interrupted)

                                if not response.data and not is_transcription_related and not is_control_signal:
                                    unhandled_text = None
                                    if response.text:
                                        unhandled_text = response.text
                                    elif hasattr(response.server_content, 'model_turn') and response.server_content.model_turn and \
                                            hasattr(response.server_content.model_turn, 'parts'):
                                        for part in response.server_content.model_turn.parts:
                                            if part.text:
                                                unhandled_text = (
                                                    unhandled_text + " " if unhandled_text else "") + part.text
                                    elif hasattr(response.server_content, 'output_text') and response.server_content.output_text:
                                        unhandled_text = response.server_content.output_text

                                    if unhandled_text:
                                        print(
                                            f"Quart Backend: Received unhandled server_content text: {unhandled_text}")
                                    elif not response.tool_call:
                                        print(
                                            f"Quart Backend: Received server_content without primary data or known text parts: {response.server_content}")

                            elif response.tool_call:
                                print(
                                    f"\033[92mQuart Backend: Received tool_call from Gemini: {response.tool_call}\033[0m")
                                function_responses = []
                                for fc in response.tool_call.function_calls:
                                    print(
                                        f"\033[92mQuart Backend: Gemini requests function call: {fc.name} with args: {dict(fc.args)}\033[0m")

                                    function_to_call = available_functions.get(
                                        fc.name)
                                    function_response_content = None

                                    if function_to_call:
                                        try:
                                            # Execute the actual local function
                                            function_args = dict(fc.args)
                                            print(
                                                f"\033[92mQuart Backend: Calling function {fc.name} with args: {function_args}\033[0m")
                                            # Await the async function call
                                            result = await function_to_call(**function_args)
                                            if isinstance(result, str):
                                                function_response_content = {
                                                    "content": result}
                                            else:
                                                # Assumes result is already a dict if not a string
                                                function_response_content = result
                                            print(
                                                f"\033[92mQuart Backend: Function {fc.name} executed. Result: {result}\033[0m")
                                        except Exception as e:
                                            print(
                                                f"Quart Backend: Error executing function {fc.name}: {e}")
                                            traceback.print_exc()  # Add if not already there
                                            function_response_content = {
                                                "status": "error", "message": str(e)}
                                    else:
                                        print(
                                            f"Quart Backend: Function {fc.name} not found.")
                                        function_response_content = {
                                            "status": "error", "message": f"Function {fc.name} not implemented or available."}

                                    function_response = types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response=function_response_content
                                    )
                                    function_responses.append(
                                        function_response)

                                if function_responses:
                                    print(
                                        f"\033[92mQuart Backend: Sending {len(function_responses)} function response(s) to Gemini.\033[0m")
                                    await session.send_tool_response(function_responses=function_responses)
                                else:
                                    print(
                                        "Quart Backend: No function responses generated for tool_call.")

                            elif hasattr(response, 'error') and response.error:
                                error_details = response.error
                                if hasattr(response.error, 'message'):
                                    error_details = response.error.message
                                print(
                                    f"Quart Backend: Gemini Error in response: {error_details}")
                                try:
                                    await websocket.send(f"[ERROR_FROM_GEMINI]: {str(error_details)}")
                                except Exception as send_exc:
                                    print(
                                        f"Quart Backend: Error sending Gemini error to client WebSocket: {type(send_exc).__name__}: {send_exc}")
                                active_processing = False
                                break

                            # Removed the separate turn_complete log here as it's handled above with user speech sending.

                        if not active_processing:
                            break

                        if not had_gemini_activity_in_this_iteration and active_processing:
                            await asyncio.sleep(0.1)
                        elif had_gemini_activity_in_this_iteration and active_processing:
                            pass

                except ConnectionClosedOK:
                    print("INFO: Connection to client closed.")
                    active_processing = False
                finally:
                    # print("Quart Backend: Stopped receiving from Gemini.")
                    active_processing = False  # Ensure graceful shutdown of the other task

            forward_task = asyncio.create_task(
                handle_client_input_and_forward(), name="ClientInputForwarder")
            receive_task = asyncio.create_task(
                receive_from_gemini_and_forward_to_client(), name="GeminiReceiver")

            try:
                await asyncio.gather(forward_task, receive_task)
            except Exception as e_gather:
                print(
                    f"Quart Backend: Exception during asyncio.gather: {type(e_gather).__name__}: {e_gather}")
                traceback.print_exc()  # Added traceback
            finally:
                active_processing = False
                if not forward_task.done():
                    forward_task.cancel()
                if not receive_task.done():
                    receive_task.cancel()
                try:
                    await forward_task
                except asyncio.CancelledError:
                    # print(f"Quart Backend: Task {forward_task.get_name()} was cancelled during cleanup.")
                    pass  # Task cancellation is an expected part of shutdown
                except Exception as e_fwd_cleanup:
                    print(
                        f"Quart Backend: Error during forward_task cleanup: {e_fwd_cleanup}")
                    traceback.print_exc()  # Added traceback
                try:
                    await receive_task
                except asyncio.CancelledError:
                    # print(f"Quart Backend: Task {receive_task.get_name()} was cancelled during cleanup.")
                    pass  # Task cancellation is an expected part of shutdown
                except Exception as e_rcv_cleanup:
                    print(
                        f"Quart Backend: Error during receive_task cleanup: {e_rcv_cleanup}")
                    traceback.print_exc()  # Added traceback

            # print("Quart Backend: Gemini interaction tasks finished.")
    except asyncio.CancelledError:
        print("⚠️ WebSocket connection cancelled (client disconnected)")
        pass  # Expected on client disconnect
    except TimeoutError as e_timeout:
        print(f"⏰ Timeout connecting to Gemini Live API: {e_timeout}")
        print("🔍 This could be due to:")
        print("   - Network connectivity issues")
        print("   - API key problems")
        print("   - Google service unavailability")
        print("   - Firewall blocking WebSocket connections")
        traceback.print_exc()
    except Exception as e_ws_main:
        print(
            f"❌ UNHANDLED error in WebSocket connection: {type(e_ws_main).__name__}: {e_ws_main}")
        traceback.print_exc()
    finally:
        print("🔚 WebSocket endpoint processing finished")


@app.route("/api/logs", methods=["GET"])
async def get_logs():
    """API endpoint to fetch captured logs."""
    # Combine logs from BQ's global store and our captured stdout logs
    # Return copies to avoid issues if the lists are modified during serialization
    combined_logs = list(GLOBAL_LOG_STORE) + list(CAPTURED_STDOUT_LOGS)

    # Optional: Sort by timestamp if all logs have a compatible timestamp field
    # For now, just concatenating. Assuming GLOBAL_LOG_STORE entries also have a timestamp
    # or can be ordered meaningfully with the new TOOL_EVENT logs.
    # If sorting is needed:
    # combined_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True) # Example sort

    return jsonify(combined_logs)

# To run this Quart application:
# 1. Install dependencies: pip install quart quart-cors google-generativeai python-dotenv hypercorn
# 2. Set your GEMINI_API_KEY environment variable in a .env file or your system environment.
# 3. Run using Hypercorn:
#    hypercorn main:app --bind 0.0.0.0:8000
#    Or, for development with auto-reload:
#    quart run --host 0.0.0.0 --port 8000 --reload
