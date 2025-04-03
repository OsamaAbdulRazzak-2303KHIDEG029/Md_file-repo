import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.model import UserQuery, InputDirPath
from src.utils import (
    translate_to_other_language,
    search_response_from_cache,
    add_record_to_cache,
)
from dotenv import load_dotenv
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from src.gen_pipeline import GenPipeline
from src.add_chroma_data import (
    add_data_to_chroma,
    add_data_to_qdrant,
    delete_data_from_qdrant,
)
import sys
import json

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

gen_pipeline = GenPipeline()


def append_to_json(file_path, data):
    try:
        # Read the existing data from the JSON file
        with open(file_path, "r") as f:
            existing_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist or is empty, start with an empty list
        existing_data = []

    # Append the new data
    existing_data.append(data)

    # Write the updated data back to the file
    with open(file_path, "w") as f:
        json.dump(existing_data, f, indent=4)


@app.post("/stream")
async def stream(user_query: UserQuery):
    query_str = user_query.query
    chat_history = user_query.chat_history
    language = user_query.language

    # cache_response = search_response_from_cache(query = query_str)
    # if cache_response:
    #     response, totat_cost = cache_response, 0
    #     if language != "en":
    #         response = translate_to_other_language(response, language)
    # else:
    #     response, totat_cost = gen_pipeline.input_user_query(query_str, chat_history)
    #     add_record_to_cache(query = query_str, response=response)
    #     if language != "en":
    response = gen_pipeline.input_user_query(
        query_str=query_str, chat_history=chat_history
    )
    # Prepare the data to append
    data_to_append = {"query": query_str, "response": response}

    # Append the data to the JSON file
    # append_to_json("responses.json", data_to_append)
    return data_to_append
    # return {
    #         "query": query_str,
    #         "response": response,
    #         "total_token": totat_cost,
    #         }


@app.post("/testing_retreival")
async def stream(user_query: UserQuery):
    query_str = user_query.query
    chat_history = user_query.chat_history
    language = user_query.language

    qdrant_result, retriever_chunk = gen_pipeline._search_similar_vectors(
        query=query_str
    )
    # print(qdrant_result)
    chroma_result = gen_pipeline.single_query_retrieve(query=query_str)
    # print(chroma_result)
    # Format the output
    output_data = {
        "query": query_str,
        "qdrant_result": qdrant_result,
        "chroma_result": chroma_result,
    }

    # File path for the JSON output
    file_path = "output.json"

    # Check if the file already exists
    if os.path.exists(file_path):
        # Read existing data
        with open(file_path, "r") as f:
            try:
                # Load existing JSON data
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []  # If the file is empty or not valid JSON
    else:
        existing_data = []

    # Append the new output data
    existing_data.append(output_data)

    # Write the updated data back to the JSON file
    with open(file_path, "w") as f:
        json.dump(existing_data, f, indent=4)  # Write as pretty-printed JSON

    return output_data


@app.post("/adddata")
def add_qdrant_data(input_dir_path: InputDirPath):
    input_path = input_dir_path.input_path
    # add_data_to_chroma(input_path)
    add_data_to_qdrant(input_path)
    return "sucessfully added the resource"


@app.delete("/delete")
def delete_qdrant_data(filename):
    delete_data_from_qdrant(filename)
    return "sucessfully deleted the resource"


@app.post("/get")
def add_chroma_data():
    def stream_response():
        print("heer we are boys")
        # response_generator = gen_pipeline.input_user_query('what is the cash fund', [])
        # print(type(response_generator))
        for chunk in gen_pipeline.input_user_query(
            "describe in detail the investment objectvie of alfalah investment", []
        ):
            if isinstance(chunk, str):  # Stream the chunk
                # full_response += chunk  # chat_history = request.data.get("chat_history", [])Accumulate full response
                # print(full_response)
                yield chunk

    return StreamingResponse(stream_response(), media_type="text/event-stream")
