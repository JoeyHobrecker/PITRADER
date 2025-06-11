import json, logging, os
from typing import List
import weaviate
from weaviate.auth import AuthApiKey
from weaviate.util import generate_uuid5

COLLECTION = os.environ.get("WEAVIATE_COLLECTION_NAME", "TradingMemories")
_client = None
def client():
    global _client
    if _client is None:
        _client = weaviate.connect_to_wcs(
            cluster_url=os.environ["WEAVIATE_URL"],
            auth_credentials=AuthApiKey(os.environ["WEAVIATE_API_KEY"]),
        )
        if not _client.collections.exists(COLLECTION):
            _client.collections.create(
                name=COLLECTION,
                vectorizer_config=weaviate.classes.config.Configure.Vectorizer.text2vec_openai(),
            )
    return _client

def store(doc_id: str, text: str):
    client().collections.get(COLLECTION).data.insert(
        uuid=generate_uuid5(doc_id), properties={"content": text}
    )

def query(q: str, top_k: int = 5) -> List[str]:
    res = client().collections.get(COLLECTION).query.near_text(query=q, limit=top_k)
    return [o.properties["content"] for o in res.objects]
