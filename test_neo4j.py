from neo4j import GraphDatabase

# Connection details for your local Docker instance
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "password123")

def run_query():
    # The driver object manages a pool of persistent network connections (sockets).
    # Creating a driver is resource-heavy, so you create it once and reuse it.
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        
        # A session is a lightweight, cheap lease of a network socket.
        # You open a session, execute your queries, and close it immediately.
        with driver.session() as session:
            
            query = """
            MATCH (t:Task)
            RETURN t.id AS id, t.title AS title, t.complexity AS complexity
            """
            
            result = session.run(query)
            
            print("\n--- Tasks in local Neo4j ---")
            for record in result:
                print(f"ID: {record['id']} | Title: {record['title']} | Complexity: {record['complexity']}")
            print("----------------------------\n")

if __name__ == "__main__":
    run_query()