# DFD Level 0 - Context Diagram

```mermaid
flowchart LR
    U[User] --> A[AURA Desktop Assistant]
    A --> U
    A --> API[External APIs]
    API --> A
    A --> LLM[Local and Cloud AI Providers]
    LLM --> A
```

## Description

The user interacts with AURA through the current CLI interface. AURA routes requests to local AI, cloud AI, and external APIs, then returns formatted text and speech output to the user.
