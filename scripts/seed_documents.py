
from app.database import get_connection
from app.embeddings import generate_embedding

from pgvector.psycopg import register_vector


DOCUMENTS = [
    "PostgreSQL is a powerful relational database.",
    "PostgreSQL is a relational database.",
    "Python is a popular programming language.",
    "The sun is shining on a beautiful day.",
]


def seed_documents():
    with get_connection() as connection:
        register_vector(connection)

        with connection.cursor() as cursor:
            for content in DOCUMENTS:
                print(f"Generating embedding: {content}")

                embedding = generate_embedding(
                    content,
                    task_type="RETRIEVAL_DOCUMENT",
                )

                cursor.execute(
                    """
                    SELECT id
                    FROM document_chunks
                    WHERE content = %s
                    LIMIT 1
                    """,
                    (content,),
                )

                existing = cursor.fetchone()

                if existing:
                    cursor.execute(
                        """
                        UPDATE document_chunks
                        SET embedding = %s
                        WHERE id = %s
                        """,
                        (embedding, existing[0]),
                    )
                    print(f"Updated document ID: {existing[0]}")
                else:
                    cursor.execute(
                        """
                        INSERT INTO document_chunks (content, embedding)
                        VALUES (%s, %s)
                        RETURNING id
                        """,
                        (content, embedding),
                    )
                    new_id = cursor.fetchone()[0]
                    print(f"Inserted document ID: {new_id}")

    print("\nDocument embedding process completed!")


if __name__ == "__main__":
    seed_documents()
