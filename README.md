# SentienceX-AI

SentienceX-AI is an advanced AI-powered platform designed for sentiment analysis, threat detection, sarcasm detection, and conversational AI. It includes a backend for processing and a frontend for visualization and interaction.

---

## Features

### Backend
- **Sentiment Analysis**: Detects positive and negative sentiments in text.
- **Threat Detection**: Identifies potential threats based on keywords and context.
- **Sarcasm Detection**: Estimates sarcasm levels using predefined keywords.
- **Conversational AI**: Generates responses using GPT-2.
- **Audio Synthesis**: Converts AI-generated responses into audio.
- **Retraining**: Supports model retraining with configurable schedules.
- **Log Streaming**: Streams logs to RabbitMQ and provides a database-backed log history.
- **Secure Authentication**: Uses Azure Key Vault for secure token management.
- **Cross-Platform Compatibility**: Ensures timeout handling works on all operating systems.

### Frontend
- **Interactive Chat**: Allows users to send messages and receive AI-generated responses.
- **Sentiment Graph**: Visualizes sentiment and threat trends in real-time.
- **Error Handling**: Displays detailed error messages for better debugging.
- **Loading Feedback**: Provides visual indicators for loading states.
- **Built with Next.js**: Utilizes Next.js for server-side rendering and optimized performance.