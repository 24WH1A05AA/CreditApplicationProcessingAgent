import os
import re
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import FakeEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from backend.config import settings
from backend.utils.logging import logger

class RAGPipeline:
    def __init__(self):
        self.kb_dir = settings.KNOWLEDGE_BASE_DIR
        self.vector_db = None
        self.chunks = []
        
        # Configure Embeddings
        is_mock_key = (
            not settings.OPENAI_API_KEY 
            or settings.OPENAI_API_KEY == "mock-key-for-development"
            or not settings.OPENAI_API_KEY.startswith("sk-")
        )
        
        if is_mock_key:
            logger.info("Using FakeEmbeddings (size=1536) for Chroma vector store")
            self.embeddings = FakeEmbeddings(size=1536)
        else:
            logger.info("Using OpenAIEmbeddings for Chroma vector store")
            self.embeddings = OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)

    def load_documents(self) -> List[Dict[str, Any]]:
        """
        Loads documents from knowledge_base supporting PDF, Markdown, and TXT files.
        """
        documents = []
        if not os.path.exists(self.kb_dir):
            logger.warning("Knowledge base directory %s does not exist", self.kb_dir)
            return documents
            
        for filename in os.listdir(self.kb_dir):
            file_path = os.path.join(self.kb_dir, filename)
            ext = os.path.splitext(filename)[1].lower()
            
            try:
                if ext == ".pdf":
                    # Load PDF using PyPDFLoader
                    logger.info("Loading PDF document: %s", filename)
                    loader = PyPDFLoader(file_path)
                    pages = loader.load()
                    # Combine pages or add them individually
                    full_content = "\n".join([page.page_content for page in pages])
                    documents.append({
                        "content": full_content,
                        "metadata": {"source": filename}
                    })
                elif ext in [".txt", ".md"]:
                    # Load Text/Markdown files using TextLoader
                    logger.info("Loading text/markdown document: %s", filename)
                    loader = TextLoader(file_path, encoding="utf-8")
                    docs = loader.load()
                    for doc in docs:
                        documents.append({
                            "content": doc.page_content,
                            "metadata": {"source": filename}
                        })
            except Exception as e:
                logger.error("Failed to load document %s: %s", filename, str(e))
                
        return documents

    def initialize_pipeline(self):
        """
        Loads documents, chunks them, embeds them, and indexes them in a Chroma vector store.
        """
        # Ensure data directory exists for Chroma persistence
        os.makedirs(os.path.dirname(settings.CHROMA_DB_PATH), exist_ok=True)
        
        documents = self.load_documents()
        if not documents:
            logger.warning("No documents loaded to initialize RAG pipeline.")
            return

        # Chunking using RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )

        texts = []
        metadatas = []
        for doc in documents:
            splits = text_splitter.split_text(doc["content"])
            for split in splits:
                if split.strip():
                    texts.append(split.strip())
                    metadatas.append(doc["metadata"])

        self.chunks = texts
        logger.info("Created %d text chunks from knowledge base", len(self.chunks))

        # Build Chroma Vector Store
        try:
            # Clean up existing persistence directory if possible to avoid state mismatch
            # (only in dev/tests environment when starting fresh)
            self.vector_db = Chroma.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas,
                persist_directory=settings.CHROMA_DB_PATH
            )
            
            logger.info("ChromaDB vector store initialized and persisted successfully at %s.", settings.CHROMA_DB_PATH)
        except Exception as e:
            logger.error("Failed to initialize Chroma vector store: %s", str(e))
            raise e

    def retrieve(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves top relevant clauses from ChromaDB with a robust fallback.
        """
        if not self.chunks:
            logger.warning("RAG pipeline not initialized. Retrying initialization...")
            self.initialize_pipeline()

        # Keyword matching heuristics for mock/test environment reliability
        results = []
        keywords = {
            "dti": ["dti", "debt-to-income", "emi", "expense"],
            "credit": ["credit score", "bureau", "cibil", "credit history", "score"],
            "income": ["income", "salaried", "salary", "self-employed", "employment"],
            "kyc": ["kyc", "aadhaar", "pan card", "identification", "ovd"],
            "fair": ["fair", "bias", "gender", "race", "equality"],
            "fraud": ["fraud", "tamper", "falsification", "matching", "discrepancy"]
        }

        # Check if query matches any keywords
        matched_categories = []
        for category, terms in keywords.items():
            if any(term in query.lower() for term in terms):
                matched_categories.append(category)

        # Retrieve via text-matching (highly reliable fallback for offline/development environments)
        for chunk in self.chunks:
            for cat in matched_categories:
                if any(term in chunk.lower() for term in keywords[cat]):
                    clause_match = re.search(r"\[Clause ([A-Z0-9\-]+)\]", chunk)
                    citation = clause_match.group(1) if clause_match else "General Policy"
                    
                    results.append({
                        "content": chunk,
                        "citation": citation,
                        "score": 1.0
                    })
                    break

        # Retrieve via ChromaDB similarity search
        if self.vector_db:
            try:
                # Query ChromaDB using raw similarity search with score
                docs_and_scores = self.vector_db.similarity_search_with_score(query, k=k)
                for doc, score in docs_and_scores:
                    clause_match = re.search(r"\[Clause ([A-Z0-9\-]+)\]", doc.page_content)
                    citation = clause_match.group(1) if clause_match else "General Policy"
                    
                    # Ensure no duplicate content added
                    if not any(res["content"] == doc.page_content for res in results):
                        # If using FakeEmbeddings, assign a low similarity score so keyword match takes priority
                        if isinstance(self.embeddings, FakeEmbeddings):
                            sim_score = 0.0
                        else:
                            # Chroma distance: smaller is better. Map distance to similarity range [0, 1]
                            sim_score = 1.0 / (1.0 + max(0.0, float(score)))
                            
                        results.append({
                            "content": doc.page_content,
                            "citation": citation,
                            "score": sim_score
                        })
            except Exception as e:
                logger.warning("ChromaDB vector search query skipped or failed: %s", str(e))

        # Sort results by score (descending) and take top k
        results = sorted(results, key=lambda x: x["score"], reverse=True)
        return results[:k]

# Global singleton
rag_pipeline = RAGPipeline()
