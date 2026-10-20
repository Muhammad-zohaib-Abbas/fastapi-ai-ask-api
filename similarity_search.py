
import psycopg

conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="rag_database",
    user="postgres",
    password="admin"
)

query_vector = [0.1] * 768

with conn.cursor() as cur:
    cur.execute(
        """
        SELECT id, content,
               embedding <-> %s::vector AS distance
        FROM document_chunks
        ORDER BY embedding <-> %s::vector
        LIMIT 20
        """,
        (query_vector, query_vector)
    )

    for row in cur.fetchall():
        print(f"ID: {row[0]}")
        print(f"Content: {row[1]}")
        print(f"Distance: {row[2]}")
        print("-" * 40)

conn.close()
