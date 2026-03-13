## ElevenLabs Realtime Voice Agent POC

This proof-of-concept bridges a Twilio Programmable Voice call with an ElevenLabs realtime conversational agent. When a caller dials your Twilio number the call audio is streamed over WebRTC-style media streams into the ElevenLabs agent, and the synthesized response is returned to the caller in near real time.

### Architecture

- Twilio receives an inbound PSTN call and executes a voice webhook that returns `<Connect><Stream>` TwiML to start a bidirectional media stream. ([Twilio docs](https://www.twilio.com/docs/voice/twiml/stream))
- A Node.js or Python bridge server (both included in this repo) terminates the Twilio media WebSocket and forwards audio frames to the ElevenLabs realtime agent client.
- The ElevenLabs agent processes the caller's utterances, invokes tools if needed, and streams synthesized speech back. See the platform overview for capabilities and workflow design options [in the ElevenLabs docs](https://elevenlabs.io/docs/agents-platform/overview) and the roadmap improvements outlined in [Conversational AI 2.0](https://elevenlabs.io/blog/conversational-ai-2-0).
- The returned audio is encoded back into µ-law format and pushed into the Twilio stream so the caller can hear the agent's response.

The ElevenLabs realtime agent is configured in your ElevenLabs workspace. The sample server expects you to provide the agent identifier and API key via environment variables. You can attach knowledge bases, tools, and personalization through the dashboard or API before testing, as described in the [Agents platform guide](https://elevenlabs.io/docs/overview).

### Prerequisites

- Node.js 18+
- Twilio account with a programmable voice number
- ElevenLabs account with access to the Agents platform and a configured realtime agent
- A public `https://` and `wss://` tunnel (for example Ngrok) so Twilio can reach your local machine

If your local path contains special characters such as `&` you may need to escape them when running npm scripts on Windows. One workaround is to open the project through a junction or symlink without the special character.

### Configuration

1. Copy `poc/server/env.sample` to `poc/server/.env` and populate it.

   ```
   PORT=3000
   PUBLIC_BASE_URL=https://<your-ngrok-domain>.ngrok.app
   TWILIO_STREAM_URL=wss://<your-ngrok-domain>.ngrok.app/twilio-media-stream
   TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ELEVENLABS_AGENT_ID=your_agent_id
   ELEVENLABS_REALTIME_URL=wss://api.elevenlabs.io/v1/convai/ws
   ```

2. Expose your local server:

   ```
   ngrok http 3000
   ngrok http 3000 --host-header="localhost:3000"
   ngrok http 3000 --domain=<custom_domain>
   ```

   Ensure you also create a WebSocket tunnel (`wss://`) that maps to the `/twilio-media-stream` endpoint.

3. Configure a Twilio voice webhook for your phone number to point at `https://<your-ngrok-domain>.ngrok.app/voice`.

4. In the ElevenLabs dashboard confirm your realtime agent is enabled for low-latency audio streaming and note the agent ID.

### Node.js Installation and Usage

```bash
cd poc/server
npm install
npm run dev
```

> **Windows tip:** if npm scripts fail because of `&` in the path, run the script from a junction without special characters or invoke `cmd /c` with the escaped path.

With the dev server running:

1. Call your Twilio number.
2. Twilio connects the call audio to `wss://<domain>/twilio-media-stream`.
3. The server streams audio frames to ElevenLabs and relays the synthesized responses to the caller.

Check the logs for call identifiers and bridge lifecycle events. You can extend the project by:

- Adding session logging and analytics (see [Conversation Analysis](https://elevenlabs.io/docs/agents-platform/customization/agent-analysis)).
- Enabling ElevenLabs tools or knowledge bases to ground the agent responses.
- Implementing authentication to protect the webhook, following the [Agents platform authentication guidance](https://elevenlabs.io/docs/agents-platform/customization/authentication).

### Python Installation and Usage

```bash
cd poc/python-server
python -m venv .venv
.venv\\Scripts\\activate            # Windows
# source .venv/bin/activate         # macOS / Linux
pip install -r requirements.txt
python -m app.main
```

The FastAPI server exposes the same `/voice` webhook and `/twilio-media-stream` WebSocket endpoint. Use `uvicorn` command line if you prefer hot reload:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

### Project Structure

```
poc/
  README.md              # You are here
  server/
    env.sample
    package.json
    src/
      index.ts           # Express server and Twilio webhook
      services/
        bridge.ts        # Twilio ↔ ElevenLabs audio bridge
        elevenlabs.ts    # Realtime ElevenLabs WebSocket client
      utils/
        audio.ts         # μ-law ↔ PCM converters
  python-server/
    requirements.txt
    app/
      main.py            # FastAPI app and Twilio webhook
      config.py          # Environment handling
      services/
        bridge.py        # Twilio ↔ ElevenLabs audio bridge
        elevenlabs.py    # Realtime ElevenLabs WebSocket client
      utils/
        audio.py         # μ-law ↔ PCM converters
```

### Next Steps

- Add persistence for conversation transcripts using ElevenLabs’ events API.
- Integrate automated testing using the [Agents testing toolkit](https://elevenlabs.io/docs/agents-platform/customization/agent-testing).
- Deploy the Node server to a cloud environment and provision HTTPS/WSS certificates.

