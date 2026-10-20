
import psycopg
import json

conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="rag_database",
    user="postgres",
    password="admin"
)

documents = [
    {
        "content": "PostgreSQL is a relational database.",
        "metadata": {"source": "database"}
    },
    {
        "content": "Python is a popular programming language.",
        "metadata": {"source": "programming"}
    },
    {
        "content": "The sun is shining on a beautiful day.",
        "metadata": {"source": "weather"}
    }
]

with conn.cursor() as cur:
    for doc in documents:
        cur.execute(
            """
            INSERT INTO document_chunks (content, metadata, embedding)
            VALUES (%s, %s, %s)
            """,
            (
                doc["content"],
                json.dumps(doc["metadata"]),
                [0.0] * 768
            )
        )

conn.commit()
conn.close()

print("Test documents inserted!")
