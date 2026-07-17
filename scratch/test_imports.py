import sys
import os

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    print("SUCCESS: Imports are working!")
except Exception as e:
    print(f"FAILED: {str(e)}")
