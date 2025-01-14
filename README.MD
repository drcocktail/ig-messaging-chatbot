# Instagram Chatbot Manager

A simple GUI application to manage an Instagram chatbot powered by LLaMA. This application provides an easy-to-use interface for configuring and managing your Instagram chatbot with automatic server management and real-time logging.

## Features

- Modern, user-friendly GUI interface
- Automatic model setup and management
- Integrated server control for Flask, Node.js, and ngrok
- Real-time log output
- Easy configuration management
- Automatic dependency handling

## Prerequisites

- Python 3.11.5 or higher
- Node.js and npm
- ngrok account (free tier is sufficient)
- instagram business account 

## Setup Instructions


### 1. ngrok Setup

1. Create a free account at [ngrok.com](https://ngrok.com)
2. Copy your authtoken from your ngrok dashboard
3. Note down your ngrok static domain URL (available in free tier)

### 2. Instagram App Setup

1. Go to [Meta for Developers](https://developers.facebook.com)
2. Create a new app
3. Add the Instagram Product to your app
4. Note down the following credentials:
   - App Secret
   - Access Token
   - Instagram Business Account ID
   - Verify Token (create your own)
5. In the webhooks, add the callback url as your {ngrok-free-url}/webhooks
6. In the VERIFY TOKEN, just write hello


### 3. Running the Application

1. Clone this repository
2. Run the GUI application:
   ```bash
   python chat.py
   ```

3. In the GUI:
   - Enter your ngrok credentials in the "Ngrok Configuration" section
   - Click "Configure Ngrok Token"
   - Enter your Instagram app credentials in the "Instagram API Configuration" section
   - Click "Save Configuration"
   - Click "Start Servers" to launch the chatbot

The application will automatically:
- Install and configure LLaMA
- Start all required servers
- Set up webhooks
- Begin processing messages

## Stopping the Application

Simply click the "Stop Servers" button or close the GUI window. The application will properly terminate all running servers and processes.

## Troubleshooting

If you encounter any issues:
1. Check the log output window in the GUI
2. Ensure all credentials are entered correctly
3. Verify your Instagram app is properly configured
4. Check your internet connection

## Note

The chatbot uses the LLaMA model for message processing. The first startup might take a few minutes as it downloads and sets up the model automatically.

## License

MIT License - Feel free to modify and distribute as needed.