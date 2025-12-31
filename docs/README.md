---
title: AI Grounding Documentation
description: Comprehensive documentation for AI grounding strategies demonstrating input-based and input-output grounding patterns with LLMs
version: 1.0.0
last_updated: 2025-12-31
related: [architecture.md, setup.md, api.md]
tags: [python, ai-grounding, rag, langchain, faiss, chroma]
---

# AI Grounding Documentation

Welcome to the comprehensive documentation for the **AI Grounding** project. This project demonstrates three distinct approaches to grounding AI systems with external data sources, focusing on user search and retrieval patterns.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Grounding Approaches](#grounding-approaches)
- [Key Concepts](#key-concepts)
- [Learning Objectives](#learning-objectives)
- [Documentation Index](#documentation-index)
- [Contributing](#contributing)

## Overview

This project is an educational demonstration that explores different AI grounding strategies, ranging from simple context injection to sophisticated input-output grounding with real-time data synchronization. It provides hands-on examples of:

- **RAG (Retrieval Augmented Generation)** patterns
- **Vector similarity search** using FAISS and Chroma
- **API-based parameter extraction** and structured queries
- **Token optimization** and cost management strategies
- **Output grounding** for hallucination prevention

### What is AI Grounding?

**Grounding** refers to connecting Large Language Models (LLMs) to external, verified data sources to:
1. Reduce hallucinations
2. Provide up-to-date information beyond training data
3. Enable domain-specific knowledge integration
4. Verify and validate generated outputs

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- DIAL API key (EPAM internal)

### 5-Minute Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd ai-dial-grounding

# 2. Start the user service
docker-compose up -d

# 3. Create virtual environment and install dependencies
python -m venv dial_grounding
source dial_grounding/bin/activate  # On Windows: dial_grounding\Scripts\activate
pip install -r requirements.txt

# 4. Set API credentials
export DIAL_API_KEY="your-api-key-here"  # Get from EPAM support portal

# 5. Run a sample approach
python -m task.t1.no_grounding
```

For detailed setup instructions, see [Setup Guide](./setup.md).

## Project Structure

```
ai-dial-grounding/
├── task/                      # Core implementation modules
│   ├── _constants.py          # API configuration and endpoints
│   ├── user_client.py         # User service client wrapper
│   ├── t1/                    # Task 1: No Grounding
│   │   └── no_grounding.py
│   ├── t2/                    # Task 2: Input-based Grounding
│   │   ├── Input_vector_based.py   # Vector similarity search
│   │   └── input_api_based.py      # API parameter extraction
│   └── t3/                    # Task 3: Input-Output Grounding
│       ├── in_out_grounding.py
│       └── run_local_test.py
├── data/                      # Persistent data storage
│   └── vectorstores/          # Chroma vector database
├── docs/                      # Documentation (you are here)
├── dial_grounding/            # Python virtual environment
├── docker-compose.yml         # User service container config
├── requirements.txt           # Python dependencies
└── README.md                  # Project introduction
```

## Grounding Approaches

This project implements three progressively sophisticated grounding strategies:

### 1. No Grounding ([t1/no_grounding.py](../task/t1/no_grounding.py))

**Strategy:** Load all data into LLM context without external knowledge integration.

```mermaid
flowchart LR
    A[User Query] --> B[Fetch All Users]
    B --> C[Batch Users]
    C --> D[LLM Processing]
    D --> E[Combine Results]
    E --> F[Final Answer]
```

**Use Cases:** Small datasets, complete context requirements, baseline comparisons.

### 2. Input-based Grounding ([t2/](../task/t2/))

**Strategy:** Filter relevant data before LLM processing.

#### 2.1 Vector-based ([Input_vector_based.py](../task/t2/Input_vector_based.py))
- Semantic similarity search using embeddings
- FAISS vector store for efficient retrieval
- Top-k most relevant results

#### 2.2 API-based ([input_api_based.py](../task/t2/input_api_based.py))
- Extract search parameters from natural language
- Structured API calls with specific filters
- Exact matching against live data

### 3. Input-Output Grounding ([t3/in_out_grounding.py](../task/t3/in_out_grounding.py))

**Strategy:** Combine semantic search with structured output and real-time verification.

- Vector similarity for candidate selection
- Pydantic models for structured LLM outputs
- Output verification against source API
- Auto-sync vector store with data changes

For detailed architecture, see [Architecture Documentation](./architecture.md).

## Key Concepts

### RAG (Retrieval Augmented Generation)
Pattern where LLM responses are augmented with retrieved context from external sources.

### Vector Embeddings
Numerical representations of text that capture semantic meaning, enabling similarity-based search.

### Grounding vs Hallucination
- **Grounding:** Connecting LLM outputs to verified external data
- **Hallucination:** LLM generating plausible but incorrect information

### Token Optimization
Strategies to reduce API costs and latency:
- Selective context loading
- Compact document representations
- Batch processing
- Result filtering

## Learning Objectives

By exploring this project, you will learn:

1. **RAG Fundamentals**
   - When to use RAG vs direct LLM queries
   - Trade-offs between different retrieval strategies

2. **Vector Search Implementation**
   - Creating and managing embeddings
   - FAISS vs Chroma for different use cases
   - Similarity scoring and threshold tuning

3. **Cost Optimization**
   - Token counting and budget management
   - Batch processing strategies
   - Context window optimization

4. **Production Patterns**
   - Data synchronization strategies
   - Error handling in distributed systems
   - Output validation and grounding

5. **LLM Integration**
   - Prompt engineering for structured outputs
   - Pydantic models for output parsing
   - Async processing patterns

## Documentation Index

| Document | Description |
|----------|-------------|
| [Architecture](./architecture.md) | System design, data flows, and component interactions |
| [API Reference](./api.md) | User service API endpoints and client methods |
| [Setup Guide](./setup.md) | Environment setup, dependencies, and configuration |
| [Testing Guide](./testing.md) | Test strategy, running tests, and validation |
| [Glossary](./glossary.md) | Domain-specific terms and abbreviations |
| [Roadmap](./roadmap.md) | Project milestones and future enhancements |
| [Changelog](./changelog.md) | Version history and notable changes |
| [ADR Index](./adr/) | Architecture Decision Records |

## Contributing

This is an educational project. Contributions are welcome! Please:

1. Review the [Architecture Documentation](./architecture.md)
2. Follow existing code patterns
3. Add tests for new features
4. Update documentation for changes

## Support

For questions or issues:
- Review the [Glossary](./glossary.md) for terminology
- Check [Setup Guide](./setup.md) for environment issues
- See [API Documentation](./api.md) for integration help

## License

TODO: Add license information

---

**Next Steps:**
- Read [Architecture Documentation](./architecture.md) for system design
- Follow [Setup Guide](./setup.md) to get started
- Explore [API Reference](./api.md) for integration details
