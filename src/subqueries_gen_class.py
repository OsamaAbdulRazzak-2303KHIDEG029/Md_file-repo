from langchain.output_parsers import PydanticToolsParser
from langchain_core.prompts import ChatPromptTemplate
# from pydantic import BaseModel
# from langchain_core.pydantic_v1 import BaseModel, Field
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings
from dotenv import load_dotenv
locals = load_dotenv()

class SubQuery(BaseModel):
    """Search over a database of tutorial videos about a software library."""

    sub_query: str = Field(
        ...,
        description="A very specific query against the database.",
    )

system = """You are an expert at converting user questions into database queries. \
You have access to a database of monthly reports. \

Perform query decomposition. Given a user question, break it down into distinct sub questions that \
you need to answer in order to answer the original question.

if year is present convert it in 4 digits.

If there are acronyms or words you are not familiar with, do not try to rephrase them."""
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "{question}"),
    ]
)

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.0)
Settings.llm = llm
llm_with_tools = llm.bind_tools([SubQuery])
parser = PydanticToolsParser(tools=[SubQuery])
query_analyzer = prompt | llm_with_tools | parser