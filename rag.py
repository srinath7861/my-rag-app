"""
CLI for RAG: uses Chroma + Gemini + Groq.
If the knowledge base is empty, run ingestion first (see STEPS.md).
"""
import sys

from rag_core import configure_gemini, get_groq_client, get_collection, query_rag


def main() -> None:
    try:
        configure_gemini()
        get_groq_client()
        coll = get_collection()
        n = coll.count()
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    if n == 0:
        print("Knowledge base is empty. Ingest first:", file=sys.stderr)
        print("  python -c \"from ingest import ingest_knowledge_file; ingest_knowledge_file()\"", file=sys.stderr)
        print("  or use the API: POST /ingest/url or /ingest/document", file=sys.stderr)
        sys.exit(1)

    print(f"Ready ({n} chunks). Ask a question (or 'quit' / 'exit' to stop).")

    while True:
        try:
            question = input("\nQuestion: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            break
        try:
            result = query_rag(question)
            print(result["answer"])
            if result.get("sources"):
                print("  Sources:", [s.get("source") for s in result["sources"]])
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
