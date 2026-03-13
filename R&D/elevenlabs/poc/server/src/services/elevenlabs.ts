import EventEmitter from 'events';
import WebSocket from 'ws';

export interface ElevenLabsRealtimeConfig {
  apiKey: string;
  agentId: string;
  baseUrl?: string;
}

export interface ElevenLabsRealtimeEvents {
  connected: () => void;
  closed: (code: number, reason: Buffer) => void;
  error: (err: Error) => void;
  audio: (chunk: Buffer) => void;
  message: (payload: unknown) => void;
}

type EventKeys = keyof ElevenLabsRealtimeEvents;

export class ElevenLabsRealtimeClient extends EventEmitter {
  private ws?: WebSocket;
  private readonly config: Required<ElevenLabsRealtimeConfig>;

  constructor(config: ElevenLabsRealtimeConfig) {
    super();
    this.config = {
      baseUrl: config.baseUrl ?? 'wss://api.elevenlabs.io/v1/convai/ws',
      apiKey: config.apiKey,
      agentId: config.agentId,
    };
  }

  async connect(): Promise<void> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return;
    }

    await new Promise<void>((resolve, reject) => {
      const ws = new WebSocket(this.config.baseUrl, {
        headers: {
          'xi-api-key': this.config.apiKey,
          'x-agent-id': this.config.agentId,
        },
      });

      ws.once('open', () => {
        this.ws = ws;
        this.emit('connected');
        resolve();
      });

      ws.once('error', (err) => {
        this.emit('error', err as Error);
        reject(err);
      });

      ws.on('message', (data: WebSocket.RawData) => {
        if (typeof data === 'string') {
          try {
            const payload = JSON.parse(data);
            this.emit('message', payload);
          } catch (err) {
            this.emit('error', err as Error);
          }
        } else {
          this.emit('audio', Buffer.from(data));
        }
      });

      ws.on('close', (code, reason) => {
        this.emit('closed', code, reason);
        this.ws = undefined;
      });
    });

    await this.initializeSession();
  }

  private async initializeSession(): Promise<void> {
    const payload = {
      type: 'session.update',
      session: {
        agent_id: this.config.agentId,
        modalities: ['text', 'audio'],
      },
    };
    this.sendJson(payload);
  }

  sendJson(payload: unknown): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('ElevenLabs websocket is not connected');
    }
    this.ws.send(JSON.stringify(payload));
  }

  sendAudio(chunk: Buffer): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('ElevenLabs websocket is not connected');
    }
    this.ws.send(chunk);
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = undefined;
    }
  }

  override on<T extends EventKeys>(event: T, listener: ElevenLabsRealtimeEvents[T]): this {
    return super.on(event, listener);
  }

  override once<T extends EventKeys>(event: T, listener: ElevenLabsRealtimeEvents[T]): this {
    return super.once(event, listener);
  }
}



