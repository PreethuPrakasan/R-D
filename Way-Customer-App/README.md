# Automotive AI Customer Service

A real-time voice AI assistant for automotive repair shops that handles customer calls, appointment booking, vehicle status checks, and service inquiries.

## Architecture

- **Node.js Server**: Handles Twilio-OpenAI realtime voice connection
- **Python FastAPI Backend**: Manages database operations and AI tools
- **PostgreSQL Database**: Stores customer, vehicle, appointment, and service data

## Features

- **Real-time Voice AI**: Powered by OpenAI's Realtime API with Twilio integration
- **Appointment Management**: Book, check, and cancel appointments
- **Vehicle Status**: Check vehicle service history and current status
- **Service Information**: Get details about available services and pricing
- **Customer Management**: Update customer information and preferences
- **Low Latency**: Optimized for fast response times with connection pooling

## Setup

### 1. Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Set up Python virtual environment and install dependencies
# Windows:
setup_python_env.bat

# Linux/Mac:
chmod +x setup_python_env.sh
./setup_python_env.sh
```

### 2. Database Setup

1. Make sure PostgreSQL is running on localhost:5432
2. Create a database named `automotive_ai`
3. Run the schema file:

```bash
psql -U postgres -d automotive_ai -f database_schema.sql
```

### 3. Environment Variables

Create a `.env` file in the root directory:

```env
OPENAI_API_KEY=your_openai_api_key_here
PYTHON_BACKEND_URL=http://localhost:8000
```

### 4. Run the Application

#### Option 1: Start both servers automatically

**Windows:**
```bash
start_servers.bat
```

**Linux/Mac:**
```bash
chmod +x start_servers.sh
./start_servers.sh
```

#### Option 2: Start servers manually

**Terminal 1 - Python Backend:**
```bash
# Windows:
venv\Scripts\activate.bat
python start_backend.py

# Linux/Mac:
source venv/bin/activate
python start_backend.py
```

**Terminal 2 - Node.js Server:**
```bash
npm run dev
```

The servers will start on:
- Python Backend: http://localhost:8000
- Node.js Server: http://localhost:5000

## Twilio Configuration

1. Set up a Twilio phone number
2. Configure the webhook URL to point to your server: `https://your-domain.com/incoming-call`
3. The system will automatically handle incoming calls and connect them to the AI assistant

## Usage Examples

Customers can call and ask questions like:

- "I'd like to book an oil change for my Toyota Camry"
- "What's the status of my vehicle?"
- "Do I have any upcoming appointments?"
- "What services do you offer and how much do they cost?"
- "I need to cancel my appointment"

## API Endpoints

- `GET /` - Health check
- `POST /incoming-call` - Twilio webhook for incoming calls
- `WebSocket /media-stream` - Real-time audio streaming

## Database Schema

The system uses the following main tables:
- `customers` - Customer information
- `vehicles` - Vehicle details linked to customers
- `services` - Available services and pricing
- `appointments` - Scheduled appointments

## Performance Optimization

- Database connection pooling for low latency
- Prepared statements for common queries
- Efficient indexing on frequently queried columns
- Real-time audio streaming with minimal buffering

## Error Handling

- Graceful fallbacks when database is unavailable
- User-friendly error messages
- Comprehensive logging for debugging
- Retry mechanisms for failed operations
