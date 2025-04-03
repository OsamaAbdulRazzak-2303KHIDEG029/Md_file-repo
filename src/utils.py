import re
import os
import pandas as pd

from langchain_text_splitters import MarkdownHeaderTextSplitter
from llama_index.core import SimpleDirectoryReader
from llama_index.readers.file.flat import FlatReader
from llama_index.core.schema import TextNode, RelatedNodeInfo, NodeRelationship
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core.vector_stores import (
    MetadataFilter,
    MetadataFilters,
    FilterOperator,
    FilterCondition,
)
from deep_translator import GoogleTranslator
from src.config import MONTH_FULL_NAMES, MONTH_PATTERN, YEAR_PATTERN


csv_file_path = "src/query_response_cache.csv"


def creat_node_data_from_input_dir(inpur_dir):

    documents = SimpleDirectoryReader(
        input_dir=inpur_dir,
        file_extractor={
            ".md": FlatReader()
        },  # This disables the MarkdownReader for .md files
        recursive=True,
    ).load_data()

    nodes_data = []

    for document in documents:
        markdown_document = document.get_content()
        filename = document.metadata.get("filename")
        file_id = document.id_
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]

        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on
        )
        md_header_splits = markdown_splitter.split_text(markdown_document)

        node_data = {"file_id": file_id, "filename": filename, "node_text": []}

        for text in md_header_splits:
            headers_combined = []

            # Loop through metadata and concatenate headers
            for _, header in text.metadata.items():
                if header:
                    headers_combined.append(header)

            headers_combined = " of ".join(headers_combined[::-1])
            # Concatenate headers and page content
            concat_text = headers_combined + "\n" + text.page_content
            node_data["node_text"].append(concat_text)
        nodes_data.append(node_data)

    return nodes_data


def create_nodes_from_nodes_data(nodes_data):
    nodes = []
    for data in nodes_data:
        filename = data["filename"]
        month = extract_month(filename)
        year = extract_year(filename)
        if month and year:
            for text in data["node_text"]:
                node = TextNode(
                    text=(text),
                    metadata={
                        "year": str(year),
                        "month": month,
                        "filename": filename,
                        "file_id": data["file_id"],
                    },
                )
                node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(
                    node_id=data["file_id"], metadata={"filename": filename}
                )
                nodes.append(node)
        else:
            for text in data["node_text"]:
                node = TextNode(
                    text=(text),
                    metadata={
                        "filename": filename,
                        "file_id": data["file_id"],
                    },
                )
                node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(
                    node_id=data["file_id"], metadata={"filename": filename}
                )
                nodes.append(node)

    return nodes


# Function to extract the month from the query
def extract_month(sub_query):
    month_match = re.search(MONTH_PATTERN, sub_query, re.IGNORECASE)
    if month_match:
        matched_month = month_match.group(0)[:3].lower()
        return MONTH_FULL_NAMES.get(matched_month, None)
    return None


# Function to extract the year from the query
def extract_year(sub_query):
    year_match = re.search(YEAR_PATTERN, sub_query)
    if year_match:
        return year_match.group(0)
    return None


# Function to create filters based on the extracted month and year
def create_filters(month, year):
    filters_list = []

    # If a month is found, add a month filter
    if month:
        filters_list.append(
            MetadataFilter(key="month", operator=FilterOperator.EQ, value=month)
        )

    # If a year is found, add a year filter
    if year:
        filters_list.append(
            MetadataFilter(key="year", operator=FilterOperator.EQ, value=year)
        )

    # Return filters if any are found, otherwise None
    if filters_list:
        return MetadataFilters(filters=filters_list, condition=FilterCondition.AND)
    return None


# Main function to handle the overall process
def make_filter(sub_query):
    # Extract month and year from the query
    month = extract_month(sub_query)
    year = extract_year(sub_query)
    # Create and return filters based on extracted month and year
    return create_filters(month, year)


def format_retrieved_chunks(retrieved_chunks):
    formatted_texts = []

    for node_with_score in retrieved_chunks:
        node = node_with_score.node
        print(
            "-----------------------------------------------------------------------------"
        )
        # print(node_with_score)
        metadata = node.metadata
        # print(metadata)

        # Extract metadata

        year = metadata.get("year", "N/A")
        month = metadata.get("month", "N/A")
        filename = metadata.get("filename", "N/A")
        text_metadata = metadata.get("text_metadata", "N/A")
        text_content = node.text

        # Format text according to the desired output
        formatted_text = (
            f"year: {year}\n"
            f"month: {month}\n"
            f"filename: {filename}\n"
            f"text_metadata: {text_metadata}\n"
            f"{text_content}\n"
            "--------------------------"
        )

        formatted_texts.append(formatted_text)

    # Join all the formatted texts together
    return "\n".join(formatted_texts)


def translate_to_other_language(response, language):
    translator = GoogleTranslator(source="auto", target=language)
    translated_text = translator.translate(response)
    return translated_text


def read_cache_data():
    """Read cached query-response data from a CSV file."""
    try:
        if os.path.exists(csv_file_path):
            return pd.read_csv(csv_file_path)
        else:
            return pd.DataFrame(columns=["query", "response"])
    except Exception as e:
        print(f"Error reading the cache file: {e}")
        return pd.DataFrame(columns=["query", "response"])


def search_response_from_cache(query: str):
    """Search for a response by query from the cache. Returns the response if found, otherwise None."""
    df = read_cache_data()
    query = query.lower()
    result = df[df["query"] == query]

    if not result.empty:
        return result["response"].values[0]

    return None


def add_record_to_cache(query: str, response: str):
    """Add a query-response record to the cache, keeping only the latest 2000 records."""
    try:
        df = read_cache_data()
        query = query.lower()

        new_data = pd.DataFrame({"query": [query], "response": [response]})
        updated_df = pd.concat([df, new_data], ignore_index=True)

        # Keep only the latest 2000 records
        if len(updated_df) > 2000:
            updated_df = updated_df.tail(2000)

        # Write back to the CSV file
        updated_df.to_csv(csv_file_path, index=False)

    except Exception as e:
        print(f"Error writing to the cache file: {e}")
