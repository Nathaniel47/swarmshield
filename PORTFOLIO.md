# Portfolio card

## SwarmShield: Prompt Infection and Memory Poisoning in Multi-Agent LLM Systems

What happens when one AI agent in a team reads a poisoned document? SwarmShield is a simulation testbed that answers this. It runs a small swarm of cooperating agents (planner, researchers, writers) in plain Python, plants a self-copying prompt or a poisoned memory note, and tracks the spread like an epidemic across chain, star and mesh networks, with a SIR-style model fitted in NetworkX. Three defences (provenance tags, a message sanitiser, a majority check) are scored on security and task success on a held-out test set, with automatic, judge-free scoring. A live Streamlit graph shows agents turning infected round by round. Built on free tools with synthetic data; results use a scripted stand-in for the model, with limits documented openly.

**Stack:** Python, NetworkX, NumPy, Streamlit, Plotly, SQLite, Groq/Gemini free APIs, Docker, GitHub Actions.

**Links:** repo https://github.com/Nathaniel47/swarmshield, live demo https://swarmshield.streamlit.app.

## One sentence for emailing professors

SwarmShield studies how a single prompt injection or poisoned memory entry propagates through a multi-agent LLM system, treats the spread as an epidemic on the agent network, and compares provenance, sanitising and voting defences, which connects directly to current work on memory poisoning (for example AgentPoison), prompt infection between agents, and the safety of cooperating agent teams.
