import chromadb
import logging
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from src.config import MONTH_FULL_NAMES, MONTH_PATTERN, YEAR_PATTERN, DOCUMENTS
from src.utils import (
    creat_node_data_from_input_dir,
    create_nodes_from_nodes_data,
    make_filter,
    format_retrieved_chunks,
)


def add_data_to_chroma(path):
    CHROMA_DB_PATH = "src/testing_db"
    COLLECTION_NAME = "quickstart"
    embed_model = "text-embedding-3-small"

    embed_model_ = OpenAIEmbedding(model_name=embed_model)
    Settings.embed_model = embed_model_

    db = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    chroma_collection = db.get_or_create_collection(COLLECTION_NAME)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    nodes_data = creat_node_data_from_input_dir(path)
    nodes = create_nodes_from_nodes_data(nodes_data)

    logging.info("no collection found")
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex(
        nodes=nodes, storage_context=storage_context, show_progress=True
    )


import logging
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from src.utils import creat_node_data_from_input_dir, create_nodes_from_nodes_data
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models
import qdrant_client
from llama_index.embeddings.openai import OpenAIEmbedding


def add_data_to_qdrant(path):

    client = qdrant_client.QdrantClient(url="http://localhost:6333/", port=6333)

    COLLECTION_NAME = "alfalah_investment"
    embed_model_name = "text-embedding-3-small"

    embed_model = OpenAIEmbedding(model_name=embed_model_name)
    Settings.embed_model = embed_model

    vector_store = QdrantVectorStore(client=client, collection_name=COLLECTION_NAME)
    nodes_data = creat_node_data_from_input_dir(path)
    nodes = create_nodes_from_nodes_data(nodes_data)

    logging.info("no collection found")
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store,
    )
    index = VectorStoreIndex(nodes, storage_context=storage_context)
    return index


# "http://65.0.229.53"


def delete_data_from_qdrant(filename: str):
    # Initialize Qdrant client
    client = qdrant_client.QdrantClient(url="http://localhost:6333/", port=6333)

    COLLECTION_NAME = "alfalah_investment"
    embed_model_name = "text-embedding-3-small"

    # Set the embedding model
    embed_model = OpenAIEmbedding(model_name=embed_model_name)
    Settings.embed_model = embed_model

    # Perform the delete operation
    try:
        response = client.delete(
            collection_name=COLLECTION_NAME,  # Use the variable directly
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="filename",
                            match=models.MatchValue(value=filename),
                        )
                    ]
                )
            ),
        )
        if response.status == "ok":
            return f"File '{filename}' deleted successfully."
        else:
            return "Failed to delete the file."
    except Exception as e:
        raise "Error deleting the file:"
