"""
seed_graph.py
=============
Seeds the Neo4j knowledge graph with the 6-layer retail hierarchy:
  BusinessDomain → BusinessCapability → BusinessService
  → Application → TechnologyComponent → InfrastructureComponent

Run:  python data/seed_graph.py
"""

from neo4j import GraphDatabase
import os

NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "retail@123")


# ─────────────────────────────────────────────────────────────────────────────
# DATA DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

BUSINESS_DOMAINS = [
    {"name": "Store Operations",         "portfolio": "CUSTOMER / REVENUE"},
    {"name": "Merchandising",            "portfolio": "CUSTOMER / REVENUE"},
    {"name": "Supply Chain",             "portfolio": "SUPPLY CHAIN"},
    {"name": "Order Management",         "portfolio": "SUPPLY CHAIN"},
    {"name": "Finance",                  "portfolio": "CORPORATE SUPPORT"},
    {"name": "HR",                       "portfolio": "CORPORATE SUPPORT"},
    {"name": "Data & Analytics",         "portfolio": "TECH & DATA"},
]

BUSINESS_CAPABILITIES = [
    # Store Operations L1
    {"name": "Sales & Checkout Management",       "domain": "Store Operations", "level": "L1"},
    {"name": "Cash & Financial Control",          "domain": "Store Operations", "level": "L1"},
    {"name": "Store Inventory Management",        "domain": "Store Operations", "level": "L1"},
    {"name": "Store Workforce Management",        "domain": "Store Operations", "level": "L1"},
    {"name": "Store Merchandising Execution",     "domain": "Store Operations", "level": "L1"},
    {"name": "Customer Service & Experience",     "domain": "Store Operations", "level": "L1"},
    {"name": "Store Operations Control",          "domain": "Store Operations", "level": "L1"},
    {"name": "Store IT & Device Operations",      "domain": "Store Operations", "level": "L1"},
    {"name": "Back Office Store Operations",      "domain": "Store Operations", "level": "L1"},
    {"name": "Omnichannel Store Fulfilment",      "domain": "Store Operations", "level": "L1"},
    {"name": "Store Performance & Monitoring",    "domain": "Store Operations", "level": "L1"},
    # Other domains
    {"name": "Payment Authorization",             "domain": "Merchandising",   "level": "L1"},
    {"name": "Customer Onboarding",               "domain": "Merchandising",   "level": "L1"},
    {"name": "Inventory Planning",                "domain": "Supply Chain",    "level": "L1"},
    {"name": "Order Processing",                  "domain": "Order Management","level": "L1"},
]

BUSINESS_SERVICES = [
    # Sales & Checkout
    {"name": "POS Transaction Processing",        "capability": "Sales & Checkout Management",    "criticality": "High"},
    {"name": "Payment Processing Service",        "capability": "Sales & Checkout Management",    "criticality": "High"},
    {"name": "Receipt & Invoice Management",      "capability": "Sales & Checkout Management",    "criticality": "Medium"},
    {"name": "Promotion & Discount Execution",    "capability": "Sales & Checkout Management",    "criticality": "Medium"},
    {"name": "Tax Calculation Service",           "capability": "Sales & Checkout Management",    "criticality": "High"},
    # Cash & Financial
    {"name": "Cash Till Management",              "capability": "Cash & Financial Control",       "criticality": "High"},
    {"name": "Cash Counting & Balancing",         "capability": "Cash & Financial Control",       "criticality": "High"},
    {"name": "Deposit Preparation & Banking",     "capability": "Cash & Financial Control",       "criticality": "Medium"},
    {"name": "Fraud & Loss Prevention Monitoring","capability": "Cash & Financial Control",       "criticality": "High"},
    # Inventory
    {"name": "Stock Receiving Service",           "capability": "Store Inventory Management",     "criticality": "High"},
    {"name": "Shelf Replenishment Service",       "capability": "Store Inventory Management",     "criticality": "Medium"},
    {"name": "Inventory Counting Service",        "capability": "Store Inventory Management",     "criticality": "Medium"},
    {"name": "Stock Adjustment Service",          "capability": "Store Inventory Management",     "criticality": "Medium"},
    {"name": "Inter-Store Transfer Service",      "capability": "Store Inventory Management",     "criticality": "Low"},
    # Workforce
    {"name": "Scheduling & Rostering Service",    "capability": "Store Workforce Management",     "criticality": "Medium"},
    {"name": "Attendance & Time Tracking",        "capability": "Store Workforce Management",     "criticality": "Medium"},
    {"name": "Task Assignment & Monitoring",      "capability": "Store Workforce Management",     "criticality": "Low"},
    # Merchandising Execution
    {"name": "Planogram Execution Service",       "capability": "Store Merchandising Execution",  "criticality": "Medium"},
    {"name": "Price Labeling & Update Service",   "capability": "Store Merchandising Execution",  "criticality": "High"},
    {"name": "Visual Merchandising Audit",        "capability": "Store Merchandising Execution",  "criticality": "Low"},
    # Customer Service
    {"name": "Customer Assistance Service",       "capability": "Customer Service & Experience",  "criticality": "High"},
    {"name": "Returns & Refund Handling",         "capability": "Customer Service & Experience",  "criticality": "High"},
    {"name": "Loyalty Program Service",           "capability": "Customer Service & Experience",  "criticality": "Medium"},
    # Store IT
    {"name": "POS Terminal Management",           "capability": "Store IT & Device Operations",   "criticality": "High"},
    {"name": "Handheld Device Management",        "capability": "Store IT & Device Operations",   "criticality": "Medium"},
    {"name": "Store Network Monitoring",          "capability": "Store IT & Device Operations",   "criticality": "High"},
    {"name": "Device Software Deployment",        "capability": "Store IT & Device Operations",   "criticality": "Medium"},
    # Back Office
    {"name": "Day-End Processing",                "capability": "Back Office Store Operations",   "criticality": "High"},
    {"name": "Back Office Batch Execution",       "capability": "Back Office Store Operations",   "criticality": "High"},
    {"name": "Data Sync Service",                 "capability": "Back Office Store Operations",   "criticality": "High"},
    {"name": "Store Reporting Service",           "capability": "Back Office Store Operations",   "criticality": "Medium"},
    # Omnichannel
    {"name": "Click & Collect Service (BOPIS)",   "capability": "Omnichannel Store Fulfilment",   "criticality": "High"},
    {"name": "Ship-from-Store Service",           "capability": "Omnichannel Store Fulfilment",   "criticality": "High"},
    {"name": "Online Returns Processing",         "capability": "Omnichannel Store Fulfilment",   "criticality": "Medium"},
    # Performance
    {"name": "Sales Performance Tracking",        "capability": "Store Performance & Monitoring", "criticality": "Medium"},
    {"name": "Store KPI Dashboard Service",       "capability": "Store Performance & Monitoring", "criticality": "Medium"},
    {"name": "Incident Tracking & Reporting",     "capability": "Store Performance & Monitoring", "criticality": "Medium"},
    # Other domains
    {"name": "Online Order Service",              "capability": "Order Processing",               "criticality": "High"},
    {"name": "Payment Validation Service",        "capability": "Payment Authorization",          "criticality": "High"},
]

APPLICATIONS = [
    {"name": "POS Application",              "vendor": "NCR",         "type": "POS",           "api_name": "POS API"},
    {"name": "Payment Gateway App",          "vendor": "Worldpay",    "type": "Payment",       "api_name": "Payment Gateway API"},
    {"name": "Tax Engine App",               "vendor": "Vertex",      "type": "Tax",           "api_name": "Tax Engine Service"},
    {"name": "Promotion Engine App",         "vendor": "In-house",    "type": "Promotion",     "api_name": "Promotion Engine API"},
    {"name": "Cash Office App",              "vendor": "In-house",    "type": "Finance",       "api_name": "Cash Management API"},
    {"name": "Fraud Detection App",          "vendor": "NICE",        "type": "Risk",          "api_name": "Fraud Detection API"},
    {"name": "Inventory Mgmt App (WMS)",     "vendor": "Manhattan",   "type": "WMS",           "api_name": "Inventory API"},
    {"name": "Workforce Mgmt App (WFM)",     "vendor": "Kronos",      "type": "WFM",           "api_name": "WFM Scheduling API"},
    {"name": "Planogram App",                "vendor": "JDA",         "type": "Merchandising", "api_name": "Planogram API"},
    {"name": "Price Mgmt App",               "vendor": "In-house",    "type": "Pricing",       "api_name": "Price Management API"},
    {"name": "CRM & Loyalty App",            "vendor": "Salesforce",  "type": "CRM",           "api_name": "CRM Loyalty API"},
    {"name": "MDM / Device Mgmt App",        "vendor": "JAMF",        "type": "MDM",           "api_name": "Device Mgmt API"},
    {"name": "Network Monitoring App",       "vendor": "Nagios",      "type": "Monitoring",    "api_name": "Network Monitoring API"},
    {"name": "Batch Scheduler App",          "vendor": "Control-M",   "type": "Scheduler",     "api_name": "Batch Orchestration Service"},
    {"name": "Data Integration Platform",    "vendor": "MuleSoft",    "type": "Integration",   "api_name": "Data Sync API"},
    {"name": "Reporting & BI App",           "vendor": "Tableau",     "type": "BI",            "api_name": "Reporting API"},
    {"name": "OMS App",                      "vendor": "Manhattan",   "type": "OMS",           "api_name": "OMS Fulfilment API"},
    {"name": "OrderMgmtApp",                 "vendor": "In-house",    "type": "OMS",           "api_name": "Order API"},
]

# business_service → application mappings (direct connection in 6-layer)
BUSINESS_SERVICE_TO_APP = {
    "POS Transaction Processing":        "POS Application",
    "Payment Processing Service":        "Payment Gateway App",
    "Tax Calculation Service":           "Tax Engine App",
    "Promotion & Discount Execution":    "Promotion Engine App",
    "Cash Till Management":              "Cash Office App",
    "Fraud & Loss Prevention Monitoring":"Fraud Detection App",
    "Stock Receiving Service":           "Inventory Mgmt App (WMS)",
    "Scheduling & Rostering Service":    "Workforce Mgmt App (WFM)",
    "Planogram Execution Service":       "Planogram App",
    "Price Labeling & Update Service":   "Price Mgmt App",
    "Loyalty Program Service":           "CRM & Loyalty App",
    "Handheld Device Management":        "MDM / Device Mgmt App",
    "Store Network Monitoring":          "Network Monitoring App",
    "Back Office Batch Execution":       "Batch Scheduler App",
    "Data Sync Service":                 "Data Integration Platform",
    "Store Reporting Service":           "Reporting & BI App",
    "Ship-from-Store Service":           "OMS App",
    "Click & Collect Service (BOPIS)":   "OMS App",
    "Store KPI Dashboard Service":       "Reporting & BI App",
    "Online Order Service":              "OrderMgmtApp",
}

TECHNOLOGY_COMPONENTS = [
    # Middleware
    {"name": "Kafka",            "type": "Middleware",  "vendor": "Confluent"},
    {"name": "NGINX",            "type": "Middleware",  "vendor": "NGINX Inc"},
    {"name": "WebSphere MQ",     "type": "Middleware",  "vendor": "IBM"},
    {"name": "Redis Cache",      "type": "Middleware",  "vendor": "Redis Labs"},
    # Databases
    {"name": "Oracle DB",        "type": "Database",    "vendor": "Oracle"},
    {"name": "MongoDB",          "type": "Database",    "vendor": "MongoDB Inc"},
    {"name": "PostgreSQL",       "type": "Database",    "vendor": "Open Source"},
    {"name": "MySQL",            "type": "Database",    "vendor": "Oracle"},
]

# application → tech component mappings
APP_TO_TECH = {
    "POS Application":           ["Oracle DB", "NGINX"],
    "Payment Gateway App":       ["Oracle DB", "NGINX", "Kafka"],
    "Tax Engine App":            ["PostgreSQL"],
    "Promotion Engine App":      ["MongoDB", "Redis Cache"],
    "Cash Office App":           ["Oracle DB"],
    "Fraud Detection App":       ["Kafka", "MongoDB"],
    "Inventory Mgmt App (WMS)":  ["Oracle DB", "WebSphere MQ"],
    "Workforce Mgmt App (WFM)":  ["MySQL"],
    "Planogram App":             ["PostgreSQL"],
    "Price Mgmt App":            ["MongoDB", "Redis Cache"],
    "CRM & Loyalty App":         ["Oracle DB", "Kafka"],
    "MDM / Device Mgmt App":     ["PostgreSQL"],
    "Network Monitoring App":    ["MySQL"],
    "Batch Scheduler App":       ["Oracle DB"],
    "Data Integration Platform": ["Kafka", "MongoDB"],
    "Reporting & BI App":        ["Oracle DB", "MongoDB"],
    "OMS App":                   ["Oracle DB", "Kafka"],
    "OrderMgmtApp":              ["Oracle DB"],
}

INFRA_COMPONENTS = [
    # Compute Servers
    {"name": "POS-Server-01",       "type": "Compute",   "env": "On-Premise"},
    {"name": "App-Server-01",       "type": "Compute",   "env": "On-Premise"},
    {"name": "App-Server-02",       "type": "Compute",   "env": "On-Premise"},
    {"name": "K8s-Node-01",         "type": "Compute",   "env": "Cloud"},
    {"name": "K8s-Node-02",         "type": "Compute",   "env": "Cloud"},
    # Database Servers
    {"name": "DB-Server-01",        "type": "Database",  "env": "On-Premise"},
    {"name": "DB-Server-02",        "type": "Database",  "env": "Cloud"},
    {"name": "DB-Server-03",        "type": "Database",  "env": "On-Premise"},
    {"name": "DB-Server-04",        "type": "Database",  "env": "Cloud"},
    {"name": "DB-Server-05",        "type": "Database",  "env": "On-Premise"},
    {"name": "DB-Server-07",        "type": "Database",  "env": "On-Premise"},
    # Network Components
    {"name": "Load-Balancer-01",    "type": "Network",   "env": "On-Premise"},
    {"name": "Firewall-01",         "type": "Network",   "env": "On-Premise"},
    {"name": "CDN-Edge",            "type": "Network",   "env": "Cloud"},
]

# tech component → infra mappings (proper DB server mapping)
TECH_TO_INFRA = {
    "Oracle DB":    ["DB-Server-01", "DB-Server-03"],
    "MongoDB":      ["DB-Server-02", "DB-Server-04"],
    "PostgreSQL":   ["DB-Server-05"],
    "MySQL":        ["DB-Server-07"],
    "Kafka":        ["K8s-Node-01", "K8s-Node-02"],
    "NGINX":        ["App-Server-01", "Load-Balancer-01"],
    "WebSphere MQ": ["App-Server-02"],
    "Redis Cache":  ["K8s-Node-01"],
}

IMPACTS = [
    {"service": "POS Transaction Processing",        "severity": "Critical", "revenue_loss_per_hour": "₹50L", "customer_impact": "High",   "regulatory": "Medium"},
    {"service": "Payment Processing Service",        "severity": "Critical", "revenue_loss_per_hour": "₹40L", "customer_impact": "High",   "regulatory": "High"},
    {"service": "Tax Calculation Service",           "severity": "High",     "revenue_loss_per_hour": "₹10L", "customer_impact": "Medium", "regulatory": "High"},
    {"service": "Cash Till Management",              "severity": "High",     "revenue_loss_per_hour": "₹20L", "customer_impact": "Medium", "regulatory": "Medium"},
    {"service": "Fraud & Loss Prevention Monitoring","severity": "High",     "revenue_loss_per_hour": "₹15L", "customer_impact": "Low",    "regulatory": "High"},
    {"service": "Stock Receiving Service",           "severity": "Medium",   "revenue_loss_per_hour": "₹5L",  "customer_impact": "Medium", "regulatory": "Low"},
    {"service": "Click & Collect Service (BOPIS)",   "severity": "High",     "revenue_loss_per_hour": "₹25L", "customer_impact": "High",   "regulatory": "Low"},
    {"service": "Day-End Processing",                "severity": "High",     "revenue_loss_per_hour": "₹30L", "customer_impact": "Low",    "regulatory": "High"},
    {"service": "Data Sync Service",                 "severity": "High",     "revenue_loss_per_hour": "₹20L", "customer_impact": "Medium", "regulatory": "Medium"},
    {"service": "Loyalty Program Service",           "severity": "Medium",   "revenue_loss_per_hour": "₹8L",  "customer_impact": "High",   "regulatory": "Low"},
]


# ─────────────────────────────────────────────────────────────────────────────
# SEEDER
# ─────────────────────────────────────────────────────────────────────────────

def clear_graph(tx):
    tx.run("MATCH (n) DETACH DELETE n")

def create_constraints(driver):
    with driver.session() as session:
        constraints = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:BusinessDomain)        REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:BusinessCapability)    REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:BusinessService)       REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Application)           REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:TechnologyComponent)   REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:InfrastructureComponent) REQUIRE n.name IS UNIQUE",
        ]
        for c in constraints:
            session.run(c)

def seed(tx):
    # 1. Business Domains
    for d in BUSINESS_DOMAINS:
        tx.run(
            "MERGE (n:BusinessDomain {name:$name}) SET n.portfolio=$portfolio",
            **d
        )

    # 2. Business Capabilities + HAS_CAPABILITY
    for c in BUSINESS_CAPABILITIES:
        tx.run(
            "MERGE (n:BusinessCapability {name:$name}) SET n.level=$level",
            name=c["name"], level=c["level"]
        )
        tx.run(
            """
            MATCH (d:BusinessDomain {name:$domain})
            MATCH (c:BusinessCapability {name:$cap})
            MERGE (d)-[:HAS_CAPABILITY]->(c)
            """,
            domain=c["domain"], cap=c["name"]
        )

    # 3. Business Services + REALIZED_BY
    for s in BUSINESS_SERVICES:
        tx.run(
            "MERGE (n:BusinessService {name:$name}) SET n.criticality=$criticality",
            name=s["name"], criticality=s["criticality"]
        )
        tx.run(
            """
            MATCH (c:BusinessCapability {name:$cap})
            MATCH (s:BusinessService {name:$svc})
            MERGE (c)-[:REALIZED_BY {criticality:$criticality}]->(s)
            """,
            cap=s["capability"], svc=s["name"], criticality=s["criticality"]
        )

    # 4. Applications
    for app in APPLICATIONS:
        tx.run(
            "MERGE (n:Application {name:$name}) SET n.vendor=$vendor, n.type=$type, n.api_name=$api_name",
            **app
        )

    # 5. BusinessService SUPPORTS Application (direct connection - 6 layers)
    for svc_name, app_name in BUSINESS_SERVICE_TO_APP.items():
        tx.run(
            """
            MATCH (s:BusinessService {name:$svc})
            MATCH (a:Application {name:$app})
            MERGE (s)-[:SUPPORTS]->(a)
            """,
            svc=svc_name, app=app_name
        )

    # 6. Technology Components
    for t in TECHNOLOGY_COMPONENTS:
        tx.run(
            "MERGE (n:TechnologyComponent {name:$name}) SET n.type=$type, n.vendor=$vendor",
            **t
        )

    # 7. Application USES_DB / USES_MW
    for app_name, tech_list in APP_TO_TECH.items():
        for tech_name in tech_list:
            tech = next((t for t in TECHNOLOGY_COMPONENTS if t["name"] == tech_name), None)
            rel = "USES_DB" if tech and tech["type"] == "Database" else "USES_MW"
            tx.run(
                f"""
                MATCH (a:Application {{name:$app}})
                MATCH (t:TechnologyComponent {{name:$tech}})
                MERGE (a)-[:{rel}]->(t)
                """,
                app=app_name, tech=tech_name
            )

    # 8. Infrastructure Components
    for i in INFRA_COMPONENTS:
        tx.run(
            "MERGE (n:InfrastructureComponent {name:$name}) SET n.type=$type, n.env=$env",
            **i
        )

    # 9. TechComponent HOSTED_ON Infra
    for tech_name, infra_list in TECH_TO_INFRA.items():
        for infra_name in infra_list:
            infra = next((i for i in INFRA_COMPONENTS if i["name"] == infra_name), None)
            rel = "HOSTED_ON" if infra and infra["type"] in ("Compute", "Database") else "CONNECTED_VIA"
            tx.run(
                f"""
                MATCH (t:TechnologyComponent {{name:$tech}})
                MATCH (i:InfrastructureComponent {{name:$infra}})
                MERGE (t)-[:{rel}]->(i)
                """,
                tech=tech_name, infra=infra_name
            )

    # 10. Impact Nodes + HAS_IMPACT
    for imp in IMPACTS:
        tx.run(
            """
            MATCH (s:BusinessService {name:$service})
            MERGE (im:Impact {service:$service})
            SET im.severity=$severity,
                im.revenueLossPerHour=$revenue_loss_per_hour,
                im.customerImpact=$customer_impact,
                im.regulatoryImpact=$regulatory
            MERGE (s)-[:HAS_IMPACT]->(im)
            """,
            **imp
        )

    print("✅ Graph seeded successfully.")


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    print("🔌 Connected to Neo4j")
    create_constraints(driver)
    with driver.session() as session:
        session.execute_write(clear_graph)
        session.execute_write(seed)
    driver.close()
    print("🎉 Done! Open Neo4j Browser → run: MATCH (n) RETURN n LIMIT 100")


if __name__ == "__main__":
    main()
