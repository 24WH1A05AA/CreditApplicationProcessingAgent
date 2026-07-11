# Capstone Project 05 -- Loan / Credit Application Processing Agent

## Domain

**Lending / Credit Processing**

## Business Owner

**Head of Credit Operations**

------------------------------------------------------------------------

# Business Problem

Banks and fintech companies receive thousands of loan applications every
day.

Currently:

-   Documents are manually verified.
-   Credit officers calculate eligibility.
-   Decisions are inconsistent.
-   Processing takes hours or days.
-   Every decision must satisfy financial regulations.

The goal is **not to replace the underwriter**, but to assist them.

The AI should: - Verify documents - Evaluate eligibility - Recommend a
decision - Explain why - Check fairness - Maintain a complete audit
trail

The final approval is always done by a human.

------------------------------------------------------------------------

# Business Objective

``` text
Receive Loan Application
        ↓
Verify Documents
        ↓
Score Against Credit Policy
        ↓
Recommend
 ├── Approve
 ├── Refer
 └── Decline
        ↓
Human Underwriter Reviews
        ↓
Final Decision
        ↓
Audit Log
```

------------------------------------------------------------------------

# Success Metrics (KPIs)

## 1. Decision Turnaround Time

Example:

-   Manual: **45 minutes**
-   AI Assisted: **8 minutes**

## 2. Straight-Through Approval Rate

Example:

-   Manual: **40%**
-   AI Assisted: **78%**

## 3. Audit Pass Rate

The system should clearly explain: - Why a decision was made - Which
policy clauses were used - Who approved the final decision - Whether
fairness checks passed

------------------------------------------------------------------------

# Business Requirements

## 1. Intake Application

Collect: - Applicant details - Loan amount - Loan purpose - Income -
Uploaded documents

## 2. Verify Documents

Verify: - Government ID - Income proof - Bank statement

Check consistency between all submitted documents.

## 3. Policy Scoring

Evaluate: - Debt-to-Income Ratio (DTI) - Credit History - Income
Stability - Existing Loans

Generate a transparent composite score.

## 4. Recommendation

Recommend one of:

-   Approve
-   Refer
-   Decline

Every recommendation must include supporting policy citations.

## 5. Human Gate

The AI **never makes the final decision**.

Workflow:

``` text
AI Recommendation
        ↓
Licensed Underwriter
        ↓
Final Decision
```

## 6. Audit Log

Store: - Input application - Uploaded documents - Score breakdown -
Policy citations - AI recommendation - Human decision - Timestamp

------------------------------------------------------------------------

# Overall Architecture

``` text
                User
                  │
                  ▼
       Loan Application UI
                  │
                  ▼
        Decisioning Agent (LLM)
          ├──────────────┬──────────────┐
          ▼              ▼              ▼
Document Validation  Policy Retrieval  Credit Scoring
          └──────────────┬──────────────┘
                         ▼
             Recommendation Engine
                         ▼
                Fairness Validation
                         ▼
                 Human Underwriter
                         ▼
                  Final Decision
                         ▼
                   Audit Database
```

------------------------------------------------------------------------

# Detailed Workflow

``` text
Receive Application
        ↓
Extract Applicant Data
        ↓
Verify Documents
        ↓
Retrieve Credit Policy (RAG)
        ↓
Calculate Score
        ↓
Explain Score
        ↓
Run Fairness Check
        ↓
Generate Recommendation
        ↓
Human Approval
        ↓
Save Audit
        ↓
End
```

------------------------------------------------------------------------

# Internal Agent Reasoning

``` text
START
  ↓
Documents Complete?
  ├── No → Request Missing Documents → END
  └── Yes
        ↓
Calculate DTI
        ↓
Check Credit History
        ↓
Check Income Stability
        ↓
Generate Composite Score
        ↓
Apply Policy
        ↓
Recommend
        ↓
Fairness Check
        ↓
Human Review
        ↓
Audit Log
        ↓
END
```

------------------------------------------------------------------------

# Components

## Loan Intake Agent

Converts the application into structured JSON.

## Document Validation Agent

Validates: - PAN/Aadhaar (or equivalent ID) - Salary slips - Bank
statements - Missing or inconsistent information

## Credit Policy Engine

Scores applicants using policy rules and produces a composite score.

## Recommendation Engine

Maps the score to: - Approve - Refer - Decline

## Fairness Checker

Removes identity information (name, address, etc.) and verifies the
recommendation remains unchanged.

## Human Gate

Displays: - Recommendation - Score - Evidence - Policy citations

The underwriter makes the final decision.

## Audit Logger

Stores the entire decision lifecycle for compliance and traceability.

------------------------------------------------------------------------

# RAG Knowledge Base

Suggested documents: - Internal Credit Policy - RBI Lending Guidelines -
KYC Guidelines - Risk Rules - Fraud Detection Policies - Interest Rate
Policies

------------------------------------------------------------------------

# Tools

  Tool                 Purpose
  -------------------- --------------------------------
  OCR                  Read uploaded documents
  Document Validator   Validate document completeness
  Credit Score API     Fetch credit score
  Debt Calculator      Calculate DTI
  RAG Retriever        Retrieve policy clauses
  Fairness Validator   Identity-blind re-scoring
  Audit Logger         Store complete decision record
  Human Approval UI    Capture final approval

------------------------------------------------------------------------

# Governance

-   No automatic approval or rejection.
-   Transparent score breakdown.
-   Policy citations required.
-   Identity-blind fairness check.
-   Complete audit logging.

------------------------------------------------------------------------

# Evaluation Scenarios

  Scenario            Expected Behaviour
  ------------------- ------------------------------------------------------
  Clear Approve       Recommend APPROVE with cited policy; human signs off
  Borderline Refer    Recommend REFER with reasons
  Missing Documents   Request missing documents; no scoring
  Fairness            Recommendation unchanged after identity removal
  Adversarial Input   Ignore "approve regardless"; follow policy

------------------------------------------------------------------------

# Suggested Tech Stack

-   **Frontend:** Streamlit / React
-   **Backend:** FastAPI
-   **Agent Framework:** LangGraph or CrewAI
-   **LLM:** GPT-5.5 / GPT-4.1 / Gemini
-   **RAG:** LangChain + FAISS/ChromaDB
-   **OCR:** Tesseract
-   **Validation:** Pydantic
-   **Database:** PostgreSQL / SQLite
-   **Audit Storage:** PostgreSQL / MongoDB

------------------------------------------------------------------------

# End-to-End Workflow

``` text
Customer Submits Application
        │
        ▼
Loan Intake
        │
        ▼
Document Validation
        │
        ▼
Credit Policy Retrieval (RAG)
        │
        ▼
Score Calculation
        │
        ▼
Recommendation
        │
        ▼
Fairness Check
        │
        ▼
Human Underwriter
        │
        ▼
Final Decision
        │
        ▼
Audit Logging
        │
        ▼
Response Returned
```
