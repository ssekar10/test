# Dialogflow CX Specialist Agent 🤖

**Version:** 1.0.0  
**Status:** ✅ Production Ready  
**Last Updated:** 2026-02-04

## 📖 Overview

The **Dialogflow CX Specialist** is an intelligent AI assistant designed to help teams manage, audit, and troubleshoot Dialogflow CX virtual agents. It acts as a read-only administrator that can instantly discover agents across all Google Cloud regions, analyze intent structures, verify configurations, and inspect webhook settings.

**Target Audience:**
- **Product Managers:** To audit intent coverage and training data.
- **Developers:** To verify configurations and webhook settings.
- **Support Teams:** To quickly locate agents and check their health.

---

## 🚀 Capabilities & User Guide

### 1. 🌍 Agent Discovery
**Goal:** Locate bots across your Google Cloud environment.
- **What it does:** Scans all 16 GCP regions (US, Europe, Asia, etc.) to find agents.
- **Why use it:** Essential for managing multi-region deployments or finding "lost" dev agents.
- **Key Query:** *"List all agents in the US region"*

### 2. ⚙️ Configuration Analysis
**Goal:** Verify agent settings without accessing the console.
- **What it does:** Retrieves time zones, default languages, logging settings, and security options.
- **Why use it:** Ensure consistency between Dev and Prod environments.
- **Key Query:** *"Show configuration for the Billing-Support-Bot"*

### 3. 🧠 Intent & NLU Inspection
**Goal:** Audit the bot's understanding.
- **What it does:** Lists intents, counts training phrases, and details parameters/entities.
- **Why use it:** Identify intents with poor training coverage (e.g., 0 phrases).
- **Key Query:** *"Show training phrases for the 'Cancel Order' intent"*

### 4. 🔗 Webhook & Backend Check
**Goal:** Troubleshoot integration issues.
- **What it does:** Lists webhook URLs, timeout settings, and disabled status.
- **Why use it:** Quickly verify if a webhook is pointing to the correct Cloud Run service or if it's disabled.
- **Key Query:** *"List webhooks for the Sales-Bot"*

---

## 🧠 Intelligent Features for Users

### Context Awareness
The agent remembers what you are talking about. You don't need to repeat yourself.
> **User:** "List intents for **Support-Bot**"  
> **User:** "Show details for **Welcome Intent**" *(Implicitly knows it's for Support-Bot)*

### Smart Search (Fuzzy Matching)
You don't need exact names or IDs.
- **Case Insensitive:** "dr-agent" = "DR-Agent"
- **Partial Match:** "billing bot" finds "Billing-Support-v2"

### High Performance Caching
- **Fast:** Cached queries return in <100ms.
- **Fresh:** Cache automatically expires every 5 minutes.
- **Force Refresh:** Say *"Get fresh details..."* to bypass the cache.

---

## 🛠️ Developer Reference

### Architecture
The agent is built on a resilient architecture designed for scale:
- **Rate Limiting:** Enforces 100ms delay between calls with exponential backoff for `429` errors.
- **Resilience:** Auto-retries failed API calls up to 5 times.
- **Safety:** Safe protobuf parsing handles missing fields gracefully.

### API Tools Reference

| Tool | Description | Performance (Cached) |
| :--- | :--- | :--- |
| `list_agents(location)` | Discovers agents in a specific GCP region. Defaults to 'us'. | ~50ms |
| `get_agent_details_fast(id)` | Retrieves full agent config (Timezone, Lang, Logging). | ~10ms |
| `list_intents(agent_id)` | Lists all intents with training phrase counts. | ~20ms |
| `get_intent_details(id)` | Deep dive: returns all training phrases & parameters. | ~15ms |
| `list_webhooks(agent_id)` | Lists webhook URIs, timeouts, and headers. | ~15ms |

### Supported Regions
Supports all 16 Dialogflow CX regions including:
- **Americas:** `us-central1`, `us-east1`, `northamerica-northeast1`...
- **Europe:** `europe-west1` (Belgium), `europe-west2` (London)...
- **Asia:** `asia-northeast1` (Tokyo), `australia-southeast1` (Sydney)...

---

## 🛡️ Limitations & Workarounds

| Feature | Status | Reason & Alternative |
| :--- | :--- | :--- |
| **Real-time Metrics** | ⛔ Unavailable | API limitation. **Alt:** Use BigQuery Export or Console Analytics. |
| **Session History** | ⛔ Unavailable | Privacy/API limitation. **Alt:** Check "Conversation History" in Console. |
| **Webhook Logs** | ⚠️ Delegated | Webhooks are Cloud Run services. **Alt:** Ask the Cloud Run specialist. |
| **Edit/Write** | ⛔ Read-Only | Safety design. **Alt:** Use the Dialogflow CX Console. |

---

## ❓ Troubleshooting

**Error: "Agent not found"**
- **Fix:** Check the region. An agent in `europe-west1` won't show up if you search `us`.
- **Try:** *"List agents in global"* or *"List agents in europe-west1"*.

**Error: "Permission Denied"**
- **Fix:** Ensure the Service Account has `roles/dialogflow.reader`.

**Error: "Rate Limit Exceeded"**
- **Fix:** The agent is handling this. Wait 5 seconds and it will auto-retry.

---

## 📦 Installation

```bash
# Prerequisites
pip install google-cloud-dialogflow-cx google-auth

# Configuration
export GCP_PROJECT_ID="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"
