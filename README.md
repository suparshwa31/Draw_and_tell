# Draw_and_tell

An **interactive conversational sketch-and-tell system** designed especially for **kids aged 5–10 years**.  
Children draws based on the given prompt, the system recognizes it, asks a follow-up, and responds **with speech** — making drawing fun, educational, and interactive.  

## Features
- **Kid-Friendly Interaction**: Designed for children ages 5–10, combining drawing with storytelling.
- **Speech-Enabled Conversations**: System responds with natural TTS after recognizing drawings or speech.
- **AI-Powered Dialogue**: CV integration for generating playful and age-appropriate follow-up questions based on the image. 
- **Model Flexibility**: Switch between ASR, TTS, and CV backends via configuration.
- **Fallback & Recovery**: Graceful fallback to alternative models with kid-friendly retry prompts.

## Prerequisites

- Python 3.8+
- Tensorflow 2.14.0
- opencv
- ffmpeg

## Installation

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd draw-and-tell/backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Frontend Setup

## kids view

1. Navigate to the frontend directory:
   ```bash
   cd draw-and-tell/frontend/kid_app
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

## parents view

1. Navigate to the frontend directory:
   ```bash
   cd draw-and-tell/frontend/parent_dashboard
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

## Running the Application

### Backend

From the `draw-and-tell/backend` directory:

```bash
python3 main.py
```

The backend will start on `http://localhost:8000`

### Frontend

## kids view

From the `draw-and-tell/frontend/kids_app` directory:

```bash
npm run dev
```
The kids frontend will start on `http://localhost:5173`

## parents view

From the `draw-and-tell/frontend/parent_dashboard` directory:

```bash
npm run dev
```

The parents frontend will start on `http://localhost:5174`

### Usage

## kids loop

1. **Prompt page**: receive a drawing topic
2. **draw page**: upload the drawing
3. **followup page**: system analyzes drawing, asks a question, and waits for the answer
4. **Acknowledgement page**: system responds via audio

## parents loop
1. **dashboard**: view all drawings submitted by their children

## API Endpoints

- `GET /prompt` - generate prompt
- `POST /analyze-drawing` - Feed the drawing to an CV model for analysis and generate a question
- `POST /transcribe-answer` - convert kids audio answer to a text
- `GET /sessions` - Fetch all sessions for the parent
- `GET /session/{session_id}` - Fetch a specifc session for the parent
- `GET /recap/{session_id}` - Fetch the recap for a specific drawing
- `GET /image/{drawing_id}` - fetch the drawing image to show parents


## AI Usage

- **CV** - Salesforce/blip-image-captioning-base
- **ASR** - Openai/whisper-small
- **TTS** - sjdata/speecht5_finetuned_single_speaker_de_small_librivox


## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request
