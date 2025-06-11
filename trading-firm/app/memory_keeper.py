import json
import logging
import os
from typing import List, Optional

import weaviate
from weaviate.auth import AuthApiKey

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# --- CONFIGURATION ---
WEAVIATE_URL = os.environ.get("WEAVIATE_URL")
WEAVIATE_API_KEY = os.environ.get("WEAVIATE_API_KEY")
COLLECTION_NAME = os.environ.get("WEAVIATE_COLLECTION_NAME", "TradingMemories")

_client = None


def get_weaviate_client() -> weaviate.WeaviateClient:
    """Initializes and returns a Weaviate client singleton."""
    global _client
    if not WEAVIATE_URL or not WEAVIATE_API_KEY:
        raise ValueError(
            "WEAVIATE_URL and WEAVIATE_API_KEY environment variables must be set."
        )

    if _client is None:
        _client = weaviate.connect_to_wcs(
            cluster_url=WEAVIATE_URL, auth_credentials=AuthApiKey(WEAVIATE_API_KEY)
        )
        # Ensure the collection exists
        if not _client.collections.exists(COLLECTION_NAME):
            logging.info(
                f"Collection '{COLLECTION_NAME}' does not exist. Creating it now."
            )
            _client.collections.create(
                name=COLLECTION_NAME,
                # Using OpenAI's text2vec-openai model, assuming it's configured in the Weaviate cluster
                vectorizer_config=weaviate.classes.config.Configure.Vectorizer.text2vec_openai(),
            )
    return _client


def store(doc_id: str, text: str, metadata: Optional[dict] = None) -> None:
    """
    Stores or updates a document in the Weaviate vector store.
    Uses Weaviate's batching for efficiency.
    """
    client = get_weaviate_client()
    memories = client.collections.get(COLLECTION_NAME)

    properties = {"content": text}
    if metadata:
        properties.update(metadata)

    try:
        # Using `insert` which is equivalent to batch with a single object.
        # `uuid=doc_id` allows for upsert-like behavior based on a custom ID.
        # Note: Weaviate v4 requires a specific UUID format, so we hash the doc_id.
        from weaviate.util import generate_uuid5

        memories.data.insert(uuid=generate_uuid5(doc_id), properties=properties)
        logging.info(f"Stored document with ID hash for: {doc_id}")
    except Exception as e:
        logging.error(f"Failed to store document {doc_id} in Weaviate: {e}")


def query(query_text: str, top_k: int = 5) -> List[str]:
    """
    Queries the Weaviate vector store for relevant documents.
    """
    client = get_weaviate_client()
    memories = client.collections.get(COLLECTION_NAME)

    try:
        response = memories.query.near_text(query=query_text, limit=top_k)

        # Return the content of the found objects
        return [obj.properties.get("content", "") for obj in response.objects]

    except Exception as e:
        logging.error(f"Failed to query Weaviate: {e}")
        return []


def get_latest_playbook_section(section: str) -> Optional[dict]:
    """
    Fetches the latest playbook from memory and returns a specific section.
    'section' can be 'okrs' or 'tasks'.
    """
    client = get_weaviate_client()
    memories = client.collections.get(COLLECTION_NAME)
    try:
        # A more direct way to get the latest playbook, assuming a timestamp property
        # For now, we query for "playbook" and sort by creation time as a proxy.
        response = memories.query.bm25(
            query="Playbook",
            limit=1,
            # We would need to add a timestamp property to sort by.
            # sort=Sort.by_property("timestamp_utc", SortOrder.DESCENDING),
        )

        if not response.objects:
            return None

        latest_playbook_str = response.objects[0].properties.get("content", "{}")
        playbook_data = json.loads(latest_playbook_str)
        return playbook_data.get(section)

    except Exception as e:
        logging.error(f"Could not retrieve latest playbook section '{section}': {e}")
        return None


if __name__ == "__main__":
    # Example usage and schema setup for manual testing
    logging.info("Attempting to connect to Weaviate for manual test...")
    try:
        client = get_weaviate_client()
        logging.info(
            f"Successfully connected to Weaviate. Collections: {[c.name for c in client.collections.list_all()]}"
        )

        test_id = "test:12345"
        test_content = "This is a test document for the memory keeper."
        logging.info(f"Storing test document: '{test_content}'")
        store(test_id, test_content)

        logging.info("Querying for 'test document'...")
        results = query("test document", top_k=2)
        logging.info(f"Query results: {results}")
        assert any(test_content in res for res in results)
        logging.info("Memory Keeper test successful.")

    except Exception as e:
        logging.critical(f"Memory Keeper failed to initialize or run test: {e}")
