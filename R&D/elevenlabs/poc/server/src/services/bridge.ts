import { IncomingMessage } from 'http';
import EventEmitter from 'events';
import WebSocket, { WebSocketServer } from 'ws';
import { ElevenLabsRealtimeClient, ElevenLabsRealtimeConfig } from './elevenlabs';
import { decodeMuLawBase64ToPcm16, encodePcm16ToMuLawBase64 } from '../utils/audio';

interface TwilioStreamStartPayload {
  event: 'start';
  streamSid: string;
  start: {
    accountSid: string;
    callSid: string;
    tracks: string[];
  };
}

interface TwilioStreamMediaPayload {
  event: 'media';
  streamSid: string;
  media: {
    track: string;
    payload: string;
  };
}

interface TwilioStreamStopPayload {
  event: 'stop';
  streamSid: string;
}

type TwilioStreamMessage = TwilioStreamStartPayload | TwilioStreamMediaPayload | TwilioStreamStopPayload;

interface BridgeOptions {
  path: string;
  elevenLabs: ElevenLabsRealtimeConfig;
}

export class TwilioElevenLabsBridge {
  private readonly options: BridgeOptions;

  constructor(options: BridgeOptions) {
    this.options = options;
  }

  attachToWebSocketServer(server: WebSocketServer): void {
    server.on('connection', (socket: WebSocket, request: IncomingMessage) => {
      const session = new StreamBridgeSession(socket, this.options.elevenLabs);

      session.once('closed', () => {
        socket.close();
      });
    });
  }
}

class StreamBridgeSession extends EventEmitter {
  private readonly twilioSocket: WebSocket;
  private readonly elevenLabsClient: ElevenLabsRealtimeClient;
  private isReady = false;

  constructor(twilioSocket: WebSocket, config: ElevenLabsRealtimeConfig) {
    super();
    this.twilioSocket = twilioSocket;
    this.elevenLabsClient = new ElevenLabsRealtimeClient(config);

    this.twilioSocket.on('message', (data) => this.handleTwilioMessage(data));
    this.twilioSocket.on('close', () => {
      this.elevenLabsClient.disconnect();
      this.emit('closed');
    });

    this.twilioSocket.on('error', (err) => {
      console.error('[Twilio stream error]', err);
      this.elevenLabsClient.disconnect();
      this.emit('closed');
    });

    this.elevenLabsClient.on('audio', (chunk) => {
      if (this.twilioSocket.readyState === WebSocket.OPEN) {
        if (!this.streamSid) {
          return;
        }
        const payload = encodePcm16ToMuLawBase64(chunk);
        const response = {
          event: 'media',
          streamSid: this.streamSid,
          media: {
            payload,
          },
        };
        this.twilioSocket.send(JSON.stringify(response));
      }
    });
  }

  private streamSid?: string;

  private async handleTwilioMessage(data: WebSocket.RawData): Promise<void> {
    try {
      const json = typeof data === 'string' ? data : data.toString('utf8');
      const message = JSON.parse(json) as TwilioStreamMessage;

      switch (message.event) {
        case 'start':
          await this.handleStart(message);
          break;
        case 'media':
          await this.handleMedia(message);
          break;
        case 'stop':
          this.handleStop();
          break;
        default:
          console.warn('[Twilio stream] Unhandled event', message);
      }
    } catch (err) {
      console.error('Failed to parse Twilio stream payload', err);
    }
  }

  private async handleStart(message: TwilioStreamStartPayload): Promise<void> {
    this.streamSid = message.streamSid;
    await this.elevenLabsClient.connect();
    this.isReady = true;
  }

  private async handleMedia(message: TwilioStreamMediaPayload): Promise<void> {
    if (!this.isReady || message.media.payload.length === 0) {
      return;
    }

    try {
      const pcm = decodeMuLawBase64ToPcm16(message.media.payload);
      this.elevenLabsClient.sendAudio(pcm);
    } catch (err) {
      console.error('Failed to forward media frame', err);
    }
  }

  private handleStop(): void {
    this.elevenLabsClient.disconnect();
    this.emit('closed');
  }
}

