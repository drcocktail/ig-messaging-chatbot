//server.js

const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');
const dotenv = require('dotenv');
dotenv.config();

const app = express();
app.use(bodyParser.json());

const VERIFY_TOKEN = process.env.VERIFY_TOKEN;
const APP_SECRET = process.env.APP_SECRET;
const ACCESS_TOKEN = process.env.ACCESS_TOKEN;
const FLASK_SERVER = 'http://localhost:3000';

async function handleMessage(senderId, messageText, payload = null) {
    try {
        // Send to model
        const modelResponse = await axios.post(`${FLASK_SERVER}/query`, {
            username: senderId,
            query: payload || messageText,
            conversation_history: [] // Add conversation history if available
        });

        // Send response back to Instagram
        if (modelResponse.data.buttons) {
            // Send button template
            await axios.post(
                `https://graph.instagram.com/v22.0/${senderId}/messages`,
                {
                    recipient: { id: senderId },
                    message: {
                        attachment: {
                            type: "template",
                            payload: {
                                template_type: "button",
                                text: messageText,
                                buttons: modelResponse.data.buttons
                            }
                        }
                    }
                },
                {
                    params: { access_token: ACCESS_TOKEN },
                    headers: { 'Content-Type': 'application/json' }
                }
            );
        } else {
            // Send text reply
            await axios.post(
                `https://graph.instagram.com/v22.0/${senderId}/messages`,
                {
                    recipient: { id: senderId },
                    message: { text: modelResponse.data.text }
                },
                {
                    params: { access_token: ACCESS_TOKEN },
                    headers: { 'Content-Type': 'application/json' }
                }
            );
        }

        console.log(`Sent response to ${username}: ${modelResponse.data.text || "Button Template"}`);
    } catch (error) {
        console.error('Error handling message:', error);
        throw error;
    }
}

// Webhook verification
app.get('/webhooks', (req, res) => {
    if (req.query['hub.mode'] === 'subscribe' && 
        req.query['hub.verify_token'] === VERIFY_TOKEN) {
        return res.status(200).send(req.query['hub.challenge']);
    }
    return res.sendStatus(403);
});

// Webhook handler
app.post('/webhooks', (req, res) => {
    const signature = req.headers['x-hub-signature-256'];
    if (!signature) return res.sendStatus(403);

    // Verify signature (omitted for brevity)

    // Handle webhook
    if (req.body.object === 'instagram') {
        res.status(200).send('EVENT_RECEIVED');

        const entry = req.body.entry?.[0];
        const messagingEvent = entry?.messaging?.[0];

        if (messagingEvent?.message?.text && !messagingEvent.message.is_echo) {
            handleMessage(
                messagingEvent.sender.id,
                messagingEvent.message.text
            ).catch(console.error);
        } else if (messagingEvent?.postback) {
            // Handle button press
            handleMessage(
                messagingEvent.sender.id,
                null,
                messagingEvent.postback.payload
            ).catch(console.error);
        }
    } else {
        res.sendStatus(404);
    }
});

const PORT = process.env.PORT || 69;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));