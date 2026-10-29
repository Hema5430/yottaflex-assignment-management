# AI Usage & Prompt Documentation

## AI Tools Used

- **ChatGPT:** Development assistance, debugging, and documentation.
- **Claude:** Reference and guidance for application architecture, component organization, and design decisions.
- **Groq API — GPT-OSS 20B:** LLM integration for explaining detected anomalies and suggesting reviewer actions.

## Application Prompt

**Objective:** Explain detected assignment-management anomalies in clear, professional language.

> Explain the detected anomaly using the provided application context. Identify the violated business rule, describe why the issue matters, and suggest practical steps for a reviewer to investigate it. Use only the available evidence, do not invent missing information, and distinguish confirmed facts from assumptions.

## AI Implementation Approach

Anomaly detection is performed using deterministic Python and SQL business rules. The LLM explains findings and suggests next steps; it does not independently determine anomalies or authorize grade changes.

## Responsible AI

AI-generated explanations are advisory and should be verified against underlying records. API credentials are stored in environment variables rather than source code.

*Note: The application prompt above documents the intended behavior. It should be treated as the exact implementation prompt only if it matches the prompt in `webapp/main.py`.*
