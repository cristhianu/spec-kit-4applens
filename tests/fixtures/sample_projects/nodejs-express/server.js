const express = require('express');
const { CosmosClient } = require('@azure/cosmos');
const { BlobServiceClient } = require('@azure/storage-blob');
const { DefaultAzureCredential } = require('@azure/identity');
const redis = require('redis');

require('dotenv').config();

const app = express();
app.use(express.json());

// Cosmos DB setup
const cosmosClient = new CosmosClient({
  endpoint: process.env.COSMOS_ENDPOINT,
  key: process.env.COSMOS_KEY
});

// Redis setup
const redisClient = redis.createClient({
  url: process.env.REDIS_CONNECTION_STRING
});

redisClient.connect().catch(console.error);

// Storage setup
const blobServiceClient = new BlobServiceClient(
  `https://${process.env.STORAGE_ACCOUNT_NAME}.blob.core.windows.net`,
  new DefaultAzureCredential()
);

// Routes
app.get('/api/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

app.get('/api/products', async (req, res) => {
  try {
    const database = cosmosClient.database(process.env.COSMOS_DATABASE);
    const container = database.container('products');
    const { resources } = await container.items.readAll().fetchAll();
    res.json(resources);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/products', async (req, res) => {
  try {
    const database = cosmosClient.database(process.env.COSMOS_DATABASE);
    const container = database.container('products');
    const { resource } = await container.items.create(req.body);
    res.status(201).json(resource);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
