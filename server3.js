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
const FLASK_SERVER = 'http://localhost:3000';

async function getConversationHistory(userId) {
    try {
        // Get conversation ID
        const convResponse = await axios.get(
            'https://graph.instagram.com/v21.0/me/conversations',
            {
                params: {
                    user_id: userId,
                    platform: 'instagram',
                    access_token: ACCESS_TOKEN
                }
            }
        );
        
        if (!convResponse.data.data.length) {
            return [];
        }
        
        // Get messages from conversation
        const conversationId = convResponse.data.data[0].id;
        const msgResponse = await axios.get(
            `https://graph.instagram.com/v21.0/${conversationId}`,
            {
                params: {
                    fields: 'messages{id,created_time,from,to,message}',
                    access_token: ACCESS_TOKEN
                }
            }
        );
        
        return msgResponse.data.messages?.data || [];
    } catch (error) {
        console.error('Error fetching conversation history:', error);
        throw error;
    }
}

async function handleMessage(senderId, messageText) {
    try {
        // Get conversation history
        const history = await getConversationHistory(senderId);
        
        // Send to model
        const modelResponse = await axios.post(`${FLASK_SERVER}/query`, {
            username: senderId,
            query: messageText,
            conversation_history: history
        });
        
        // Send response back to Instagram
        await axios.post(
            'https://graph.instagram.com/v21.0/me/messages',
            {
                recipient: { id: senderId },
                message: { text: modelResponse.data.response }
            },
            {
                params: { access_token: ACCESS_TOKEN },
                headers: { 'Content-Type': 'application/json' }
            }
        );

        console.log(`Sent response to ${senderId}: ${modelResponse.data.response}`);
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
    
    // Verify signature
    const sig = signature.split('sha256=')[1];
    const expectedSignature = crypto
        .createHmac('sha256', APP_SECRET)
        .update(JSON.stringify(req.body))
        .digest('hex');
        
    if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expectedSignature))) {
        return res.sendStatus(403);
    }

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
        }
    } else {
        res.sendStatus(404);
    }
});

const PORT = process.env.PORT || 69;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));