import os
import re
import json
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import FakeEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
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
                    openai_api_key=settings.OPENAI_API_KEY, #text-embedding-3-small model for embeddings
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

    def _raw_retrieve(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Performs the basic retrieval (keyword and Chroma similarity search).
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
                    else:
                        for res in results:
                            if res["content"] == doc.page_content:
                                if not isinstance(self.embeddings, FakeEmbeddings):
                                    res["score"] = max(res["score"], 1.0 / (1.0 + max(0.0, float(score))))
                                break
            except Exception as e:
                logger.warning("ChromaDB vector search query skipped or failed: %s", str(e))

        results = sorted(results, key=lambda x: x["score"], reverse=True)
        return results

    def grade_document_relevance(self, query: str, document_content: str) -> bool:
        """
        Grades the relevance of a document to a query using an LLM or keyword rules if mock key.
        """
        is_mock_key = (
            not settings.OPENAI_API_KEY 
            or settings.OPENAI_API_KEY == "mock-key-for-development"
            or not settings.OPENAI_API_KEY.startswith("sk-")
        )
        
        # Simple rule-based grading
        keywords = {
            "dti": ["dti", "debt-to-income", "emi", "expense"],
            "credit": ["credit score", "bureau", "cibil", "credit history", "score", "default", "defaults", "write-off", "write-offs"],
            "income": ["income", "salaried", "salary", "self-employed", "employment"],
            "kyc": ["kyc", "aadhaar", "pan card", "identification", "ovd"],
            "fair": ["fair", "bias", "gender", "race", "equality"],
            "fraud": ["fraud", "tamper", "falsification", "matching", "discrepancy"]
        }
        
        query_categories = []
        for cat, terms in keywords.items():
            if any(term in query.lower() for term in terms):
                query_categories.append(cat)
                
        rule_relevant = False
        for cat in query_categories:
            if any(term in document_content.lower() for term in keywords[cat]):
                rule_relevant = True
                break
                
        if not query_categories:
            query_words = set(re.findall(r'\w+', query.lower())) - {"what", "is", "the", "a", "of", "and", "or", "for", "to"}
            doc_words = set(re.findall(r'\w+', document_content.lower()))
            overlap = len(query_words.intersection(doc_words))
            if overlap >= 1:
                rule_relevant = True

        if is_mock_key:
            return rule_relevant

        try:
            llm = ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                model_name=settings.OPENAI_MODEL,
                temperature=0.0,
                max_retries=1
            )
            
            prompt = (
                "You are a relevance grader. Your job is to determine if a retrieved credit underwriting policy clause is relevant to a specific user query.\n"
                "Query: {query}\n"
                "Retrieved Clause Content:\n\"\"\"\n{doc_content}\n\"\"\"\n\n"
                "Determine if the clause contains information that directly answers or relates to the query.\n"
                "Output ONLY a JSON object in the following format:\n"
                "{{\n"
                "  \"is_relevant\": true/false,\n"
                "  \"reasoning\": \"explanation\"\n"
                "}}"
            )
            
            messages = [
                SystemMessage(content="You are a strict relevance grader. Output only JSON."),
                HumanMessage(content=prompt.format(query=query, doc_content=document_content))
            ]
            
            response = llm.invoke(messages)
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            parsed = json.loads(content)
            logger.info("CRAG: LLM graded document relevance: %s", parsed.get("is_relevant"))
            return bool(parsed.get("is_relevant", rule_relevant))
        except Exception as e:
            logger.warning("CRAG: LLM relevance grading failed: %s. Falling back to keyword rules.", str(e))
            return rule_relevant

    def reformulate_query(self, query: str) -> str:
        """
        Reformulates the query to optimize vector retrieval using the LLM or rules.
        """
        is_mock_key = (
            not settings.OPENAI_API_KEY 
            or settings.OPENAI_API_KEY == "mock-key-for-development"
            or not settings.OPENAI_API_KEY.startswith("sk-")
        )
        
        expanded = query
        if "dti" in query.lower():
            expanded = "maximum allowed DTI debt to income ratio limits requirements CP-DTI-01"
        elif "credit" in query.lower() or "score" in query.lower() or "bureau" in query.lower():
            expanded = "bureau credit score thresholds poor fair good excellent limits CP-CS-01 CP-CS-02"
        elif "income" in query.lower():
            expanded = "minimum monthly income salary requirements salaried self-employed CP-INC-01"
        elif "default" in query.lower():
            expanded = "active defaults write-off history policy rules CP-CS-02"

        if is_mock_key:
            return expanded

        try:
            llm = ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                model_name=settings.OPENAI_MODEL,
                temperature=0.0,
                max_retries=1
            )
            
            prompt = (
                "You are an expert search query reformulation assistant.\n"
                "The following search query failed to retrieve relevant underwriting policy clauses from the vector database.\n"
                f"Original Query: {query}\n\n"
                "Reformulate, expand, and rewrite this query to include search keywords, synonyms, and specific clause identifiers "
                "(like CP-CS-01, CP-DTI-01, CP-INC-01, CP-CS-02, KYC, defaults limits) that would improve retrieval in a credit underwriting knowledge base.\n"
                "Output ONLY the re-written query string. Do not include introductory text."
            )
            
            messages = [
                SystemMessage(content="You are a precise search optimizer. Output only the query string."),
                HumanMessage(content=prompt)
            ]
            
            response = llm.invoke(messages)
            new_query = response.content.strip().strip('"').strip("'")
            logger.info("CRAG: LLM reformulated query to: '%s'", new_query)
            return new_query if new_query else expanded
        except Exception as e:
            logger.warning("CRAG: LLM query reformulation failed: %s. Falling back to rule-based expansion.", str(e))
            return expanded

    def retrieve(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves top relevant clauses from ChromaDB using Self-Corrective RAG (CRAG) workflow.
        """
        logger.info("CRAG: Commencing retrieval for query: '%s'", query)
        
        # 1. Initial retrieval (slightly wider candidate set)
        candidates = self._raw_retrieve(query, k=k*2)
        
        # 2. Grade retrieved candidates
        relevant_results = []
        for cand in candidates:
            is_relevant = self.grade_document_relevance(query, cand["content"])
            if is_relevant:
                relevant_results.append(cand)
                
        logger.info("CRAG: Initial retrieval graded %d/%d documents as relevant.", len(relevant_results), len(candidates))
        
        # 3. If no relevant documents are found, reformulate query and retry
        if len(relevant_results) < 1:
            logger.info("CRAG: Relevance threshold not met. Triggering query reformulation...")
            reformulated = self.reformulate_query(query)
            
            secondary_candidates = self._raw_retrieve(reformulated, k=k)
            for cand in secondary_candidates:
                is_relevant = self.grade_document_relevance(reformulated, cand["content"])
                if is_relevant and not any(r["content"] == cand["content"] for r in relevant_results):
                    relevant_results.append(cand)
            logger.info("CRAG: Secondary retrieval with reformulated query found %d relevant documents.", len(relevant_results))

        # 4. Fallback to raw results if still empty
        if len(relevant_results) < 1:
            logger.info("CRAG: Still no relevant documents. Using fallback keyword search.")
            fallback = self._raw_retrieve(query, k=k)
            relevant_results.extend(fallback)

        # De-duplicate and sort
        seen = set()
        final_results = []
        for r in relevant_results:
            if r["content"] not in seen:
                seen.add(r["content"])
                final_results.append(r)
                
        final_results = sorted(final_results, key=lambda x: x["score"], reverse=True)
        return final_results[:k]

# Global singleton
rag_pipeline = RAGPipeline()
