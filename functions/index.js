const functions = require('firebase-functions');
const { exec } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');

// Simple health check endpoint
exports.health = functions.https.onRequest((req, res) => {
  res.json({ status: 'OK', message: 'Kalaa Saarathi API is running' });
});

// WhatsApp webhook handler
exports.whatsapp = functions.https.onRequest((req, res) => {
  // Set CORS headers
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Methods', 'GET, POST');
  res.set('Access-Control-Allow-Headers', 'Content-Type');
  
  // Handle preflight request
  if (req.method === 'OPTIONS') {
    res.status(204).send('');
    return;
  }

  console.log('WhatsApp webhook received:', req.method, req.body);
  
  // For now, send a simple response
  res.set('Content-Type', 'text/xml');
  res.send(`
    <Response>
      <Message>Thanks for your message! Kalaa Saarathi is working.</Message>
    </Response>
  `);
});

// API endpoints handler (simplified)
exports.api = functions.https.onRequest((req, res) => {
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE');
  res.set('Access-Control-Allow-Headers', 'Content-Type');
  
  if (req.method === 'OPTIONS') {
    res.status(204).send('');
    return;
  }
  
  // Simple API response
  res.json({ 
    message: "Kalaa Saarathi API", 
    status: "online",
    endpoints: {
      whatsapp: "/whatsapp",
      health: "/health",
      products: "/api/products"
    }
  });
});