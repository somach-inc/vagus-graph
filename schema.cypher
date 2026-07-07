CREATE CONSTRAINT task_id_unique IF NOT EXISTS
FOR (task:Task)
REQUIRE task.id IS UNIQUE;

CREATE CONSTRAINT domain_name_unique IF NOT EXISTS
FOR (domain:Domain)
REQUIRE domain.name IS UNIQUE;

MERGE (strategy:Domain {name: "Strategy"})
MERGE (engineering:Domain {name: "Engineering"})
MERGE (operations:Domain {name: "Operations"});

MERGE (recover:Task {
    id: "task-low-001",
    title: "Review recovery checklist",
    complexity: "low",
    status: "open"
})
MERGE (focus:Task {
    id: "task-medium-001",
    title: "Refine Vagus Graph pipeline",
    complexity: "medium",
    status: "open"
})
MERGE (build:Task {
    id: "task-high-001",
    title: "Implement cognitive graph orchestration",
    complexity: "high",
    status: "open"
})
MERGE (prep:Task {
    id: "task-prep-001",
    title: "Prepare telemetry fixtures",
    complexity: "medium",
    status: "completed"
});

MERGE (recover)-[:REQUIRES_DOMAIN]->(operations)
MERGE (focus)-[:REQUIRES_DOMAIN]->(strategy)
MERGE (build)-[:REQUIRES_DOMAIN]->(engineering)
MERGE (prep)-[:REQUIRES_DOMAIN]->(engineering)
MERGE (prep)-[:BLOCKS]->(build);

MATCH (task:Task)
WHERE task.complexity = $current_energy
AND NOT EXISTS {
    MATCH (blocking:Task)-[:BLOCKS]->(task)
    WHERE NOT blocking.status = "completed"
}
RETURN task.id AS id, task.title AS title
LIMIT 1;
