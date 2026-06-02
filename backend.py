"""
retail_kg_backend.py
====================
Single-file backend for the Retail Knowledge Graph Explorer.

Contains:
  ┌─ SECTION 1: Neo4j Driver & run_query helper
  ├─ SECTION 2: Layer Queries           (hierarchy explorer panels)
  ├─ SECTION 3: End-to-End Path Query   (get_full_path)
  ├─ SECTION 4: Impact / Blast Radius   (get_blast_radius, get_impact_for_service)
  ├─ SECTION 5: Graph Statistics        (get_graph_stats)
  ├─ SECTION 6: Search                  (search_nodes, get_all_infra)
  └─ SECTION 7: LLM Reasoning           (intent extraction, smart router, explanation)

Usage:
    from retail_kg_backend import (
        get_all_domains, get_blast_radius, answer_question, ...
    )
"""

import os
import re
import json

from neo4j import GraphDatabase
from groq import Groq


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — NEO4J DRIVER & QUERY HELPER
# ══════════════════════════════════════════════════════════════════════════════

#NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://127.0.0.1:7687")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "retail@123")

_driver = None


def get_driver():
    """Return (or lazily create) the Neo4j driver singleton."""
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
    return _driver


def run_query(cypher: str, **params) -> list[dict]:
    """Execute a Cypher query and return results as a list of plain dicts."""
    driver = get_driver()
    with driver.session() as session:
        result = session.run(cypher, **params)
        return [dict(r) for r in result]


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — LAYER QUERIES (Hierarchy Explorer Panels)
# ══════════════════════════════════════════════════════════════════════════════

def get_all_domains() -> list[dict]:
    """Return all BusinessDomain nodes ordered by portfolio then name."""
    return run_query(
        "MATCH (d:BusinessDomain) "
        "RETURN d.name AS name, d.portfolio AS portfolio "
        "ORDER BY d.portfolio, d.name"
    )


def get_capabilities_for_domain(domain_name: str) -> list[dict]:
    """Return all BusinessCapability nodes under a given domain."""
    return run_query(
        """
        MATCH (d:BusinessDomain {name:$name})-[:HAS_CAPABILITY]->(c:BusinessCapability)
        RETURN c.name AS name, c.level AS level
        ORDER BY c.name
        """,
        name=domain_name,
    )


def get_services_for_capability(cap_name: str) -> list[dict]:
    """Return all BusinessService nodes realised by a capability."""
    return run_query(
        """
        MATCH (c:BusinessCapability {name:$name})-[:REALIZED_BY]->(s:BusinessService)
        RETURN s.name AS name, s.criticality AS criticality
        ORDER BY s.criticality DESC, s.name
        """,
        name=cap_name,
    )


def get_applications_for_business_service(svc_name: str) -> list[dict]:
    """
    Return all Application nodes directly supported by a BusinessService
    (Layer 3 → Layer 4 in the 6-layer architecture).
    """
    return run_query(
        """
        MATCH (s:BusinessService {name:$name})-[:SUPPORTS]->(app:Application)
        RETURN app.name AS name, app.vendor AS vendor,
               app.type AS type, app.api_name AS api_name
        ORDER BY app.name
        """,
        name=svc_name,
    )


def get_tech_for_application(app_name: str) -> list[dict]:
    """Return all TechnologyComponent nodes used by an Application (DB + middleware)."""
    return run_query(
        """
        MATCH (app:Application {name:$name})-[r:USES_DB|USES_MW]->(t:TechnologyComponent)
        RETURN t.name AS name, t.type AS type,
               t.vendor AS vendor, type(r) AS relation
        ORDER BY t.type, t.name
        """,
        name=app_name,
    )


def get_infra_for_tech(tech_name: str) -> list[dict]:
    """Return all InfrastructureComponent nodes that host a TechnologyComponent."""
    return run_query(
        """
        MATCH (t:TechnologyComponent {name:$name})-[r:HOSTED_ON|CONNECTED_VIA]->(i:InfrastructureComponent)
        RETURN i.name AS name, i.type AS type, i.env AS env, type(r) AS relation
        ORDER BY i.type, i.name
        """,
        name=tech_name,
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — END-TO-END PATH QUERY
# ══════════════════════════════════════════════════════════════════════════════

def get_full_path(domain_name: str) -> list[dict]:
    """
    Return the complete 6-layer chain starting from a BusinessDomain.

    All inner joins use OPTIONAL MATCH so that nodes whose chain is broken
    at any layer are still included (strict MATCH would silently drop them).
    No LIMIT so large domains are never truncated.

    Layer order:
      Domain (L1) → Capability (L2) → BusinessService (L3)
      → Application (L4) → TechnologyComponent (L5) → Infrastructure (L6)
    """
    return run_query(
        """
        MATCH (d:BusinessDomain {name: $name})

        OPTIONAL MATCH (d)-[:HAS_CAPABILITY]->(c:BusinessCapability)
        OPTIONAL MATCH (c)-[:REALIZED_BY]->(s:BusinessService)
        OPTIONAL MATCH (s)-[:SUPPORTS]->(app:Application)
        OPTIONAL MATCH (app)-[:USES_DB|USES_MW]->(t:TechnologyComponent)
        OPTIONAL MATCH (t)-[:HOSTED_ON|CONNECTED_VIA]->(i:InfrastructureComponent)

        RETURN
            d.name          AS domain,
            c.name          AS capability,
            s.name          AS business_service,
            s.criticality   AS criticality,
            app.name        AS application,
            app.type        AS app_type,
            app.vendor      AS app_vendor,
            t.name          AS tech_component,
            t.type          AS tech_type,
            i.name          AS infra,
            i.type          AS infra_type,
            i.env           AS env

        ORDER BY c.name, s.name
        """,
        name=domain_name,
    )


def get_impact_for_service(svc_name: str) -> list[dict]:
    """Return the Impact node linked to a BusinessService."""
    return run_query(
        """
        MATCH (s:BusinessService {name:$name})-[:HAS_IMPACT]->(im:Impact)
        RETURN im.severity            AS severity,
               im.revenueLossPerHour  AS revenueLossPerHour,
               im.customerImpact      AS customerImpact,
               im.regulatoryImpact    AS regulatoryImpact
        """,
        name=svc_name,
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — IMPACT / BLAST RADIUS
# ══════════════════════════════════════════════════════════════════════════════

def get_blast_radius(infra_name: str) -> list[dict]:
    """
    Full 6-layer upstream traversal starting from an InfrastructureComponent.

    Path: Infra (L6) → Tech (L5) → App (L4) → BizSvc (L3)
          → Capability (L2) → Domain (L1)

    Results ordered by impact severity, then domain/capability/service name.
    """
    return run_query(
        """
        MATCH (i:InfrastructureComponent {name:$name})
              <-[:HOSTED_ON|CONNECTED_VIA]- (t:TechnologyComponent)
              <-[:USES_DB|USES_MW]-          (app:Application)
              <-[:SUPPORTS]-                 (s:BusinessService)
              <-[:REALIZED_BY]-              (bc:BusinessCapability)
              <-[:HAS_CAPABILITY]-           (bd:BusinessDomain)
        OPTIONAL MATCH (s)-[:HAS_IMPACT]->(im:Impact)
        RETURN
            bd.name   AS business_domain,
            bc.name   AS business_capability,
            s.name    AS business_service,
            s.criticality          AS criticality,
            app.name               AS application,
            app.type               AS app_type,
            t.name                 AS tech,
            i.name                 AS infra,
            i.type                 AS infra_type,
            im.severity            AS impact_severity,
            im.revenueLossPerHour  AS revenue_loss,
            im.customerImpact      AS customer_impact,
            im.regulatoryImpact    AS regulatory_impact
        ORDER BY
            CASE im.severity
                WHEN 'Critical' THEN 0
                WHEN 'High'     THEN 1
                WHEN 'Medium'   THEN 2
                ELSE 3
            END,
            bd.name, bc.name, s.name
        """,
        name=infra_name,
    )


def get_critical_services() -> list[dict]:
    """Return all High/Critical BusinessService nodes with their Impact data."""
    return run_query(
        """
        MATCH (s:BusinessService)-[:HAS_IMPACT]->(im:Impact)
        WHERE im.severity IN ['Critical', 'High']
        RETURN s.name AS service,
               s.criticality          AS criticality,
               im.severity            AS impact_severity,
               im.revenueLossPerHour  AS revenue_loss,
               im.customerImpact      AS customer_impact
        ORDER BY
            CASE im.severity
                WHEN 'Critical' THEN 0
                WHEN 'High'     THEN 1
                ELSE 2
            END,
            s.name
        """
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — GRAPH STATISTICS
# ══════════════════════════════════════════════════════════════════════════════

def get_graph_stats() -> dict:
    """
    Return a count of nodes per layer plus total relationship count.

    Keys: BusinessDomain, BusinessCapability, BusinessService,
          Application, TechnologyComponent, InfrastructureComponent,
          Impact, Relationships
    """
    labels = [
        "BusinessDomain",
        "BusinessCapability",
        "BusinessService",
        "Application",
        "TechnologyComponent",
        "InfrastructureComponent",
        "Impact",
    ]
    stats: dict = {}
    for label in labels:
        result = run_query(f"MATCH (n:{label}) RETURN count(n) AS cnt")
        stats[label] = result[0]["cnt"] if result else 0

    rel_result = run_query("MATCH ()-[r]->() RETURN count(r) AS cnt")
    stats["Relationships"] = rel_result[0]["cnt"] if rel_result else 0
    return stats


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — SEARCH & UTILITY
# ══════════════════════════════════════════════════════════════════════════════

def search_nodes(query: str) -> list[dict]:
    """Full-text search across all node labels by name (case-insensitive contains)."""
    return run_query(
        """
        CALL {
            MATCH (n:BusinessDomain)
                WHERE toLower(n.name) CONTAINS toLower($q)
                RETURN n.name AS name, 'BusinessDomain' AS label
            UNION
            MATCH (n:BusinessCapability)
                WHERE toLower(n.name) CONTAINS toLower($q)
                RETURN n.name AS name, 'BusinessCapability' AS label
            UNION
            MATCH (n:BusinessService)
                WHERE toLower(n.name) CONTAINS toLower($q)
                RETURN n.name AS name, 'BusinessService' AS label
            UNION
            MATCH (n:Application)
                WHERE toLower(n.name) CONTAINS toLower($q)
                RETURN n.name AS name, 'Application' AS label
            UNION
            MATCH (n:TechnologyComponent)
                WHERE toLower(n.name) CONTAINS toLower($q)
                RETURN n.name AS name, 'TechnologyComponent' AS label
            UNION
            MATCH (n:InfrastructureComponent)
                WHERE toLower(n.name) CONTAINS toLower($q)
                RETURN n.name AS name, 'InfrastructureComponent' AS label
        }
        RETURN name, label ORDER BY label, name
        """,
        q=query,
    )


def get_all_infra() -> list[dict]:
    """Return every InfrastructureComponent node (type + env)."""
    return run_query(
        "MATCH (i:InfrastructureComponent) "
        "RETURN i.name AS name, i.type AS type, i.env AS env "
        "ORDER BY i.type, i.name"
    )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — LLM REASONING  (intent extraction → routing → explanation)
# ══════════════════════════════════════════════════════════════════════════════

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
GROQ_MODEL   = "llama-3.3-70b-versatile"


# ── 7.1  Groq client ──────────────────────────────────────────────────────────

def get_groq_client() -> Groq:
    key = os.getenv("GROQ_API_KEY", GROQ_API_KEY)
    if not key:
        raise ValueError("GROQ_API_KEY is not set.")
    return Groq(api_key=key)


# ── 7.2  Entity resolution ────────────────────────────────────────────────────

_node_cache: list[dict] | None = None


def _get_all_nodes() -> list[dict]:
    """Cache all node names + labels from Neo4j for fuzzy matching."""
    global _node_cache
    if _node_cache is not None:
        return _node_cache
    _node_cache = run_query(
        """
        CALL {
            MATCH (n:BusinessDomain)
                RETURN n.name AS name, 'BusinessDomain' AS label
            UNION MATCH (n:BusinessCapability)
                RETURN n.name AS name, 'BusinessCapability' AS label
            UNION MATCH (n:BusinessService)
                RETURN n.name AS name, 'BusinessService' AS label
            UNION MATCH (n:Application)
                RETURN n.name AS name, 'Application' AS label
            UNION MATCH (n:TechnologyComponent)
                RETURN n.name AS name, 'TechnologyComponent' AS label
            UNION MATCH (n:InfrastructureComponent)
                RETURN n.name AS name, 'InfrastructureComponent' AS label
        }
        RETURN name, label
        """
    )
    return _node_cache


def _key(s: str) -> str:
    """Normalise a string for fuzzy comparison (strip whitespace/punctuation)."""
    return re.sub(r"[\s\-_&/()]", "", s.lower())


def resolve_entity(entity: str) -> tuple[str, str]:
    """
    Fuzzy-match an entity string to a real graph node.

    Resolution passes (first match wins):
      1. Exact normalised match
      2. Substring in either direction
      3. Word-overlap >= 45 %

    Returns (canonical_name, layer_label).
    """
    if not entity:
        return entity, ""
    nodes = _get_all_nodes()
    ek = _key(entity)

    # Pass 1: exact normalised
    for r in nodes:
        if _key(r["name"]) == ek:
            return r["name"], r["label"]

    # Pass 2: substring either way
    for r in nodes:
        nk = _key(r["name"])
        if ek in nk or nk in ek:
            return r["name"], r["label"]

    # Pass 3: word-overlap ≥ 45 %
    e_words = set(re.sub(r"[\s\-_&/()]", " ", entity.lower()).split())
    best, best_row = 0.0, None
    for r in nodes:
        n_words = set(re.sub(r"[\s\-_&/()]", " ", r["name"].lower()).split())
        score = len(e_words & n_words) / max(len(e_words | n_words), 1)
        if score > best:
            best, best_row = score, r
    if best >= 0.45 and best_row:
        return best_row["name"], best_row["label"]

    return entity, ""


# ── 7.3  Multi-layer traversal helpers ───────────────────────────────────────

def _down(name: str, layer: str) -> list[dict]:
    """Traverse one step downward from any layer."""
    if layer == "BusinessDomain":      return get_capabilities_for_domain(name)
    if layer == "BusinessCapability":  return get_services_for_capability(name)
    if layer == "BusinessService":     return get_applications_for_business_service(name)
    if layer == "Application":         return get_tech_for_application(name)
    if layer == "TechnologyComponent": return get_infra_for_tech(name)
    return []


def _up(name: str, layer: str) -> list[dict]:
    """Traverse upward — returns business impact records."""
    if layer == "InfrastructureComponent":
        return get_blast_radius(name)
    if layer == "TechnologyComponent":
        infra = get_infra_for_tech(name)
        r: list[dict] = []
        for i in infra:
            r.extend(get_blast_radius(i["name"]))
        return r or infra
    if layer == "Application":
        return run_query(
            """
            MATCH (app:Application {name:$name})
                  <-[:SUPPORTS]-(bs:BusinessService)
                  <-[:REALIZED_BY]-(bc:BusinessCapability)
                  <-[:HAS_CAPABILITY]-(bd:BusinessDomain)
            RETURN bd.name AS domain, bc.name AS capability,
                   bs.name AS business_service, bs.criticality AS criticality
            """,
            name=name,
        )
    if layer == "BusinessService":
        return get_impact_for_service(name)
    if layer == "BusinessCapability":
        return run_query(
            """
            MATCH (bd:BusinessDomain)-[:HAS_CAPABILITY]->(bc:BusinessCapability {name:$name})
            RETURN bd.name AS domain, bc.name AS capability
            """,
            name=name,
        )
    return []


def _full_chain(name: str, layer: str) -> list[dict]:
    """Return the full 6-layer chain for any starting layer."""
    if layer == "BusinessDomain":
        return get_full_path(name)
    if layer == "BusinessCapability":
        return run_query(
            """
            MATCH (bc:BusinessCapability {name:$name})-[:REALIZED_BY]->(bs:BusinessService)
                  -[:SUPPORTS]->(app:Application)
                  -[:USES_DB|USES_MW]->(tc:TechnologyComponent)
                  -[:HOSTED_ON|CONNECTED_VIA]->(ic:InfrastructureComponent)
            OPTIONAL MATCH (bs)-[:HAS_IMPACT]->(im:Impact)
            RETURN bc.name AS capability,
                   bs.name AS business_service, bs.criticality AS criticality,
                   app.name AS application, app.type AS app_type,
                   tc.name AS tech, ic.name AS infra, ic.env AS env,
                   im.severity AS impact_severity,
                   im.revenueLossPerHour AS revenue_loss
            """,
            name=name,
        )
    if layer in ("BusinessService", "Application"):
        return run_query(
            """
            MATCH (bs:BusinessService)-[:SUPPORTS]->(app:Application)
                  -[:USES_DB|USES_MW]->(tc:TechnologyComponent)
                  -[:HOSTED_ON|CONNECTED_VIA]->(ic:InfrastructureComponent)
            WHERE bs.name=$name OR app.name=$name
            OPTIONAL MATCH (bs)-[:HAS_IMPACT]->(im:Impact)
            RETURN bs.name AS business_service, bs.criticality AS criticality,
                   app.name AS application, app.type AS app_type,
                   tc.name AS tech, ic.name AS infra, ic.env AS env,
                   im.severity AS impact_severity,
                   im.revenueLossPerHour AS revenue_loss
            """,
            name=name,
        )
    if layer == "TechnologyComponent":
        return get_infra_for_tech(name)
    if layer == "InfrastructureComponent":
        return get_blast_radius(name)
    return []


def _applications_for_layer(name: str, layer: str) -> list[dict]:
    """Return Applications reachable from ANY layer (multi-hop where needed)."""
    if layer == "BusinessService":
        return get_applications_for_business_service(name)
    if layer == "BusinessCapability":
        svcs = get_services_for_capability(name)
        r: list[dict] = []
        for s in svcs:
            apps = get_applications_for_business_service(s["name"])
            for a in apps:
                a["business_service"] = s["name"]
            r.extend(apps)
        return r
    if layer == "BusinessDomain":
        caps = get_capabilities_for_domain(name)
        r = []
        for c in caps:
            svcs = get_services_for_capability(c["name"])
            for s in svcs:
                apps = get_applications_for_business_service(s["name"])
                for a in apps:
                    a["capability"]      = c["name"]
                    a["business_service"] = s["name"]
                r.extend(apps)
        return r
    if layer == "Application":
        return [{"name": name, "layer": "Application"}]
    return []


def _tech_for(name: str, layer: str) -> list[dict]:
    """Return TechnologyComponents reachable from ANY layer."""
    if layer == "Application":
        return get_tech_for_application(name)
    if layer == "BusinessService":
        return run_query(
            """
            MATCH (bs:BusinessService {name:$name})-[:SUPPORTS]->(app:Application)
                  -[:USES_DB|USES_MW]->(tc:TechnologyComponent)
            RETURN app.name AS application,
                   tc.name AS tech, tc.type AS type, tc.vendor AS vendor
            """,
            name=name,
        )
    if layer == "BusinessCapability":
        return run_query(
            """
            MATCH (bc:BusinessCapability {name:$name})-[:REALIZED_BY]->(bs:BusinessService)
                  -[:SUPPORTS]->(app:Application)
                  -[:USES_DB|USES_MW]->(tc:TechnologyComponent)
            RETURN bs.name AS business_service, app.name AS application,
                   tc.name AS tech, tc.type AS type, tc.vendor AS vendor
            """,
            name=name,
        )
    if layer == "BusinessDomain":
        return run_query(
            """
            MATCH (bd:BusinessDomain {name:$name})-[:HAS_CAPABILITY]->(bc:BusinessCapability)
                  -[:REALIZED_BY]->(bs:BusinessService)
                  -[:SUPPORTS]->(app:Application)
                  -[:USES_DB|USES_MW]->(tc:TechnologyComponent)
            RETURN bc.name AS capability, bs.name AS business_service,
                   app.name AS application, tc.name AS tech, tc.type AS type
            """,
            name=name,
        )
    return []


def _infra_for(name: str, layer: str) -> list[dict]:
    """Return InfrastructureComponents reachable from ANY layer."""
    if layer == "TechnologyComponent":
        return get_infra_for_tech(name)
    if layer == "Application":
        return run_query(
            """
            MATCH (app:Application {name:$name})
                  -[:USES_DB|USES_MW]->(tc:TechnologyComponent)
                  -[:HOSTED_ON|CONNECTED_VIA]->(ic:InfrastructureComponent)
            RETURN tc.name AS tech, ic.name AS infra,
                   ic.type AS type, ic.env AS env
            """,
            name=name,
        )
    if layer == "BusinessService":
        return run_query(
            """
            MATCH (bs:BusinessService {name:$name})-[:SUPPORTS]->(app:Application)
                  -[:USES_DB|USES_MW]->(tc:TechnologyComponent)
                  -[:HOSTED_ON|CONNECTED_VIA]->(ic:InfrastructureComponent)
            RETURN app.name AS application, tc.name AS tech,
                   ic.name AS infra, ic.type AS type, ic.env AS env
            """,
            name=name,
        )
    if layer == "BusinessCapability":
        return run_query(
            """
            MATCH (bc:BusinessCapability {name:$name})-[:REALIZED_BY]->(bs:BusinessService)
                  -[:SUPPORTS]->(app:Application)
                  -[:USES_DB|USES_MW]->(tc:TechnologyComponent)
                  -[:HOSTED_ON|CONNECTED_VIA]->(ic:InfrastructureComponent)
            RETURN bs.name AS business_service, app.name AS application,
                   tc.name AS tech, ic.name AS infra, ic.env AS env
            """,
            name=name,
        )
    if layer == "BusinessDomain":
        return run_query(
            """
            MATCH (bd:BusinessDomain {name:$name})-[:HAS_CAPABILITY]->(bc:BusinessCapability)
                  -[:REALIZED_BY]->(bs:BusinessService)
                  -[:SUPPORTS]->(app:Application)
                  -[:USES_DB|USES_MW]->(tc:TechnologyComponent)
                  -[:HOSTED_ON|CONNECTED_VIA]->(ic:InfrastructureComponent)
            RETURN bc.name AS capability, bs.name AS business_service,
                   tc.name AS tech, ic.name AS infra, ic.env AS env
            """,
            name=name,
        )
    return []


def _applications_for(name: str, layer: str) -> list[dict]:
    """Return Applications reachable from TechnologyComponent, BusinessService, or Capability."""
    if layer == "TechnologyComponent":
        return run_query(
            """
            MATCH (app:Application)-[:USES_DB|USES_MW]->(tc:TechnologyComponent {name:$name})
            RETURN app.name AS name, app.vendor AS vendor, app.type AS type
            """,
            name=name,
        )
    if layer == "BusinessService":
        return run_query(
            """
            MATCH (bs:BusinessService {name:$name})-[:SUPPORTS]->(app:Application)
            RETURN app.name AS application, app.vendor AS vendor, app.type AS app_type
            """,
            name=name,
        )
    if layer == "BusinessCapability":
        return run_query(
            """
            MATCH (bc:BusinessCapability {name:$name})-[:REALIZED_BY]->(bs:BusinessService)
                  -[:SUPPORTS]->(app:Application)
            RETURN bs.name AS business_service,
                   app.name AS application, app.vendor AS vendor
            """,
            name=name,
        )
    return []


# ── 7.4  Intent extraction ────────────────────────────────────────────────────

_INTENT_PROMPT = """
You extract intent and entities from questions about a Retail IT Knowledge Graph (6 layers):
  BusinessDomain → BusinessCapability → BusinessService
  → Application → TechnologyComponent → InfrastructureComponent

Return ONLY valid JSON with these fields:
- intent: one of the values listed below
- primary_entity: main subject (copy exact words from question)
- entities: all entity names mentioned

Intent values:
  blast_radius      → X fails/crashes/goes down → what business impact?
  full_chain        → show everything / full path / end-to-end for X
  list_down         → what does X have/contain? (capabilities, services, apps, tech, infra)
  list_up           → what higher layer does X belong to / feed into?
  list_applications → what applications support X (X can be any layer)
  list_tech         → what tech/databases/middleware does X use
  list_infra        → what servers/infrastructure host X
  impact_analysis   → what is the revenue/business impact of X
  critical_services → most critical / highest risk / highest revenue loss services
  general_search    → anything else

Examples:
  "what applications are available for back office store operations" → list_applications, Back Office Store Operations
  "what applications support POS Transaction Processing"            → list_applications, POS Transaction Processing
  "what breaks if DB-Server-01 crashes"                            → blast_radius, DB-Server-01
  "what capabilities does Store Operations have"                   → list_down, Store Operations
  "what services does Sales & Checkout Management have"            → list_down, Sales & Checkout Management
  "what tech does POS Application use"                             → list_tech, POS Application
  "what infra hosts Oracle DB"                                     → list_infra, Oracle DB
  "what applications use Kafka"                                    → list_applications, Kafka
  "what domain does POS Transaction Processing belong to"          → list_up, POS Transaction Processing
  "show everything about Store Reporting Service"                  → full_chain, Store Reporting Service
  "what is the revenue impact if POS Transaction Processing fails" → impact_analysis, POS Transaction Processing
  "which infrastructure supports Oracle DB"                        → list_infra, Oracle DB
  "what are the most critical services"                            → critical_services
"""


def extract_intent(question: str, history: list | None = None) -> dict:
    """
    Call the LLM to extract structured intent + entities from a natural-language question.
    Up to 3 prior turns are included for context.
    Returns a dict with keys: intent, primary_entity, entities.
    """
    client = get_groq_client()
    msgs = [{"role": "system", "content": _INTENT_PROMPT}]

    if history:
        for t in history[-3:]:
            msgs.append({"role": "user",      "content": t["question"]})
            msgs.append({"role": "assistant",  "content": t.get("intent_summary", "")})

    msgs.append({"role": "user", "content": question})

    raw = client.chat.completions.create(
        model=GROQ_MODEL, messages=msgs, temperature=0.05, max_tokens=300
    ).choices[0].message.content.strip()

    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"intent": "general_search", "primary_entity": "", "entities": []}


# ── 7.5  Smart router ─────────────────────────────────────────────────────────

def fetch_graph_data(ir: dict) -> list[dict]:
    """
    Route an intent result (from extract_intent) to the correct graph query.
    Mutates ir to add resolved_layer.
    Returns a (possibly empty) list of graph records.
    """
    intent = ir.get("intent", "general_search")
    entity, layer = resolve_entity(ir.get("primary_entity", ""))
    ir["primary_entity"]  = entity
    ir["resolved_layer"]  = layer

    if intent == "blast_radius":
        if layer == "InfrastructureComponent": return get_blast_radius(entity)
        if layer == "TechnologyComponent":     return _up(entity, layer)
        return _up(entity, layer) or search_nodes(entity)

    if intent == "full_chain":
        return _full_chain(entity, layer) or search_nodes(entity)

    if intent == "list_down":
        return _down(entity, layer) or search_nodes(entity)

    if intent == "list_up":
        return _up(entity, layer) or search_nodes(entity)

    if intent == "list_applications":
        return _applications_for_layer(entity, layer) or search_nodes(entity)

    if intent == "list_tech":
        return _tech_for(entity, layer) or search_nodes(entity)

    if intent == "list_infra":
        return _infra_for(entity, layer) or search_nodes(entity)

    if intent == "impact_analysis":
        if layer == "BusinessService":
            return get_impact_for_service(entity)
        if layer in ("InfrastructureComponent", "TechnologyComponent"):
            return _up(entity, layer)
        return get_impact_for_service(entity) or _up(entity, layer)

    if intent == "critical_services":
        return get_critical_services()

    # general_search — auto-route by resolved layer
    q, ql = entity, layer
    if not q:
        raw_ents = ir.get("entities", [])
        if raw_ents:
            q, ql = resolve_entity(raw_ents[0])

    if ql == "InfrastructureComponent": return get_blast_radius(q)
    if ql == "TechnologyComponent":     return _up(q, ql)
    if ql == "BusinessService":         return _full_chain(q, ql)
    if ql == "BusinessCapability":      return get_services_for_capability(q)
    if ql == "BusinessDomain":          return get_capabilities_for_domain(q)
    if ql == "Application":             return get_tech_for_application(q)
    return search_nodes(q) if q else []


# ── 7.6  LLM explanation ──────────────────────────────────────────────────────

_EXPLANATION_PROMPT = """
You are a senior enterprise architect for a large retail company.
You answer questions about a 6-layer Retail IT Knowledge Graph.

LAYER ORDER (Layer 1 = top/business, Layer 6 = bottom/infrastructure):
  Layer 1: BusinessDomain          (e.g. Store Operations)
  Layer 2: BusinessCapability      (e.g. Sales & Checkout Management)
  Layer 3: BusinessService         (e.g. POS Transaction Processing)
  Layer 4: Application             (e.g. POS Application)
  Layer 5: TechnologyComponent     (e.g. Oracle DB)
  Layer 6: InfrastructureComponent (e.g. DB-Server-01)

For blast_radius queries (e.g. "what happens if DB-Server-01 fails"):
- DB-Server-01 is Layer 6 (the BOTTOM, infrastructure)
- The blast radius travels UPWARD: Infra → Tech → App → BusinessService → Capability → Domain
- BusinessService is Layer 3, NOT the top — always clarify this
- The TOP-MOST affected layer should be BusinessDomain (Layer 1) or BusinessCapability (Layer 2)
- Never call BusinessService the "top-most" layer

Rules:
- Always state layer numbers correctly using the order above
- Be specific: name actual services, apps, infrastructure from the data
- Use bullet points for lists
- ONLY mention revenue if revenueLossPerHour is explicitly in the graph data
- Do NOT invent any facts not in the provided graph data
- Keep response under 450 words
- End with a short recommendation where useful
"""


def explain_with_llm(
    question: str,
    graph_data: list[dict],
    ir: dict,
    history: list | None = None,
) -> str:
    """
    Generate a business-friendly explanation of graph_data using the LLM.
    Returns a plain-text (markdown) string.
    """
    if not graph_data:
        e    = ir.get("primary_entity", "the requested entity")
        lyr  = ir.get("resolved_layer", "")
        hint = f" (resolved layer: {lyr})" if lyr else ""
        return (
            f"⚠️ No graph data found for **{e}**{hint}. "
            "The entity may not exist in the graph or has no connections at this layer. "
            "Try the Hierarchy Explorer or Cypher Playground to verify."
        )

    client = get_groq_client()
    content = (
        f"Question: {question}\n"
        f"Intent: {ir.get('intent')} | "
        f"Entity: {ir.get('primary_entity')} [{ir.get('resolved_layer', '')}]\n\n"
        f"Graph data ({len(graph_data)} records):\n"
        f"{json.dumps(graph_data[:60], indent=2)}\n\n"
        "Answer using only the graph data above."
    )

    msgs = [{"role": "system", "content": _EXPLANATION_PROMPT}]
    if history:
        for t in history[-4:]:
            msgs.append({"role": "user",      "content": t["question"]})
            msgs.append({"role": "assistant",  "content": t["answer"]})
    msgs.append({"role": "user", "content": content})

    return client.chat.completions.create(
        model=GROQ_MODEL, messages=msgs, temperature=0.3, max_tokens=900
    ).choices[0].message.content.strip()


# ── 7.7  Main pipeline ────────────────────────────────────────────────────────

def answer_question(question: str, history: list | None = None) -> dict:
    """
    Full NL → graph → LLM pipeline.

    Steps:
      1. extract_intent  — LLM classifies question intent + entity
      2. fetch_graph_data — routes to the correct Neo4j query
      3. explain_with_llm — LLM generates a business-friendly explanation

    Returns:
      {
        "intent_result":  dict,
        "graph_data":     list[dict],
        "explanation":    str,
        "intent_summary": str,   ← compact string for chat history
      }
    """
    ir          = extract_intent(question, history)
    graph_data  = fetch_graph_data(ir)
    explanation = explain_with_llm(question, graph_data, ir, history)
    return {
        "intent_result":  ir,
        "graph_data":     graph_data,
        "explanation":    explanation,
        "intent_summary": (
            f"intent={ir.get('intent')} "
            f"entity={ir.get('primary_entity')} "
            f"layer={ir.get('resolved_layer', '?')}"
        ),
    }


# ── 7.8  Cypher generation (custom playground) ───────────────────────────────

_CYPHER_PROMPT = """
Neo4j Cypher expert for Retail Knowledge Graph.

Nodes:
  BusinessDomain, BusinessCapability, BusinessService,
  Application, TechnologyComponent, InfrastructureComponent, Impact

Relationships:
  (BusinessDomain)-[:HAS_CAPABILITY]->(BusinessCapability)
  (BusinessCapability)-[:REALIZED_BY]->(BusinessService)
  (BusinessService)-[:SUPPORTS]->(Application)
  (Application)-[:USES_DB|USES_MW]->(TechnologyComponent)
  (TechnologyComponent)-[:HOSTED_ON|CONNECTED_VIA]->(InfrastructureComponent)
  (BusinessService)-[:HAS_IMPACT]->(Impact)

Return ONLY the Cypher query — no markdown, no explanation.
"""


def generate_cypher(question: str) -> str:
    """Ask the LLM to generate a Cypher query from a natural-language description."""
    client = get_groq_client()
    return client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": _CYPHER_PROMPT},
            {"role": "user",   "content": question},
        ],
        temperature=0.1,
        max_tokens=400,
    ).choices[0].message.content.strip()


def run_custom_cypher(cypher: str) -> list[dict]:
    """Execute an arbitrary Cypher query and return results as plain dicts."""
    return run_query(cypher)
