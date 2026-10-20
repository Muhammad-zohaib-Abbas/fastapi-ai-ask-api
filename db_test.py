import psycopg

conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="rag_database",
    user="postgres",
    password="admin"
)

print("Connected to PostgreSQL!")


# with conn.cursor() as cur:
#     cur.execute(
#         """
#         INSERT INTO document_chunks (content, metadata, embedding)
#         VALUES (%s, %s, %s)
#         """,
#         (
#             "PostgreSQL is a powerful relational database.",
#             '{"source": "test"}',
#             [0.1] * 768
#         )
#     )

with conn.cursor() as cur:
    data = cur.execute(
        """
        select * from document_chunks
        """
    )

    rows = cur.fetchall()
    # print(rows)

    for row in rows:
        print(f"ID: {row[0]}")
        print(f"Content: {row[1]}")
        print(f"Metadata: {row[2]}")
        print(f"Embedding: {row[3]}")
        print("-" * 50)

conn.commit()
conn.close()

print("Vector inserted successfully!")