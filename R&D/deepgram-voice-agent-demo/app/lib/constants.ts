import { type AudioConfig, type StsConfig, type Voice } from "app/utils/deepgramUtils";

const audioConfig: AudioConfig = {
  input: {
    encoding: "linear16",
    sample_rate: 16000,
  },
  output: {
    encoding: "linear16",
    sample_rate: 24000,
    container: "none",
  },
};

// LLM Provider Options (cheaper alternatives to OpenAI)
// You can switch providers via URL params: ?think_provider=groq&think_model=llama-3.1-70b-versatile
export const LLM_PROVIDERS = {
  // Cheapest & Fastest Option
  GROQ: {
    type: "groq" as const,
    models: [
      "llama-3.1-70b-versatile", // Best quality
      "mixtral-8x7b-32768", // Fast, cheaper
      "gemma2-9b-it", // Fastest, cheapest
    ],
    defaultModel: "llama-3.1-70b-versatile",
  },
  // High Quality Alternative
  ANTHROPIC: {
    type: "anthropic" as const,
    models: [
      "claude-sonnet-3.5", // Best quality
      "claude-haiku-3", // Cheaper, still good
    ],
    defaultModel: "claude-haiku-3",
  },
  // Good Balance
  GOOGLE: {
    type: "google" as const,
    models: [
      "gemini-pro", // Better quality
      "gemini-flash", // Cheaper, faster
    ],
    defaultModel: "gemini-flash",
  },
  // Cheapest (Open Source)
  TOGETHER: {
    type: "together" as const,
    models: [
      "meta-llama/Llama-3-70b-chat-hf",
      "mistralai/Mixtral-8x7B-Instruct-v0.1",
    ],
    defaultModel: "meta-llama/Llama-3-70b-chat-hf",
  },
  // European/GDPR Compliant
  MISTRAL: {
    type: "mistral" as const,
    models: [
      "mistral-large-latest", // Best quality
      "mistral-medium-latest", // Good balance
      "pixtral-12b", // Multimodal
      "mistral-small-latest", // Fastest, cheapest
    ],
    defaultModel: "mistral-large-latest",
  },
  // Enterprise-focused, Great for Conversations
  COHERE: {
    type: "cohere" as const,
    models: [
      "command-r-plus", // Best for conversations
      "command-r", // Good balance
      "command", // Faster, cheaper
      "command-light", // Fastest, cheapest
    ],
    defaultModel: "command-r-plus",
  },
  // Real-time Search & Answers
  PERPLEXITY: {
    type: "perplexity" as const,
    models: [
      "sonar", // Best for real-time
      "sonar-pro", // Enhanced version
      "sonar-online", // With web search
    ],
    defaultModel: "sonar",
  },
  // Original (Expensive)
  OPENAI: {
    type: "open_ai" as const,
    models: [
      "gpt-4o", // Most expensive
      "gpt-4-turbo",
      "gpt-3.5-turbo", // Cheaper OpenAI option
    ],
    defaultModel: "gpt-4o",
  },
} as const;

// Default provider - Change this to switch default provider
// NOTE: Verify Deepgram supports your chosen provider before changing default
// You can always use URL params: ?think_provider=groq&think_model=llama-3.1-70b-versatile
const DEFAULT_LLM_PROVIDER = LLM_PROVIDERS.OPENAI; // Keep OpenAI as default until verified
const DEFAULT_LLM_MODEL = DEFAULT_LLM_PROVIDER.defaultModel;

const baseConfig = {
  type: "Settings" as const,
  audio: audioConfig,
  agent: {
    listen: { provider: { type: "deepgram" as const, model: "nova-3" } },
    speak: { provider: { type: "deepgram" as const, model: "aura-asteria-en" } },
    think: {
      // Default to Groq for cost savings - can be overridden via URL params
      provider: { 
        type: DEFAULT_LLM_PROVIDER.type, 
        model: DEFAULT_LLM_MODEL 
      },
    },
  },
  experimental: true,
};

export const stsConfig: StsConfig = {
  ...baseConfig,
  agent: {
    ...baseConfig.agent,
    think: {
      ...baseConfig.agent.think,
      prompt: `
                ## Base instructions
                You are a helpful voice assistant made by Deepgram's engineers.
                Respond in a friendly, human, conversational manner.
                YOU MUST answer in 1-2 sentences at most when the message is not empty.
                Always reply to empty messages with an empty message.
                Ask follow up questions.
                Ask one question at a time.
                Your messages should have no more than than 120 characters.
                Do not use abbreviations for units.
                Separate all items in a list with commas.
                Keep responses unique and free of repetition.
                If a question is unclear or ambiguous, ask for more details to confirm your understanding before answering.
                If someone asks how you are, or how you are feeling, tell them.
                Deepgram gave you a mouth and ears so you can take voice as an input. You can listen and speak.
                Your name is Voicebot.
                `,
      functions: [],
    },
  },
};

// Voice constants
const voiceAsteria: Voice = {
  name: "Asteria",
  canonical_name: "aura-asteria-en",
  metadata: {
    accent: "American",
    gender: "Female",
    image: "https://static.deepgram.com/examples/avatars/asteria.jpg",
    color: "#7800ED",
    sample: "https://static.deepgram.com/examples/voices/asteria.wav",
  },
};

const voiceOrion: Voice = {
  name: "Orion",
  canonical_name: "aura-orion-en",
  metadata: {
    accent: "American",
    gender: "Male",
    image: "https://static.deepgram.com/examples/avatars/orion.jpg",
    color: "#83C4FB",
    sample: "https://static.deepgram.com/examples/voices/orion.mp3",
  },
};

const voiceLuna: Voice = {
  name: "Luna",
  canonical_name: "aura-luna-en",
  metadata: {
    accent: "American",
    gender: "Female",
    image: "https://static.deepgram.com/examples/avatars/luna.jpg",
    color: "#949498",
    sample: "https://static.deepgram.com/examples/voices/luna.wav",
  },
};

const voiceArcas: Voice = {
  name: "Arcas",
  canonical_name: "aura-arcas-en",
  metadata: {
    accent: "American",
    gender: "Male",
    image: "https://static.deepgram.com/examples/avatars/arcas.jpg",
    color: "#DD0070",
    sample: "https://static.deepgram.com/examples/voices/arcas.mp3",
  },
};

type NonEmptyArray<T> = [T, ...T[]];
export const availableVoices: NonEmptyArray<Voice> = [
  voiceAsteria,
  voiceOrion,
  voiceLuna,
  voiceArcas,
];
export const defaultVoice: Voice = availableVoices[0];

export const sharedOpenGraphMetadata = {
  title: "Voice Agent | Deepgram",
  type: "website",
  url: "/",
  description: "Meet Deepgram's Voice Agent API",
};

export const latencyMeasurementQueryParam = "latency-measurement";
