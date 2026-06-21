from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

qdrant = QdrantClient(host="localhost", port=6333)
COLLECTION_NAME = "project_documents"
qdrant.delete_collection(collection_name=COLLECTION_NAME)
qdrant.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
)
print("Recreated Qdrant collection with dim 3072")
