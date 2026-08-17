# Screenshot Guide

Automatic screenshot capture is not reliable for this CLI/TTS workflow because several outputs depend on interactive input, local services, API keys, and audio behavior. Capture screenshots manually using the commands below and save them in `docs/screenshots/`.

| Screenshot Name | Command / Action | Expected Output | Purpose | Slide Number |
|---|---|---|---|---|
| `01_Startup_Screen.png` | `python app.py` | AURA header and welcome prompt | Show application startup | 18 |
| `02_Greeting.png` | Start app and capture greeting | Aura greeting message | Show assistant greeting | 18 |
| `03_Conversation.png` | Type `Hello` | Ollama/local conversation response | Show local AI chat | 17 |
| `04_Programming_Groq.png` | Type `Write Python code to reverse a string` | Programming response routed to Groq | Show cloud AI routing | 17 |
| `05_Wikipedia.png` | Type `/wiki Alan Turing` | Wikipedia summary | Show knowledge service | 17 |
| `06_Weather.png` | Type `/weather Kochi` | Live weather information | Show Open-Meteo integration | 17 |
| `07_Maps.png` | Type `/map Kochi` | Location results with coordinates | Show OpenStreetMap integration | 17 |
| `08_Translation.png` | Type `Translate hello to French` | Translation response | Show Hugging Face/AI translation | 17 |
| `09_Language_Switching.png` | Type `Speak in Malayalam` | Language mode changed | Show multilingual support | 17 |
| `10_Error_Handling.png` | Temporarily remove an API key and run provider command | Friendly error without crash | Show error handling | 17 |
| `11_Smart_Router_Logs.png` | Run app with logs visible | Intent, provider, model, execution logs | Show routing diagnostics | 15 |
| `12_Piper_Output.png` | Ask any question with speakers enabled | TTS speaks assistant response only | Show speech synthesis | 17 |

## Capture Instructions

1. Open a terminal at the project root.
2. Run `python app.py`.
3. Execute the command listed in the table.
4. Use the Windows Snipping Tool or screenshot shortcut.
5. Save the file with the exact screenshot name under `docs/screenshots/`.
