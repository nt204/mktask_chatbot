from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

qdrant = QdrantClient(host="localhost", port=6333)
COLLECTION_NAME = "project_documents"

res = qdrant.scroll(
    collection_name=COLLECTION_NAME,
    scroll_filter=Filter(
        must=[
            FieldCondition(key="project_id", match=MatchValue(value="5225e865-d5dc-4d9c-a75c-de93c8671dab"))
        ]
    ),
    limit=5,
    with_payload=True,
    with_vectors=False
)

for p in res[0]:
    print(f"--- Chunk {p.payload.get('chunk_index')} ---")
    print(p.payload.get('text')[:200])
