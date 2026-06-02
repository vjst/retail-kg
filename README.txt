==============================================
RETAIL KNOWLEDGE GRAPH EXPLORER
==============================================

FOLDER STRUCTURE:
  index.html      ← Open this in browser (frontend)
  app.py          ← Flask API server (backend)
  backend.py      ← Soumyasree's Neo4j + Groq logic
  seed_graph.py   ← Already run ✅ data is in Neo4j
  requirements.txt

SETUP STEPS:
--------------
1. Make sure Neo4j Desktop is RUNNING (retail_kg instance)

2. Copy backend.py and seed_graph.py into this folder
   (you already have them from the GitHub repo)

3. Set your Groq API key:
   In backend.py line ~85:
   GROQ_API_KEY = "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"

4. Install dependencies:
   python -m pip install flask flask-cors neo4j groq

5. Start the API server:
   python app.py

6. Open index.html in Chrome
   → Page 1: Dashboard with real stats
   → Page 2: Knowledge Graph Explorer (tree + graph)
   → Page 3: AI Chatbot powered by Groq LLaMA 3.3

SAMPLE QUESTIONS FOR AI:
  "What breaks if DB-Server-01 crashes?"
  "Show full path for Store Operations"
  "What applications support POS Transaction Processing?"
  "What are the most critical services?"
  "What tech does POS Application use?"

==============================================
