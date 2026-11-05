# HealthGuide AI 

### Evidence-Based Health Information Assistant

HealthGuide AI is an AI-powered health information assistant designed to help users access understandable, evidence-based health information through natural language conversations.

The application combines **Retrieval-Augmented Generation (RAG)** with online health information retrieval to generate responses grounded in information from trusted public health sources, including the World Health Organization (WHO), the Centers for Disease Control and Prevention (CDC), and MyHealthfinder.

Rather than relying solely on an AI model's pre-trained knowledge, HealthGuide retrieves relevant health information before generating responses.

## Project Objective

The goal of HealthGuide AI is to demonstrate how AI engineering techniques, particularly Retrieval-Augmented Generation, can be applied to make reliable public health information more accessible and understandable.

The project also explores the potential of AI-powered information systems in addressing health information accessibility challenges.


##  Key Features

- **AI-Powered Health Assistant:** Ask health-related questions using natural language.
- **Evidence-Based Responses:** Uses retrieved information from trusted public health sources to ground generated answers.
- **Hybrid Retrieval:** Combines online health information retrieval with local vector search.
- **Source References:** Displays the sources used to generate responses.
- **Insufficient Evidence Handling:** Designed to avoid presenting unsupported information as established fact.
- **User Authentication:** Registration and login with password hashing and JWT-based authentication.
- **Personalized Health Interests:** Users can select and manage their health interests.
- **Health Library:** Saves previous questions, answers, topics, and sources for later reference.
- **Responsive Interface:** A clean interface designed for convenient access across devices.

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| Styling | CSS |
| Backend | Python, FastAPI |
| Database | SQLAlchemy, SQLite / PostgreSQL |
| AI Model | Groq API |
| Retrieval Architecture | Retrieval-Augmented Generation (RAG) |
| Vector Database | ChromaDB |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) |
| Web Retrieval | Requests, BeautifulSoup |
| Authentication | JWT, Argon2 password hashing |
| Deployment | Vercel (frontend), Render (backend) |

##  System Architecture

HealthGuide AI follows a retrieval-augmented generation architecture.

1. **User Input:** A signed-in user submits a health-related question.
2. **Evidence Retrieval:** The backend retrieves relevant information from online health sources and the local ChromaDB collection.
3. **Evidence Processing:** Retrieved passages are processed and relevant evidence is selected.
4. **AI Generation:** The Groq-powered language model generates an answer using the retrieved evidence.
5. **Source Presentation:** The application returns the answer alongside its supporting sources.
6. **History Storage:** The question, answer, topic, and source references are saved to the user's Health Library.

## 📁 Project Structure

```text
HealthGuide-AI/
│
├── backend/
│   ├── auth.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── requirements.txt
│   ├── documents/
│   └── rag/
│       ├── hybrid_retriever.py
│       ├── llm_service.py
│       ├── online_retriever.py
│       ├── retriever.py
│       └── chroma_db/
│
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
│
├── docs/
├── .gitignore
└── README.md
```

##  Local Installation and Setup

### Prerequisites

- Python
- Node.js and npm
- Git
- A Groq API key

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/Health_guide.git

cd Health_guide
```

### 2. Set up the backend

Navigate to the backend directory:

```bash
cd backend
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file inside the backend directory:

```env
GROQ_API_KEY=your_groq_api_key
JWT_SECRET_KEY=your_secure_random_secret
DATABASE_URL=sqlite:///./healthguide.db
```

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

Backend API:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### 3. Set up the frontend

Open another terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create a `.env` file inside the frontend directory:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Start the development server:

```bash
npm run dev
```

Frontend:

```text
http://localhost:5173
```


## ⚠️ Health Information Disclaimer

HealthGuide AI is an educational health information tool. It is not a medical diagnostic system and does not replace professional medical advice, diagnosis, or treatment.

Users should consult qualified healthcare professionals for personal medical concerns and treatment decisions.

