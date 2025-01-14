const express = require('express');
const crypto = require('crypto');
const bodyParser = require('body-parser');
const axios = require('axios');
const dotenv = require('dotenv');
dotenv.config();

const app = express();
app.use(bodyParser.json());

const VERIFY_TOKEN = process.env.VERIFY_TOKEN;
const APP_SECRET = process.env.APP_SECRET;
const ACCESS_TOKEN = process.env.ACCESS_TOKEN;  
const IG_ID = process.env.IG_ID;
const FLASK_SERVER = 'http://localhost:3000';

class ConversationManager {
    async getConversationId(userId) {
        try {
            // Using correct v21.0 endpoint as per documentation
            const response = await axios.get(
                `https://graph.instagram.com/v21.0/me/conversations`,
                {
                    params: {
                        user_id: userId,
                        platform: 'instagram',
                        access_token: ACCESS_TOKEN
                    }
                }
            );
            
            if (!response.data.data.length) {
                console.log(`No conversation found for user ${userId}`);
                return null;
            }
            
            return response.data.data[0].id;
        } catch (error) {
            console.error('Error getting conversation ID:', error);
            throw error;
        }
    }

    async fetchMessages(conversationId) {
        try {
            // Using correct endpoint structure from documentation
            const response = await axios.get(
                `https://graph.instagram.com/v21.0/${conversationId}`,
                {
                    params: {
                        fields: 'messages{id,created_time,from,to,message}',
                        access_token: ACCESS_TOKEN
                    }
                }
            );
            
            // Extract messages from the nested structure
            return response.data.messages?.data || [];
        } catch (error) {
            console.error('Error fetching messages:', error);
            throw error;
        }
    }

    async getMessageDetails(messageId) {
        try {
            // Implementation of individual message fetching as per documentation
            const response = await axios.get(
                `https://graph.instagram.com/v21.0/${messageId}`,
                {
                    params: {
                        fields: 'id,created_time,from,to,message',
                        access_token: ACCESS_TOKEN
                    }
                }
            );
            return response.data;
        } catch (error) {
            console.error('Error fetching message details:', error);
            throw error;
        }
    }

    async syncConversation(userId) {
        try {
            console.log(`Syncing conversation for user ${userId}`);
            
            // Get local conversation history
            const localHistory = await this.getLocalHistory(userId);
            
            // Get Instagram conversation
            const conversationId = await this.getConversationId(userId);
            if (!conversationId) {
                console.log('No conversation found on Instagram');
                return [];
            }

            // Fetch messages with proper fields
            const messages = await this.fetchMessages(conversationId);
            console.log(`Fetched ${messages.length} messages from Instagram`);

            // Deduplicate messages based on message ID
            const existingIds = new Set(localHistory.map(msg => msg.id));
            const newMessages = messages.filter(msg => !existingIds.has(msg.id));

            // If there are new messages, store them
            if (newMessages.length > 0) {
                await this.storeConversation(userId, [...localHistory, ...newMessages]);
            }
            
            return messages;
        } catch (error) {
            console.error('Error syncing conversation:', error);
            throw error;
        }
    }

    async getLocalHistory(userId) {
        try {
            const response = await axios.get(`${FLASK_SERVER}/conversation_history/${userId}`);
            return response.data.history || [];
        } catch (error) {
            if (error.response && error.response.status === 404) {
                return [];
            }
            console.error('Error getting local history:', error);
            throw error;
        }
    }

    async storeConversation(userId, messages) {
        try {
            console.log(`Storing ${messages.length} messages for user ${userId}`);
            const response = await axios.post(
                `${FLASK_SERVER}/store_conversation`,
                {
                    username: userId,
                    history: messages
                }
            );
            console.log('Store response:', response.data);
            return response.data;
        } catch (error) {
            console.error('Error storing conversation:', error);
            throw error;
        }
    }
}

class MessageHandler {
    constructor() {
        this.conversationManager = new ConversationManager();
    }

    async handleMessage(senderID, messageText) {
        try {
            console.log(`Processing message from ${senderID}: ${messageText}`);

            // Sync conversation before processing
            await this.conversationManager.syncConversation(senderID);

            // Process message with Flask server
            const response = await this.processMessage(senderID, messageText);
            
            // Send response back to Instagram
            await this.sendResponse(senderID, response);

            // Sync again to capture the new message
            await this.conversationManager.syncConversation(senderID);

        } catch (error) {
            console.error('Error handling message:', error);
            throw error;
        }
    }

    async processMessage(senderID, messageText) {
        try {
            const response = await axios.post(
                `${FLASK_SERVER}/query`,
                {
                    username: senderID,
                    query: messageText
                }
            );
            return response.data.response;
        } catch (error) {
            console.error('Error processing message:', error);
            throw error;
        }
    }

    async sendResponse(senderID, message) {
        try {
            const response = await axios.post(
                'https://graph.instagram.com/v21.0/me/messages',
                {
                    recipient: { id: senderID },
                    message: { text: message }
                },
                {
                    params: {
                        access_token: ACCESS_TOKEN
                    },
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );
            console.log('Response sent successfully');
            return response.data;
        } catch (error) {
            console.error('Error sending response:', error);
            throw error;
        }
    }
}

// Initialize message handler
const messageHandler = new MessageHandler();

// Webhook verification endpoint
app.get('/webhooks', (req, res) => {
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];

    if (mode === 'subscribe' && token === VERIFY_TOKEN) {
        console.log('WEBHOOK_VERIFIED');
        return res.status(200).send(challenge);
    }
    
    return res.sendStatus(403);
});

// Webhook endpoint for receiving updates
app.post('/webhooks', (req, res) => {
    const signature = req.headers['x-hub-signature-256'];
    
    if (!verifySignature(req.body, signature)) {
        console.error('Invalid signature');
        return res.sendStatus(403);
    }

    console.log('Received webhook:', JSON.stringify(req.body, null, 2));

    if (req.body.object === 'instagram') {
        res.status(200).send('EVENT_RECEIVED');

        if (req.body.entry && req.body.entry.length > 0) {
            req.body.entry.forEach((entry) => {
                if (entry.messaging) {
                    entry.messaging.forEach((messagingEvent) => {
                        if (messagingEvent.message && 
                            messagingEvent.message.text && 
                            !messagingEvent.message.is_echo) {
                            messageHandler.handleMessage(
                                messagingEvent.sender.id,
                                messagingEvent.message.text
                            ).catch(console.error);
                        }
                    });
                }
            });
        }
    } else {
        res.sendStatus(404);
    }
});

function verifySignature(payload, signature) {
    if (!signature) return false;
    const sig = signature.split('sha256=')[1];
    const expectedSignature = crypto
        .createHmac('sha256', APP_SECRET)
        .update(JSON.stringify(payload))
        .digest('hex');
    return crypto.timingSafeEqual(
        Buffer.from(sig),
        Buffer.from(expectedSignature)
    );
}

const PORT = process.env.PORT || 69;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});