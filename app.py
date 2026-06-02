"""
app.py — Retail Knowledge Graph Explorer
Flask server that connects frontend to Neo4j + Groq AI
Run: python app.py
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import sys, os

# Add current directory to path so backend.py can be imported
sys.path.insert(0, os.path.dirname(__file__))

# ── Import Soumyasree's backend ──────────────────────────────────────────────
from backend import (
    get_graph_stats,
    get_all_domains,
    get_capabilities_for_domain,
    get_services_for_capability,
    get_applications_for_business_service,
    get_tech_for_application,
    get_infra_for_tech,
    get_full_path,
    get_blast_radius,
    get_critical_services,
    search_nodes,
    answer_question,
)

app = Flask(__name__)
CORS(app)   # Allow frontend HTML to call this API

# ── SECTION 1: Stats (Page 1 - Dashboard) ───────────────────────────────────

@app.route("/api/stats")
def stats():
    """Returns node counts for dashboard cards."""
    return jsonify(get_graph_stats())

@app.route("/api/domains")
def domains():
    """Returns all L1 Business Domains."""
    return jsonify(get_all_domains())

@app.route("/api/critical-services")
def critical():
    """Returns high/critical services for dashboard."""
    return jsonify(get_critical_services())

# ── SECTION 2: Hierarchy (Page 2 - Knowledge Graph Explorer) ─────────────────

@app.route("/api/capabilities/<domain>")
def capabilities(domain):
    """L2: capabilities for a domain."""
    return jsonify(get_capabilities_for_domain(domain))

@app.route("/api/services/<cap>")
def services(cap):
    """L3: services for a capability."""
    return jsonify(get_services_for_capability(cap))

@app.route("/api/applications/<svc>")
def applications(svc):
    """L4: apps for a service."""
    return jsonify(get_applications_for_business_service(svc))

@app.route("/api/tech/<app_name>")
def tech(app_name):
    """L5: tech for an app."""
    return jsonify(get_tech_for_application(app_name))

@app.route("/api/infra/<tech_name>")
def infra(tech_name):
    """L6: infra for a tech component."""
    return jsonify(get_infra_for_tech(tech_name))

@app.route("/api/full-path/<domain>")
def full_path(domain):
    """Complete 6-layer chain for a domain."""
    return jsonify(get_full_path(domain))

@app.route("/api/blast-radius/<infra_name>")
def blast_radius(infra_name):
    """Impact analysis — what breaks if this infra fails."""
    return jsonify(get_blast_radius(infra_name))

@app.route("/api/search")
def search():
    """Search nodes by name."""
    q = request.args.get("q", "")
    return jsonify(search_nodes(q))

# ── SECTION 3: AI Chatbot (Page 3) ───────────────────────────────────────────

# Store conversation history per session (simple in-memory)
chat_history = []

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    AI chatbot endpoint.
    POST body: { "question": "What breaks if DB-Server-01 crashes?" }
    Returns: { explanation, graph_data, intent_result }
    """
    global chat_history
    data     = request.json
    question = data.get("question", "")

    if not question:
        return jsonify({"error": "No question provided"}), 400

    # Call Soumyasree's full AI pipeline
    result = answer_question(question, history=chat_history)

    # Save to history for multi-turn context
    chat_history.append({
        "question":       question,
        "answer":         result["explanation"],
        "intent_summary": result["intent_summary"],
    })

    # Keep last 10 turns only
    if len(chat_history) > 10:
        chat_history = chat_history[-10:]

    return jsonify({
        "explanation":   result["explanation"],
        "graph_data":    result["graph_data"],
        "intent_result": result["intent_result"],
    })

@app.route("/api/chat/clear", methods=["POST"])
def clear_chat():
    """Clear conversation history."""
    global chat_history
    chat_history = []
    return jsonify({"status": "cleared"})

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Retail KG API running at http://localhost:5000")
    print("📊 Open index.html in your browser")
    app.run(debug=True, port=5000)
