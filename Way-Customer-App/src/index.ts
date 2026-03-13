import Fastify from "fastify"
import WebSocket from "ws"
import dotenv from "dotenv"
import fastifyFormBody from "@fastify/formbody"
import fastifyWs from "@fastify/websocket"
import axios from "axios"

dotenv.config();

const { OPENAI_API_KEY, PYTHON_BACKEND_URL = 'http://localhost:8000' } = process.env

if (!OPENAI_API_KEY) {
    console.error('Missing OpenAI API key. Please set it in the .env file.');
    process.exit(1);
}

const fastify = Fastify();
fastify.register(fastifyFormBody);
fastify.register(fastifyWs);

// Constants
const SYSTEM_MESSAGE = `You are a helpful customer service assistant for an automotive repair shop. 
You help customers with appointments, service status, pricing, and vehicle history. 
Be friendly, knowledgeable, and professional. 

IMPORTANT: You MUST use the available tools when customers ask about:
- Vehicle status or service history (use check_vehicle_status)
- Booking appointments (use book_appointment)
- Viewing appointments (use check_appointments)
- Cancelling appointments (use cancel_appointment)
- Service information and pricing (use get_service_info)
- Updating customer information (use update_customer_info)

When a customer asks to book an appointment, you MUST call the book_appointment tool with their phone number, service name, preferred date, and vehicle information. Do not ask for information you already have - use the tools to get or create the information you need.

Be conversational and helpful, but always use the tools for automotive-related requests.`;

const VOICE = 'alloy';

// AI Tools definition for OpenAI
const AI_TOOLS = [
    {
        name: 'check_vehicle_status',
        description: 'Check the status and service history of a customer\'s vehicle',
        parameters: {
            type: 'object',
            properties: {
                customer_phone: {
                    type: 'string',
                    description: 'Customer\'s phone number'
                }
            },
            required: ['customer_phone']
        }
    },
    {
        name: 'book_appointment',
        description: 'Book a new appointment for vehicle service',
        parameters: {
            type: 'object',
            properties: {
                customer_phone: {
                    type: 'string',
                    description: 'Customer\'s phone number'
                },
                service_name: {
                    type: 'string',
                    description: 'Name of the service requested (e.g., oil change, brake inspection)'
                },
                preferred_date: {
                    type: 'string',
                    description: 'Preferred appointment date in YYYY-MM-DD format'
                },
                preferred_time: {
                    type: 'string',
                    description: 'Preferred time in HH:MM format (24-hour)'
                },
                vehicle_info: {
                    type: 'string',
                    description: 'Vehicle make, model, and year'
                },
                notes: {
                    type: 'string',
                    description: 'Additional notes or special requests'
                }
            },
            required: ['customer_phone', 'service_name', 'preferred_date', 'vehicle_info']
        }
    },
    {
        name: 'check_appointments',
        description: 'Check existing appointments for a customer',
        parameters: {
            type: 'object',
            properties: {
                customer_phone: {
                    type: 'string',
                    description: 'Customer\'s phone number'
                }
            },
            required: ['customer_phone']
        }
    },
    {
        name: 'cancel_appointment',
        description: 'Cancel an existing appointment',
        parameters: {
            type: 'object',
            properties: {
                customer_phone: {
                    type: 'string',
                    description: 'Customer\'s phone number'
                },
                appointment_id: {
                    type: 'string',
                    description: 'ID of the appointment to cancel'
                }
            },
            required: ['customer_phone', 'appointment_id']
        }
    },
    {
        name: 'get_service_info',
        description: 'Get information about available services and pricing',
        parameters: {
            type: 'object',
            properties: {
                service_name: {
                    type: 'string',
                    description: 'Name of the service to get information about (optional - if not provided, returns all services)'
                }
            },
            required: []
        }
    },
    {
        name: 'update_customer_info',
        description: 'Update customer contact information',
        parameters: {
            type: 'object',
            properties: {
                customer_phone: {
                    type: 'string',
                    description: 'Customer\'s current phone number'
                },
                name: {
                    type: 'string',
                    description: 'Customer\'s name'
                },
                email: {
                    type: 'string',
                    description: 'Customer\'s email address'
                }
            },
            required: ['customer_phone']
        }
    }
];
const PORT = 5000;
const LOG_EVENT_TYPES = [
    'response.content.done',
    'rate_limits.updated',
    'response.done',
    'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started',
    'session.created'
];

// Function to call Python backend
async function callPythonBackend(toolName: string, parameters: any): Promise<string> {
    try {
        console.log(`Calling Python backend for tool: ${toolName}`, parameters);
        
        const response = await axios.post(`${PYTHON_BACKEND_URL}/ai-tools/execute`, {
            tool_name: toolName,
            parameters: parameters
        }, {
            timeout: 10000, // 10 second timeout
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.data.success) {
            return response.data.message;
        } else {
            return response.data.message || 'Sorry, I encountered an error processing your request.';
        }
    } catch (error) {
        console.error('Error calling Python backend:', error);
        return 'Sorry, I encountered an error processing your request. Please try again.';
    }
}

// Root Route
fastify.get('/', async (request, reply) => {
    reply.send({ message: 'Twilio Media Stream Server is running!' });
});

// Route for Twilio to handle incoming and outgoing calls
// <Say> punctuation to improve text-to-speech translation
fastify.all('/incoming-call', async (request, reply) => {
    const twimlResponse = `<?xml version="1.0" encoding="UTF-8"?>
                          <Response>
                              <Connect>
                                  <Stream url="wss://${request.headers.host}/media-stream" />
                              </Connect>
                          </Response>`;
    reply.type('text/xml').send(twimlResponse);
});

// WebSocket route for media-stream
fastify.register(async (fastify) => {
    fastify.get('/media-stream', { websocket: true }, (connection, req) => {
        console.log('Client connected');
        const openAiWs = new WebSocket('wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01', {
            headers: {
                Authorization: `Bearer ${OPENAI_API_KEY}`,
                "OpenAI-Beta": "realtime=v1"
            }
        });
        let streamSid: string | null = null;
        const sendSessionUpdate = () => {
            const sessionUpdate = {
                type: 'session.update',
                session: {
                    turn_detection: { type: 'server_vad' },
                    input_audio_format: 'g711_ulaw',
                    output_audio_format: 'g711_ulaw',
                    voice: VOICE,
                    instructions: SYSTEM_MESSAGE,
                    modalities: ["text", "audio"],
                    temperature: 0.8,
                    tools: AI_TOOLS.map(tool => ({
                        type: 'function',
                        name: tool.name,
                        description: tool.description,
                        parameters: tool.parameters
                    }))
                }
            };
            console.log('Sending session update:', JSON.stringify(sessionUpdate));
            openAiWs.send(JSON.stringify(sessionUpdate));
        };
        // Open event for OpenAI WebSocket
        openAiWs.on('open', () => {
            console.log('Connected to the OpenAI Realtime API');
            setTimeout(sendSessionUpdate, 250); // Ensure connection stability, send after .25 seconds
        });
        // Listen for messages from the OpenAI WebSocket (and send to Twilio if necessary)
        openAiWs.on('message', async (data: any) => {
            try {
                const response = JSON.parse(data);
                if (LOG_EVENT_TYPES.includes(response.type)) {
                    console.log(`Received event: ${response.type}`, response);
                }
                
                // Log all response types for debugging
                if (response.type && !LOG_EVENT_TYPES.includes(response.type)) {
                    console.log(`Received other event: ${response.type}`);
                }
                if (response.type === 'session.updated') {
                    console.log('Session updated successfully:', response);
                }
                if (response.type === 'response.audio.delta' && response.delta) {
                    const audioDelta = {
                        event: 'media',
                        streamSid: streamSid,
                        media: { payload: Buffer.from(response.delta, 'base64').toString('base64') }
                    };
                    connection.send(JSON.stringify(audioDelta));
                }
                // Handle function calls
                if (response.type === 'conversation.item.input_audio_transcript.completed') {
                    console.log('Audio transcript completed:', response);
                }
                if (response.type === 'response.function_call') {
                    console.log('Function call received:', JSON.stringify(response, null, 2));
                    const toolName = response.function_call.name;
                    const toolArgs = JSON.parse(response.function_call.arguments);
                    
                    try {
                        console.log(`Executing tool: ${toolName} with args:`, toolArgs);
                        const result = await callPythonBackend(toolName, toolArgs);
                        const toolResponse = {
                            type: 'response.function_call_result',
                            function_call_id: response.function_call.id,
                            result: result
                        };
                        console.log('Sending tool result:', toolResponse);
                        openAiWs.send(JSON.stringify(toolResponse));
                    } catch (error) {
                        console.error('Error executing tool:', error);
                        const errorResponse = {
                            type: 'response.function_call_result',
                            function_call_id: response.function_call.id,
                            result: 'Sorry, I encountered an error processing your request. Please try again.'
                        };
                        openAiWs.send(JSON.stringify(errorResponse));
                    }
                }
            } catch (error) {
                console.error('Error processing OpenAI message:', error, 'Raw message:', data);
            }
        });
        // Handle incoming messages from Twilio
        connection.on('message', (message: any) => {
            try {
                const data = JSON.parse(message);
                switch (data.event) {
                    case 'media':
                        if (openAiWs.readyState === WebSocket.OPEN) {
                            const audioAppend = {
                                type: 'input_audio_buffer.append',
                                audio: data.media.payload
                            };
                            openAiWs.send(JSON.stringify(audioAppend));
                        }
                        break;
                    case 'start':
                        streamSid = data.start.streamSid;
                        console.log('Incoming stream has started', streamSid);
                        break;
                    default:
                        console.log('Received non-media event:', data.event);
                        break;
                }
            } catch (error) {
                console.error('Error parsing message:', error, 'Message:', message);
            }
        });
        // Handle connection close
        connection.on('close', () => {
            if (openAiWs.readyState === WebSocket.OPEN) openAiWs.close();
            console.log('Client disconnected.');
        });
        // Handle WebSocket close and errors
        openAiWs.on('close', () => {
            console.log('Disconnected from the OpenAI Realtime API');
        });
        openAiWs.on('error', (error: any) => {
            console.error('Error in the OpenAI WebSocket:', error);
        });
    });
});

fastify.listen({ port: PORT }, (err) => {
    if (err) {
        console.error(err);
        process.exit(1);
    }
    console.log(`Server is listening on port ${PORT}`);
});
