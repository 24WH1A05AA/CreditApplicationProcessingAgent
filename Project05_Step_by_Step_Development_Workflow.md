# Project 05 -- Loan / Credit Application Processing Agent

# Step-by-Step Development Guide

> Goal: Build a production-style MVP that receives a loan application,
> validates documents, evaluates it against credit policy, recommends a
> decision, routes it for human approval, and stores a complete audit
> trail.

------------------------------------------------------------------------

# Phase 1 -- Understand the Problem

## Objective

Understand the business and define the MVP.

### Deliverables

-   Business problem statement
-   One user (Credit Underwriter)
-   One workflow
-   One success metric
-   Technology stack

### Workflow

``` text
Customer
    ↓
Loan Application
    ↓
AI Recommendation
    ↓
Human Approval
    ↓
Final Decision
```

------------------------------------------------------------------------

# Phase 2 -- Gather Requirements

## Functional Requirements

-   Accept loan application
-   Upload documents
-   Validate documents
-   Retrieve credit policy (RAG)
-   Calculate score
-   Recommend Approve / Refer / Decline
-   Human approval
-   Audit logging

## Non-functional Requirements

-   Explainable
-   Fair
-   Auditable
-   Reliable
-   Fast

------------------------------------------------------------------------

# Phase 3 -- Design the Architecture

``` text
Frontend
   │
   ▼
FastAPI Backend
   │
   ▼
LangGraph Decision Agent
   │
 ┌─┼──────────────────────────────┐
 ▼ ▼                              ▼
Validation Tool           Credit Policy (RAG)
Credit Score Tool         Debt Calculator
Fairness Checker          Audit Logger
   │
   ▼
Human Approval
   │
   ▼
Database
```

Deliverables: - Architecture diagram - Folder structure - Tool list

------------------------------------------------------------------------

# Phase 4 -- Create the Project

## Backend

-   FastAPI
-   LangGraph
-   LangChain
-   Pydantic
-   SQLAlchemy
-   ChromaDB / FAISS

## Frontend

-   Streamlit (recommended for MVP)

Create folders:

``` text
backend/
agents/
tools/
rag/
database/
models/
evaluation/
frontend/
data/
docs/
```

------------------------------------------------------------------------

# Phase 5 -- Prepare Data

## Credit Policy

Create a policy document containing: - Debt-to-Income rules - Credit
score rules - Income stability rules - Approval thresholds

## Sample Applications

Create 20--100 mock applications.

## Documents

Prepare: - ID - Income proof - Bank statement - Salary slip

------------------------------------------------------------------------

# Phase 6 -- Build the RAG Pipeline

Steps

1.  Load policy PDFs
2.  Split into chunks
3.  Generate embeddings
4.  Store in vector database
5.  Build retriever
6.  Return policy clauses

Deliverable: Working RAG search.

------------------------------------------------------------------------

# Phase 7 -- Build Individual Tools

## Tool 1

Document Validator

Input: Application documents

Output: - Complete - Missing - Invalid

------------------------------------------------------------------------

## Tool 2

Credit Score Tool

Returns applicant credit score (mock API acceptable).

------------------------------------------------------------------------

## Tool 3

Debt-to-Income Calculator

Calculates DTI.

------------------------------------------------------------------------

## Tool 4

Policy Retrieval Tool

Uses RAG to retrieve relevant policy.

------------------------------------------------------------------------

## Tool 5

Recommendation Tool

Uses scores and policy to recommend: - Approve - Refer - Decline

------------------------------------------------------------------------

## Tool 6

Fairness Checker

Remove identity information. Run scoring again. Recommendation must
remain unchanged.

------------------------------------------------------------------------

## Tool 7

Audit Logger

Store: - Inputs - Tool calls - Policy citations - Recommendation - Human
decision - Timestamp

------------------------------------------------------------------------

# Phase 8 -- Build the LangGraph Workflow

Nodes:

``` text
Start
 ↓
Loan Intake
 ↓
Document Validation
 ↓
Policy Retrieval
 ↓
Credit Scoring
 ↓
Recommendation
 ↓
Fairness Check
 ↓
Human Approval
 ↓
Audit Logging
 ↓
End
```

Each node should update shared state.

------------------------------------------------------------------------

# Phase 9 -- Human Approval

AI never finalizes a decision.

``` text
Recommendation
      ↓
Licensed Underwriter
      ↓
Approve / Refer / Reject
```

------------------------------------------------------------------------

# Phase 10 -- Database

Suggested tables: - applications - applicants - documents -
policy_results - recommendations - audit_logs

------------------------------------------------------------------------

# Phase 11 -- Frontend

Pages: 1. Login 2. Dashboard 3. New Application 4. Upload Documents 5.
Decision Details 6. Human Approval 7. Audit History

------------------------------------------------------------------------

# Phase 12 -- Evaluation

Implement the required scenarios:

1.  Clear Approve
2.  Borderline Refer
3.  Missing Document
4.  Fairness Test
5.  Prompt Injection

Record: - Trace correctness - Tool-call accuracy - Task completion -
Business KPI

------------------------------------------------------------------------

# Phase 13 -- Testing

Test: - Backend APIs - Tool integrations - LangGraph workflow - RAG
retrieval - Human approval - Audit logging - UI

------------------------------------------------------------------------

# Phase 14 -- Demo

Demo sequence:

``` text
Open Dashboard
 ↓
Create Loan Application
 ↓
Upload Documents
 ↓
Validate Documents
 ↓
Retrieve Policy
 ↓
Calculate Score
 ↓
Generate Recommendation
 ↓
Run Fairness Check
 ↓
Human Approval
 ↓
Save Audit Log
 ↓
Show Final Decision
```

------------------------------------------------------------------------

# Suggested Git Milestones

## Milestone 1

Project setup

## Milestone 2

Backend APIs

## Milestone 3

RAG implementation

## Milestone 4

Tool development

## Milestone 5

LangGraph workflow

## Milestone 6

Human approval

## Milestone 7

Audit logging

## Milestone 8

Frontend

## Milestone 9

Evaluation suite

## Milestone 10

Final demo

------------------------------------------------------------------------

# Final Deliverables

-   Working MVP
-   LangGraph workflow
-   RAG knowledge base
-   Tool integrations
-   Human approval gate
-   Audit logging
-   Evaluation report
-   Architecture diagram
-   Demo video / presentation

This guide follows the Project 05 capstone workflow from planning
through deployment and evaluation, while keeping the implementation
focused on the required MVP.
