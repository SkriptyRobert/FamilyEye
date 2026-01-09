---
trigger: always_on
---

Agent Code Freeze Protocol
TARGET SCOPE: clients/windows/agent/**/*

The Windows Agent code is considered STABLE and FROZEN.

🚫 RESTRICTIONS
You are FORBIDDEN from modifying any file within the clients/windows/agent directory or its subdirectories.
You are FORBIDDEN from proposing changes to the agent logic unless specifically asked to debug a critical agent failure.
🔓 EXCEPTION PROCEDURE
If a modification is absolutely necessary (violating the freeze), you MUST follow this strict protocol BEFORE writing any code:

STOP: Do not execute any tool to write/replace files.
NOTIFY: Inform the user that the requested task requires modifying the Frozen Agent Code.
ASSESS: Provide a detailed "Risk Assessment":
What exactly needs to change?
Why can't this be handled on the Backend?
What is the risk of breaking existing functionality (Offline mode, Self-healing, Ghost filtering)?
APPROVAL: Explicitly ask: "Do I have permission to unfreeze the Agent code for this specific change?"
EXECUTE: Only proceed if the user replies with a clear "YES".