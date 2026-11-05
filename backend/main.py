
import jwt
import os


from models import HealthInterest, QuestionHistory, User
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import Base, engine, get_db
from auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

# AI services
from rag.hybrid_retriever import retrieve_hybrid_evidence
from rag.llm_service import generate_health_answer


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="HealthGuide AI API",
    description="Evidence-grounded public health information assistant",
    version="0.1.0",
)


cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in cors_origins.split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


bearer_scheme = HTTPBearer()


# Request and response schemas

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class HealthInterestRequest(BaseModel):
    interests: list[str] = Field(min_length=1, max_length=20)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=5000)


# Public endpoints

@app.get("/")
def root():
    return {
        "message": "HealthGuide AI API is running",
        "status": "ok",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Authentication endpoints

@app.post(
    "/api/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    email = request.email.strip().lower()

    existing_user = (
        db.query(User).filter(User.email == email).first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        name=request.name.strip(),
        email=email,
        hashed_password=hash_password(request.password),
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    return user


@app.post("/api/auth/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    email = request.email.strip().lower()

    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(
        request.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    token = create_access_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


# Authentication dependency

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = decode_access_token(token)

        subject = payload.get("sub")

        if not subject:
            raise credentials_error

        user_id = int(subject)

    except (jwt.InvalidTokenError, ValueError):
        raise credentials_error

    user = db.query(User).filter(User.id == user_id).first()

    if user is None or not user.is_active:
        raise credentials_error

    return user


# Protected account endpoint

@app.get("/api/auth/me", response_model=UserResponse)
def get_my_account(
    current_user: User = Depends(get_current_user),
):
    return current_user


# Dashboard: Health interests

@app.get("/api/dashboard/interests")
def get_my_interests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return [
        item.interest
        for item in db.query(HealthInterest)
        .filter(HealthInterest.user_id == current_user.id)
        .order_by(HealthInterest.interest)
        .all()
    ]


@app.put("/api/dashboard/interests")
def save_my_interests(
    request: HealthInterestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    interests = list(
        dict.fromkeys(
            interest.strip()
            for interest in request.interests
            if interest.strip()
        )
    )

    if not interests:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one valid health interest.",
        )

    if len(interests) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can select up to 20 health interests.",
        )

    if any(len(interest) > 100 for interest in interests):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Each interest must be 100 characters or fewer.",
        )

    db.query(HealthInterest).filter(
        HealthInterest.user_id == current_user.id
    ).delete(synchronize_session=False)

    db.add_all(
        [
            HealthInterest(
                user_id=current_user.id,
                interest=interest,
            )
            for interest in interests
        ]
    )

    db.commit()

    return {"interests": interests}


# Dashboard: Question history

@app.get("/api/dashboard/questions")
def get_my_questions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    questions = (
        db.query(QuestionHistory)
        .filter(QuestionHistory.user_id == current_user.id)
        .order_by(QuestionHistory.created_at.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "id": item.id,
            "question": item.question,
            "created_at": item.created_at,
        }
        for item in questions
    ]


@app.post(
    "/api/dashboard/questions",
    status_code=status.HTTP_201_CREATED,
)
def save_my_question(
    request: QuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    question_text = request.question.strip()

    if not question_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    question = QuestionHistory(
        user_id=current_user.id,
        question=question_text,
    )

    db.add(question)
    db.commit()
    db.refresh(question)

    return {
        "id": question.id,
        "question": question.question,
        "created_at": question.created_at,
    }


# Health Library: Retrieve saved questions

@app.get("/api/library")
def get_health_library(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    records = (
        db.query(QuestionHistory)
        .filter(QuestionHistory.user_id == current_user.id)
        .order_by(QuestionHistory.created_at.desc())
        .all()
    )

    return [
        {
            "id": item.id,
            "question": item.question,
            "topic": item.topic,
            "created_at": item.created_at,
        }
        for item in records
    ]


# Health Library: Retrieve a saved answer

@app.get("/api/library/{question_id}")
def get_library_question(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = (
        db.query(QuestionHistory)
        .filter(
            QuestionHistory.id == question_id,
            QuestionHistory.user_id == current_user.id,
        )
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved question not found.",
        )

    return {
        "id": item.id,
        "question": item.question,
        "answer": item.answer,
        "sources": item.sources or [],
        "topic": item.topic,
        "created_at": item.created_at,
    }      

def classify_health_topic(question: str) -> str:
    text = question.lower()

    topic_keywords = {
        "Malaria": ["malaria", "mosquito", "anopheles"],
        "Diabetes": ["diabetes", "blood sugar", "glucose"],
        "Cholera": ["cholera"],
        "Heart Health": [
            "heart",
            "blood pressure",
            "hypertension",
            "cardiovascular",
        ],
        "Nutrition": [
            "nutrition",
            "diet",
            "food",
            "vitamins",
            "malnutrition",
        ],
        "Mental Health": [
            "mental health",
            "stress",
            "anxiety",
            "depression",
        ],
        "Infectious Diseases": [
            "infection",
            "infectious disease",
            "tuberculosis",
            "ebola",
            "hiv",
        ],
    }

    for topic, keywords in topic_keywords.items():
        if any(keyword in text for keyword in keywords):
            return topic

    return "General Health"

# HealthGuide AI: Ask a health question

@app.post("/api/ask")
def ask_health_question(
    request: QuestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    question_text = request.question.strip()

    if not question_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    # 1. Retrieve relevant health evidence
    try:
        retrieval = retrieve_hybrid_evidence(
            question=question_text,
            top_k=5,
            online_top_k=5,
            local_top_k=3,
        )

    except Exception as error:
        print(f"Health evidence retrieval failed: {error}")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Health information retrieval is temporarily "
                "unavailable. Please try again."
            ),
        )

    evidence = retrieval.get("results", [])
    print("\n========== HEALTHGUIDE DEBUG ==========")
    print("Question:", question_text)
    print("Has evidence:", retrieval.get("has_evidence"))
    print("Online results:", retrieval.get("total_online_results"))
    print("Local results:", retrieval.get("total_local_results"))
    print("Unique results:", retrieval.get("total_unique_results"))
    print("Relevant results:", retrieval.get("total_relevant_results"))
    print("Selected evidence:", len(evidence))
    for index, item in enumerate(evidence, start=1):
        print(f"\nSource {index}")
        print("Title:", item.get("title"))
        print("Publisher:", item.get("source"))
        print("Score:", item.get("relevance_score"))
        print("Text:", item.get("text", "")[:250])
        print("=======================================\n")

    # 2. Generate an evidence-grounded answer
    try:
        ai_response = generate_health_answer(
            question=question_text,
            evidence=evidence,
        )

    except Exception as error:
        print(f"AI answer generation failed: {error}")

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "The AI service is temporarily unavailable. "
                "Please try again."
            ),
        )

    # 3. Save the question, answer, and sources
    history_item = QuestionHistory(
        user_id=current_user.id,
        question=question_text,
        answer=ai_response["answer"],
        sources=ai_response["sources"],
        topic=classify_health_topic(question_text),
    )

    try:
        db.add(history_item)
        db.commit()
        db.refresh(history_item)

    except Exception as error:
        db.rollback()
        print(f"Question history save failed: {error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save your question and answer.",
        )

    # 4. Return answer and sources
    return {
        "question_id": history_item.id,
        "question": question_text,
        "answer": ai_response["answer"],
        "sources": ai_response["sources"],
        "evidence_count": ai_response["evidence_count"],
        "has_evidence": retrieval.get("has_evidence", False),
        "providers_unavailable": retrieval.get(
            "providers_unavailable",
            [],
        ),
    }
