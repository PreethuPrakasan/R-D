import http from 'http';
import express from 'express';
import dotenv from 'dotenv';
import { twiml } from 'twilio';
import { WebSocketServer } from 'ws';
import { TwilioElevenLabsBridge } from './services/bridge';

dotenv.config();

const port = Number(process.env.PORT ?? 3000);
const twilioStreamPath = process.env.TWILIO_STREAM_PATH ?? '/twilio-media-stream';
const publicStreamUrl =
  process.env.TWILIO_STREAM_URL ??
  (process.env.PUBLIC_BASE_URL
    ? `${process.env.PUBLIC_BASE_URL.replace(/\/$/, '')
        .replace(/^http:/, 'ws:')
        .replace(/^https:/, 'wss:')}${twilioStreamPath}`
    : undefined);

if (!process.env.ELEVENLABS_API_KEY) {
  throw new Error('Missing ELEVENLABS_API_KEY env variable');
}

if (!process.env.ELEVENLABS_AGENT_ID) {
  throw new Error('Missing ELEVENLABS_AGENT_ID env variable');
}

if (!publicStreamUrl) {
  throw new Error('Missing TWILIO_STREAM_URL or PUBLIC_BASE_URL env variable (must resolve to wss://...)');
}

const app = express();
app.use(express.urlencoded({ extended: false }));
app.use(express.json());

// Basic health check.
app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

// Twilio voice webhook that returns TwiML to start the media stream.
app.post('/voice', (_req, res) => {
  const response = new twiml.VoiceResponse();
  response.connect().stream({
    url: publicStreamUrl,
    track: 'inbound_track',
  });

  res.type('text/xml');
  res.send(response.toString());
});

const server = http.createServer(app);

const bridge = new TwilioElevenLabsBridge({
  path: twilioStreamPath,
  elevenLabs: {
    apiKey: process.env.ELEVENLABS_API_KEY,
    agentId: process.env.ELEVENLABS_AGENT_ID,
    baseUrl: process.env.ELEVENLABS_REALTIME_URL ?? 'wss://api.elevenlabs.io/v1/convai/ws',
  },
});

const wss = new WebSocketServer({ server, path: twilioStreamPath });
bridge.attachToWebSocketServer(wss);

server.listen(port, () => {
  console.log(`Server listening on http://localhost:${port}`);
});

