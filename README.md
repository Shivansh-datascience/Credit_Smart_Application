# Credit Scoring Project

A comprehensive **credit scoring system** with **RAG (Retrieval-Augmented Generation) chatbot** powered by LangChain, Pinecone vector database, and DeepSeek LLM.

## 📋 Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Endpoints](#api-endpoints)
- [Architecture](#architecture)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## ✨ Features

### Authentication Service
- ✅ OTP generation and verification via **Email (SMTP)**
- ✅ Redis-based OTP storage with TTL
- ✅ User authentication and session management
- ✅ Fast2SMS integration for SMS OTP (optional)
- ✅ JWT token generation

### RAG Chatbot Service
- ✅ **Retrieval-Augmented Generation** (RAG) for accurate, context-aware responses
- ✅ **Pinecone vector database** for semantic search (1024-dimensional embeddings)
- ✅ **BGE-Large embeddings** for high-quality document encoding
- ✅ **DeepSeek LLM** for intelligent response generation
- ✅ **LangChain Expression Language (LCEL)** for composable chains
- ✅ MongoDB integration for conversation history
- ✅ Multi-document retrieval with context ranking
- ✅ Credit scoring knowledge base

### Additional Features
- 🔐 Environment-based configuration management
- 📊 MongoDB for data persistence
- ⚡ FastAPI for high-performance API endpoints
- 🔄 CORS support for cross-origin requests
- 📝 Comprehensive logging
- 🧪 Easy to test with Postman

---

## 📁 Project Structure

┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ├─────────────────────────┬──────────────────────────┐
       │                         │                          │
       ▼                         ▼                          ▼
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│ Auth Service │         │   Chatbot    │         │   MongoDB    │
│  (Port 8000) │         │ Service      │         │              │
└──────┬───────┘         │ (Port 8001)  │         └──────────────┘
       │                 └───────┬──────┘
       │                         │
       │              ┌──────────┼──────────┐
       │              │          │          │
       ▼              ▼          ▼          ▼
┌──────────────┐ ┌─────────┐ ┌────────┐ ┌──────────┐
│    Redis     │ │ Pinecone│ │DeepSeek│ │ BGE-Emb  │
│   (OTP)      │ │  (VDB)  │ │  LLM   │ │ Embedder │
└──────────────┘ └─────────┘ └────────┘ └──────────┘
