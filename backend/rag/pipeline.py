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
            try:
                logger.info("Using OpenAIEmbeddings (via OpenRouter) for Chroma vector store")
                self.embeddings = OpenAIEmbeddings(
                    openai_api_key=settings.OPENAI_API_KEY,
                    openai_api_base=settings.OPENAI_API_BASE
                )
            except Exception as e:
                logger.error("Failed to initialize OpenAIEmbeddings: %s. Falling back to FakeEmbeddings.", str(e))
                self.embeddings = FakeEmbeddings(size=1536)

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
                    logger.info("Loading PDF document: %s", filename)
                    loader = PyPDFLoader(file_path)
                    pages = loader.load()
                    full_content = "\n".join([page.page_content for page in pages])
                    documents.append({
                        "content": full_content,
                        "metadata": {"source": filename}
                    })
                elif ext in [".txt", ".md"]:
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
        Loads documents, chunks them by clause markers, and indexes them in a Chroma vector store.
        """
        os.makedirs(os.path.dirname(settings.CHROMA_DB_PATH), exist_ok=True)
        
        documents = self.load_documents()
        if not documents:
            logger.warning("No documents loaded to initialize RAG pipeline.")
            return

        texts = []
        metadatas = []
        
        # Split documents using policy [Clause ] markers for absolute accuracy
        for doc in documents:
            content = doc["content"]
            if "[Clause " in content:
                parts = content.split("[Clause ")
                # Add pre-clause header if it exists
                if parts[0].strip():
                    texts.append(parts[0].strip())
                    metadatas.append(doc["metadata"])
                
                # Add each clause as an individual chunk
                for part in parts[1:]:
                    reconstructed = "[Clause " + part
                    if reconstructed.strip():
                        texts.append(reconstructed.strip())
                        metadatas.append(doc["metadata"])
            else:
                # Fallback to standard character splitter if no clause tags exist
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=500,
                    chunk_overlap=50,
                    separators=["\n\n", "\n", " ", ""]
                )
                splits = text_splitter.split_text(content)
                for split in splits:
                    if split.strip():
                        texts.append(split.strip())
                        metadatas.append(doc["metadata"])

        self.chunks = texts
        logger.info("Created %d text chunks from knowledge base", len(self.chunks))

        # Build Chroma Vector Store
        try:
            self.vector_db = Chroma.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas,
                persist_directory=settings.CHROMA_DB_PATH
            )
            logger.info("ChromaDB vector store initialized and persisted successfully at %s.", settings.CHROMA_DB_PATH)
        except Exception as e:
            logger.critical("Failed to initialize Chroma vector store: %s. System will run in keyword-fallback mode.", str(e))
            self.vector_db = None

    def retrieve(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves top relevant clauses from ChromaDB with a robust fallback.
        """
        if not self.chunks:
            logger.warning("RAG pipeline not initialized. Retrying initialization...")
            self.initialize_pipeline()

        results = []
        keywords = {
            "dti": ["dti", "debt-to-income", "emi", "expense"],
            "credit": ["credit score", "bureau", "cibil", "credit history", "score", "default", "defaults", "write-off", "write-offs"],
            "income": ["income", "salaried", "salary", "self-employed", "employment"],
            "kyc": ["kyc", "aadhaar", "pan card", "identification", "ovd"],
            "fair": ["fair", "bias", "gender", "race", "equality"],
            "fraud": ["fraud", "tamper", "falsification", "matching", "discrepancy"]
        }

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
                docs_and_scores = self.vector_db.similarity_search_with_score(query, k=k)
                for doc, score in docs_and_scores:
                    clause_match = re.search(r"\[Clause ([A-Z0-9\-]+)\]", doc.page_content)
                    citation = clause_match.group(1) if clause_match else "General Policy"
                    
                    if not any(res["content"] == doc.page_content for res in results):
                        if isinstance(self.embeddings, FakeEmbeddings):
                            sim_score = 0.0
                        else:
                            sim_score = 1.0 / (1.0 + max(0.0, float(score)))
                            
                        results.append({
                            "content": doc.page_content,
                            "citation": citation,
                            "score": sim_score
                        })
            except Exception as e:
                logger.warning("ChromaDB vector search query skipped or failed: %s", str(e))

        results = sorted(results, key=lambda x: x["score"], reverse=True)
        return results[:k]

# Global singleton
rag_pipeline = RAGPipeline()
