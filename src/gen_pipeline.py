import logging
import os
import sys
import chromadb
from src.config import MONTH_FULL_NAMES, MONTH_PATTERN, YEAR_PATTERN, DOCUMENTS
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.llms.openai import OpenAI
from llama_index.core.retrievers import RecursiveRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers.fusion_retriever import QueryFusionRetriever
from dotenv import load_dotenv
from src.subqueries_gen_class import query_analyzer
from langchain.chains.llm import LLMChain
from src.qa_template import qa_prompt
from langchain_openai import ChatOpenAI
from src.utils import (
    creat_node_data_from_input_dir,
    create_nodes_from_nodes_data,
    make_filter,
    format_retrieved_chunks,
)
from qdrant_client import QdrantClient
from llama_index.embeddings.openai import OpenAIEmbedding
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.runnable import RunnableSequence
from langchain_community.callbacks import get_openai_callback
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding


class GenPipeline:
    _initialized = False

    def __init__(self) -> None:
        self._load_env()
        self.CHROMA_DB_PATH = "src/correct_testing_db"
        self.COLLECTION_NAME = "quickstart"
        self.model_name = "gpt-4o-mini"
        self.embed_model_name = "text-embedding-3-small"

        self._initialize_model()
        GenPipeline._initialized = True

    def _load_env(self):
        try:
            load_dotenv()
            openai_api = os.getenv("OPENAI_API_KEY")
            if not openai_api:
                raise ValueError("openai API key is missing.")
        except Exception as e:
            logging.error(f"Error while loading env variable: {e}")
            raise Exception(e, sys)

    def _initialize_model(self):

        # qa_tmpl_str = prompt_alpha.qa_prompt
        # self.qa_tmpl = PromptTemplate(qa_tmpl_str)
        # self.lim_reorder = LongContextReorder()
        # self.reranker = FlagEmbeddingReranker(
        #                 top_n=3,
        #                 model=self.rerank_model_name,)

        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=0.0,
            verbose=True,
            streaming=True,
            stream_usage=True,
        )

        self.embed_model = OpenAIEmbedding(model_name=self.embed_model_name)
        Settings.embed_model = self.embed_model
        # Settings.llm = self.llm

    def subqueries_retriever(self, sub_qeuries):
        index = self._create_or_get_chroma()
        index_qdrant = self._search_similar_vectors()
        print(f"---------------------{sub_qeuries}---------------------")
        retrieved_chucks = []
        if sub_qeuries:
            for sub_query in sub_qeuries:
                query_filters = make_filter(sub_query.sub_query)
                print(f"filter-------{query_filters}")
                retriever = index.as_retriever(
                    filters=query_filters, similarity_top_k=3
                )
                retriever_chunk = RecursiveRetriever(
                    "vector",
                    retriever_dict={"vector": retriever},
                    verbose=True,
                )
                chucks = retriever.retrieve(sub_query.sub_query)
                retrieved_chucks.extend(chucks)
        return retrieved_chucks

    # def single_query_retrieve(self, query):
    #     index = self._create_or_get_chroma()
    #     retriever = index.as_retriever(similarity_top_k=3)
    #     retriever_chunk = RecursiveRetriever(
    #         "vector",
    #         retriever_dict={"vector": retriever},
    #         verbose=True,
    #     )
    #     retrieved_chucks = retriever_chunk.retrieve(query)
    #     return retrieved_chucks
    def single_query_retrieve(self, query):
        index = self._create_or_get_chroma()
        print("***", index)
        query_filters = make_filter(query)
        print("***", query_filters)
        retriever = index.as_retriever(filters=query_filters, similarity_top_k=3)
        print("***", retriever)
        retrieved_chucks = retriever.retrieve(query)
        print("***", retrieved_chucks)
        # Extract only filename and text
        results = [
            {"filename": chunk.node.metadata.get("filename"), "text": chunk.node.text}
            for chunk in retrieved_chucks
        ]
        return results

    def _get_qdrant_index(self):
        try:
            client = QdrantClient(host="98.70.40.88", port=6333)

            vector_store = QdrantVectorStore(
                client=client, collection_name="alfalah_investment"
            )
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store, embed_model=self.embed_model
            )
            return index

        except Exception as e:
            logging.error(f"Error during setup_Qdrant: {e}")
            raise Exception(e, sys)

    def _search_similar_vectors(self, query):
        try:
            client = QdrantClient(host="98.70.40.88", port=6333)
            vector_store = QdrantVectorStore(
                # client=client, collection_name="qdrant_collection"
                client=client,
                collection_name="alfalah_investment",
            )
            logging.info("no collection found")
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store, embed_model=self.embed_model_
            )
        except Exception as e:
            logging.error(f"Error during setup_chroma: {e}")
            raise Exception(e, sys)

        query_filters = make_filter(query)
        retriever = index.as_retriever(filters=query_filters, similarity_top_k=3)

        chucks = retriever.retrieve(query)
        results = [
            {"filename": chunk.node.metadata.get("filename"), "text": chunk.node.text}
            for chunk in chucks
        ]
        return results, chucks

    def _create_or_get_chroma(self):
        try:
            db = chromadb.PersistentClient(path=self.CHROMA_DB_PATH)
            chroma_collection = db.get_or_create_collection(self.COLLECTION_NAME)
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

            # if len(chroma_collection.get()["documents"]) == 0:
            #     nodes_data = creat_node_data_from_input_dir(DOCUMENTS)
            #     nodes = create_nodes_from_nodes_data(nodes_data)

            #     logging.info("no collection found")
            #     storage_context = StorageContext.from_defaults(
            #     vector_store=vector_store
            #     )
            #     index = VectorStoreIndex(
            #         nodes= nodes, storage_context=storage_context,
            #         show_progress= True
            # )
            # else:
            logging.info("collection found")
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store, embed_model=self.embed_model_
            )

            return index

        except Exception as e:
            logging.error(f"Error during setup_chroma: {e}")
            raise Exception(e, sys)

    def input_user_query(self, query_str, chat_history=[]):
        try:
            with get_openai_callback() as cb:
                sub_qeuries = query_analyzer.invoke({"question": query_str})
                sub_qeuries_cost = cb.total_cost
                print(sub_qeuries_cost)
            if sub_qeuries:
                print(f"---------------------{sub_qeuries}---------------------")
                self.retriever_chunk = self.subqueries_retriever(sub_qeuries)
            else:
                self.retriever_chunk = self.single_query_retrieve(query_str)
            # print(self.retriever_chunk)
            results, self.retriever_chunk = self._search_similar_vectors(query_str)
            retrieved_text = format_retrieved_chunks(self.retriever_chunk)

            print(retrieved_text)
            # return retrieved_text
            # Create the prompt template and use the dictionary format
            prompt = PromptTemplate(
                input_variables=["query_str", "retrieved_chucks", "chat_history"],
                template=qa_prompt,
            )

            # Dictionary input for PromptTemplate
            input_data = {
                "query_str": query_str,
                "retrieved_chucks": retrieved_text,
                "chat_history": chat_history,
            }

            llm_chain = prompt | self.llm | StrOutputParser()
            response = llm_chain.invoke(input_data)

            # with get_openai_callback() as cb:
            #     for chunk in llm_chain.stream(input_data):
            #         print(chunk, flush=True)
            #         yield chunk
            # # print(response)
            # print(f"Total Tokens: {cb.total_tokens}")
            # print(f"Prompt Tokens: {cb.prompt_tokens}")
            # print(f"Completion Tokens: {cb.completion_tokens}")
            # print(f"Total Cost (USD): ${cb.total_cost }")
            # total_cost = cb.total_cost + sub_qeuries_cost
            return response

        except Exception as e:
            logging.error(f"Error in processes user query: {str(e)}")
