
```markdown
# Dialogflow CX Specialist - Interaction Guide
**Standard Operating Procedures & Test Prompts**

This document provides a categorized list of prompts to help you get the most out of the Dialogflow CX Specialist.

---

## 🏁 Quick Start (Top 5)
*Just getting started? Try these.*

1. **"List all Dialogflow agents"** (Finds everything in the default US region)
2. **"Show configuration for [Agent Name]"** (Checks health/settings)
3. **"List intents for [Agent Name]"** (See what the bot knows)
4. **"List webhooks for [Agent Name]"** (Check backend connections)
5. **"Show training phrases for Default Welcome Intent"** (Audit NLU)

---

## 🟢 Level 1: Discovery & Inventory
*Use these to locate bots across different environments.*

| Goal | User Prompt | Expected Outcome |
| :--- | :--- | :--- |
| **Find All Agents** | "List all agents in the US" | Lists agents in `us` multi-region. |
| **Check Specific Region** | "List agents in europe-west1" | Lists agents hosted in Belgium. |
| **Global Search** | "List global agents" | Checks the `global` non-regional endpoint. |
| **Inventory Count** | "How many agents do we have?" | Returns a total count and summary list. |

---

## 🟡 Level 2: Configuration Audits
*Use these to verify settings consistency.*

| Goal | User Prompt | Expected Outcome |
| :--- | :--- | :--- |
| **Full Config Audit** | "Show config for [Agent Name]" | Returns Timezone, Language, Logging status. |
| **Check Languages** | "What languages does it support?" | Lists primary (e.g., en) and secondary (e.g., es). |
| **Verify Timezone** | "What is the agent's time zone?" | Critical for "Opening Hours" logic. |
| **Security Check** | "Is logging enabled?" | Verifies if Stackdriver logging is active. |

---

## 🟠 Level 3: Intent & NLU Inspection
*Use these to debug matching issues or audit training data.*

| Goal | User Prompt | Expected Outcome |
| :--- | :--- | :--- |
| **List Intents** | "List all intents for [Agent Name]" | Summarizes all intents with phrase counts. |
| **Find Weak Intents** | "Which intents have 0 training phrases?" | Identifies empty intents that won't trigger. |
| **Deep Dive** | "Show training phrases for [Intent]" | Lists every user example phrase for that intent. |
| **Check Parameters** | "What parameters does [Intent] use?" | Shows entities (e.g., @date, @city) and requirements. |

---

## 🔴 Level 4: Webhook & Backend
*Use these when the bot responds with "Webhook call failed".*

| Goal | User Prompt | Expected Outcome |
| :--- | :--- | :--- |
| **List Endpoints** | "List webhooks for [Agent Name]" | Shows names, target URLs, and status. |
| **Check Timeouts** | "What is the webhook timeout?" | Verifies if timeout is too short (e.g., <5s). |
| **Disabled Check** | "Are any webhooks disabled?" | Highlights integrations that are turned off. |

---

## 💡 Advanced Workflows

### Scenario A: The "Production Audit"
*You need to verify a live bot is healthy.*
1. **"List agents in us-central1"** (Find the prod bot)
2. **"Show config for Prod-Bot"** (Verify logging is ON)
3. **"List webhooks for Prod-Bot"** (Verify it points to Prod URL, not Dev)
4. **"Show details for 'Make Payment' intent"** (Ensure sensitive parameters are redacted)

### Scenario B: The "Migration Comparison"
*You moved a bot from Dev to QA. Did everything copy over?*
1. **"Show config for Dev-Bot"**
2. **"Show config for QA-Bot"**
3. **"List intents for Dev-Bot"** (Note the count, e.g., 50)
4. **"List intents for QA-Bot"** (Verify count matches 50)

---

## ⚠️ Edge Cases & "What If"

**Q: I don't know the full agent name.**
> **Prompt:** "Search for a bot like 'billing'"
> **Result:** The agent uses fuzzy matching to find "Billing-Support-v2".

**Q: I need to check multiple regions.**
> **Prompt:** "List agents in us-east1 and europe-west1"
> **Result:** The agent will execute two searches and combine the results.

**Q: I need conversation traffic metrics.**
> **Prompt:** "How many users spoke to the bot today?"
> **Result:** The agent will explain it cannot access live metrics and guide you to BigQuery.
