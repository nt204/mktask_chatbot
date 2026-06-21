from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

qdrant = QdrantClient(host="localhost", port=6333)
count = qdrant.count(
    collection_name="project_documents",
    count_filter=Filter(
        must=[
            FieldCondition(key="project_id", match=MatchValue(value="5225e865-d5dc-4d9c-a75c-de93c8671dab"))
        ]
    )
)
print(count)
