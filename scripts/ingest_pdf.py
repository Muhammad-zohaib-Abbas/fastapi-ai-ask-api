
import sys
from pathlib import Path

from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb

from app.database import get_connection
from app.documents import extract_pdf_pages, split_text_into_chunks
from app.embeddings import generate_embedding


def ingest_pdf(pdf_path: str) -> None:
    path = Path(pdf_path)

    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Please provide a PDF file.")

    pages = extract_pdf_pages(str(path))

    if not pages:
        raise ValueError(
            "No extractable text found. The PDF may be scanned "
            "or contain images instead of selectable text."
        )

    total_chunks = 0

    # The database transaction commits only if the entire
    # ingestion succeeds. Errors roll back its database changes.
    with get_connection() as connection:
        register_vector(connection)

        with connection.cursor() as cursor:
            for page in pages:
                cursor.execute(
                    """
                    INSERT INTO documents
                        (document_name, page_number, content)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (
                        path.name,
                        page["page_number"],
                        page["content"],
                    ),
                )

                document_id = cursor.fetchone()[0]

                chunks = split_text_into_chunks(page["content"])

                for chunk_index, chunk in enumerate(chunks, start=1):
                    print(
                        f"Embedding page {page['page_number']}, "
                        f"chunk {chunk_index}..."
                    )

                    embedding = generate_embedding(
                        chunk,
                        task_type="RETRIEVAL_DOCUMENT",
                    )

                    metadata = {
                        "source": path.name,
                        "page_number": page["page_number"],
                        "chunk_index": chunk_index,
                    }

                    cursor.execute(
                        """
                        INSERT INTO document_chunks
                            (document_id, content, metadata, embedding)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            document_id,
                            chunk,
                            Jsonb(metadata),
                            Vector(embedding),
                        ),
                    )

                    total_chunks += 1

    print("\nPDF ingestion completed successfully!")
    print(f"File: {path.name}")
    print(f"Pages with extractable text: {len(pages)}")
    print(f"Chunks stored: {total_chunks}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            'Usage: python -m scripts.ingest_pdf "path\\to\\file.pdf"'
        )
        sys.exit(1)

    try:
        ingest_pdf(sys.argv[1])
    except Exception as error:
        print(f"\nPDF ingestion failed: {error}")
        sys.exit(1)
