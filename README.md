# EU AI Act Chat

AI-powered compliance assistant for the EU AI Act.

This tool analyzes AI systems and classifies them under the EU AI Act
using a combination of retrieval-augmented generation (RAG), rule-based
decision logic, and LLM reasoning.

------------------------------------------------------------------------

## Features

-   Chat-based interface (Streamlit)
-   RAG pipeline over EU AI Act
-   Decision Engine (rule-based classification support)
-   Confidence scoring
-   Source traceability with exact legal references
-   Dynamic follow-up questions for missing information

------------------------------------------------------------------------

## Tech Stack

-   Python
-   Streamlit
-   SentenceTransformers
-   FAISS (vector search)
-   LLM (DeepSeek / OpenAI compatible)
-   Custom decision engine

------------------------------------------------------------------------

## How it works

1.  User asks a question about an AI system\
2.  Relevant legal text is retrieved (RAG)\
3.  Decision engine analyzes context\
4.  LLM generates a structured answer\
5.  Confidence score + sources are provided\
6.  System asks follow-up questions if needed

------------------------------------------------------------------------

## Project Structure

    app/
      rag_pipeline.py
      decision_engine.py
      llm.py
      confidence.py

    ui/
      streamlit_app.py

    scripts/
      ingest.py

    data/
      index/
      processed/

------------------------------------------------------------------------

## Setup

``` bash
git clone https://github.com/YOUR_USERNAME/eu-ai-act-chat.git
cd eu-ai-act-chat

pip install -r requirements.txt
```

Create a `.env` file:

    DEEPSEEK_API_KEY=your_api_key_here

------------------------------------------------------------------------

## Run

``` bash
streamlit run ui/streamlit_app.py
```

------------------------------------------------------------------------

## Disclaimer

This project is for educational and prototyping purposes only.\
It does not provide legally binding advice.

------------------------------------------------------------------------

## Author

Built as a portfolio project demonstrating:

-   AI system design
-   LLM integration
-   Explainability in AI
-   Real-world regulatory use case
