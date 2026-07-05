#!/usr/bin/env python3
from dotenv import load_dotenv

load_dotenv()

from backend.rag import get_vector_store


def main() -> None:
    store = get_vector_store()

    try:
        count = getattr(store, "collection").count()
        print(f"Vector Store Document Count: {count}")
    except Exception as e:
        print(f"Could not count documents: {e}")

    print("\n--- Testing Retrieval ---")
    query = "brake grinding noise"
    print(f"Query: '{query}'")

    # Try a query without filtering first
    results = store.search(query=query, k=2)

    if not results:
        print("No results found.")
    else:
        for i, res in enumerate(results):
            print(f"\nResult {i+1}:")
            print(f"  ID: {res.get('id')}")
            print(f"  Distance: {res.get('distance')}")
            print(f"  Metadata: {res.get('metadata')}")
            text_preview = res.get("text", "")[:150].replace("\n", " ")
            print(f"  Text: {text_preview}...")


if __name__ == "__main__":
    main()
