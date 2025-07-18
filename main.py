import os
import uuid
import json
import zipfile
from datetime import datetime, timedelta
from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException, status, Request, Body, Form
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, and_, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from agents.langgraph_flow import app as langgraph_app, PipelineState
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from pathlib import Path
import asyncio

from agents.agent_scraper import scrape_breakout, scrape_rastah, save_to_csv, scrape_all_products
from agents.agent_analysis import analyze_products
from agents.qa_chatbot import qa_chatbot
from agents.report_generator import generate_report

load_dotenv()

# --- Auth & DB Setup ---
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# --- Models ---
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer)
    status = Column(String)
    progress_status = Column(String, nullable=True)
    report_path = Column(String, nullable=True)
    error = Column(Text, nullable=True)
    agent_messages = Column(Text, nullable=True)  # Stored as JSON string
    question = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert job to dictionary with proper type handling"""
        try:
            agent_messages = json.loads(str(self.agent_messages)) if self.agent_messages is not None else []
        except (json.JSONDecodeError, TypeError):
            agent_messages = []

        return {
            "id": str(self.id) if self.id is not None else None,
            "user_id": self.user_id if self.user_id is not None else None,
            "status": str(self.status) if self.status is not None else None,
            "progress_status": str(self.progress_status) if self.progress_status is not None else None,
            "report_path": str(self.report_path) if self.report_path is not None else None,
            "error": str(self.error) if self.error is not None else None,
            "agent_messages": agent_messages,
            "question": str(self.question) if self.question is not None else None,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None
        }

Base.metadata.create_all(bind=engine)

# --- Utility Functions ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        # Ensure username is str type
        username_str: str = str(username)
    except JWTError:
        raise credentials_exception
    user = get_user(db, username_str)
    if user is None:
        raise credentials_exception
    return user

# --- FastAPI App ---
app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

# --- Template Routes ---
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/scraper", response_class=HTMLResponse)
async def scraper_page(request: Request):
    return templates.TemplateResponse("scraper.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})

@app.get("/analysis", response_class=HTMLResponse)
async def analysis_page(request: Request):
    return templates.TemplateResponse("analysis.html", {"request": request})

@app.get("/qa", response_class=HTMLResponse)
async def qa_page(request: Request):
    return templates.TemplateResponse("qa.html", {"request": request})

@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    return templates.TemplateResponse("reports.html", {"request": request})

# --- API Routes ---
@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    # Validate input using UserCreate model
    try:
        user_data = UserCreate(username=username, password=password)
    except ValidationError as e:
        # Convert validation error to a readable message
        error_messages = []
        for error in e.errors():
            field = error["loc"][0]
            message = error["msg"]
            error_messages.append(f"{field}: {message}")
        raise HTTPException(
            status_code=422, 
            detail={"message": "Validation error", "errors": error_messages}
        )
        
    if get_user(db, user_data.username):
        raise HTTPException(
            status_code=400, 
            detail={"message": "Registration failed", "errors": ["Username already registered"]}
        )
        
    db_user = User(username=user_data.username, hashed_password=get_password_hash(user_data.password))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User registered successfully"}

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token({"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me")
async def get_current_user_info(user: User = Depends(get_current_user)):
    return {"username": user.username, "id": user.id}

@app.get("/api/history")
async def get_history(
    date_filter: str = "all",
    status_filter: str = "all",
    page: int = 1,
    page_size: int = 10,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Job).filter(Job.user_id == user.id)
    
    # Apply date filter
    if date_filter == "today":
        query = query.filter(Job.created_at >= datetime.utcnow().date())
    elif date_filter == "week":
        query = query.filter(Job.created_at >= datetime.utcnow().date() - timedelta(days=7))
    elif date_filter == "month":
        query = query.filter(Job.created_at >= datetime.utcnow().date() - timedelta(days=30))
    
    # Apply status filter
    if status_filter != "all":
        query = query.filter(Job.status == status_filter)
    
    # Get total count for pagination
    total_count = query.count()
    
    # Apply pagination
    jobs = query.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    # Process jobs for response
    job_list = []
    for job in jobs:
        try:
            agent_messages = json.loads(str(job.agent_messages)) if isinstance(job.agent_messages, str) else []
        except (json.JSONDecodeError, TypeError):
            agent_messages = []
            
        created_at = None
        if hasattr(job, 'created_at') and job.created_at is not None:
            try:
                created_at = job.created_at.isoformat()
            except (AttributeError, TypeError):
                pass
            
        job_list.append({
            "id": str(job.id),
            "status": str(job.status),
            "progress_status": str(job.progress_status) if isinstance(job.progress_status, str) else None,
            "question": str(job.question) if isinstance(job.question, str) else None,
            "created_at": created_at,
            "error": str(job.error) if isinstance(job.error, str) else None,
            "agent_messages": agent_messages
        })
    
    return {
        "jobs": job_list,
        "total": total_count,
        "page": page,
        "page_size": page_size
    }

@app.post("/run_pipeline/")
async def run_pipeline(
    background_tasks: BackgroundTasks,
    question: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job_id = str(uuid.uuid4())
    
    # Create initial job record
    db_job = Job(
        id=job_id,
        user_id=user.id,
        status="queued",
        progress_status="initializing",
        question=question,
        agent_messages=json.dumps([])
    )
    db.add(db_job)
    db.commit()
    
    def task():
        try:
            # Initialize PipelineState
            state = PipelineState(
                question=question,
                scraped_data={},
                analysis_results="",
                report=None,
                messages=[],  # Updated to match new state definition
                progress_status="initializing",
                error=None
            )
            
            # Run the LangGraph pipeline
            result = langgraph_app.invoke(state)
            
            # Save report if generated
            report_path = None
            if result.get("report"):
                report_path = os.path.abspath(f"data/generated_report_{job_id}.txt")
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(str(result["report"]))
            
            # Update job record
            db.query(Job).filter(Job.id == job_id).update({
                Job.status: "failed" if result.get("error") else "complete",
                Job.progress_status: result.get("progress_status", "unknown"),
                Job.report_path: report_path,
                Job.error: result.get("error"),
                Job.agent_messages: json.dumps(result.get("messages", []))  # Updated to match new state
            })
            db.commit()
            
        except Exception as e:
            error_msg = f"Pipeline error: {str(e)}"
            db.query(Job).filter(Job.id == job_id).update({
                Job.status: "failed",
                Job.progress_status: "error",
                Job.error: error_msg,
                Job.agent_messages: json.dumps([])
            })
            db.commit()
    
    background_tasks.add_task(task)
    return {"job_id": job_id}

@app.get("/status/{job_id}")
async def get_status(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        agent_messages = json.loads(str(job.agent_messages)) if isinstance(job.agent_messages, str) else []
    except (json.JSONDecodeError, TypeError):
        agent_messages = []
    
    return {
        "status": str(job.status),
        "progress_status": str(job.progress_status) if isinstance(job.progress_status, str) else None,
        "agent_messages": agent_messages,
        "error": str(job.error) if isinstance(job.error, str) else None
    }

@app.get("/download_report/{job_id}")
async def download_report(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job_status = str(job.status) if isinstance(job.status, str) else None
    if not job_status or job_status != "complete":
        raise HTTPException(status_code=404, detail="Report not found")
    
    report_path = str(job.report_path) if isinstance(job.report_path, str) else None
    if not report_path or not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    return FileResponse(report_path, filename=f"analysis_report_{job_id}.txt") 

@app.post("/api/scraper/start")
async def start_scraping(
    max_products: int = Body(..., ge=2, le=200),
    headless: bool = Body(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job_id = str(uuid.uuid4())
    
    # Create initial job record
    db_job = Job(
        id=job_id,
        user_id=user.id,
        status="running",
        progress_status="scraping",
        question=f"Scraping with max_products={max_products}, headless={headless}",
        agent_messages=json.dumps([
            {"role": "system", "content": "Starting scraping process..."}
        ])
    )
    db.add(db_job)
    db.commit()

    try:
        # Run scraper
        result = await scrape_all_products(total_products=max_products, headless=headless)
        
        # Update job record with success
        db.query(Job).filter(Job.id == job_id).update({
            Job.status: "completed",
            Job.progress_status: "completed",
            Job.report_path: result['files']['all'],  # Save path to combined data
            Job.agent_messages: json.dumps([
                {"role": "system", "content": f"Scraped {result['breakout_count']} products from Breakout"},
                {"role": "system", "content": f"Scraped {result['rastah_count']} products from Rastah"},
                {"role": "system", "content": f"Total products scraped: {result['total_scraped']}"}
            ])
        })
        db.commit()
        
        return {
            "job_id": job_id,
            "status": "completed",
            "message": "Scraping completed successfully",
            "data": result
        }
    except Exception as e:
        # Update job record with error
        db.query(Job).filter(Job.id == job_id).update({
            Job.status: "failed",
            Job.progress_status: "failed",
            Job.error: str(e),
            Job.agent_messages: json.dumps([
                {"role": "system", "content": f"Error during scraping: {str(e)}"}
            ])
        })
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/scraper/stop/{job_id}")
async def stop_scraping(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(
        and_(Job.id == job_id, Job.user_id == user.id)
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status in ["completed", "failed"]:
        return {"status": job.status}
    
    # Update job status to stopped
    db.query(Job).filter(Job.id == job_id).update({
        Job.status: "stopped",
        Job.progress_status: "stopped"
    })
    db.commit()
    
    return {"status": "stopped"}

@app.get("/api/scraper/status/{job_id}")
async def get_scraping_status(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(
        and_(Job.id == job_id, Job.user_id == user.id)
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_dict = job.to_dict()
    
    # Calculate progress based on status
    progress = 0
    breakout_progress = 0
    rastah_progress = 0
    message = None
    
    if job_dict["status"] == "completed":
        progress = 100
        breakout_progress = 100
        rastah_progress = 100
        message = "Scraping completed successfully"
    elif job_dict["status"] == "running":
        progress = 50
        message = "Scraping in progress..."
    elif job_dict["status"] == "failed":
        message = job_dict["error"] or "Scraping failed"
    
    # Get latest message if available
    if job_dict["agent_messages"]:
        message = job_dict["agent_messages"][-1].get("content", message)
    
    return {
        "status": job_dict["status"],
        "progress": progress,
        "breakout_progress": breakout_progress,
        "rastah_progress": rastah_progress,
        "message": message,
        "agent_messages": job_dict["agent_messages"],
        "error": job_dict["error"]
    }

@app.get("/api/scraper/download/{job_id}")
async def download_scraped_data(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(
        and_(Job.id == job_id, Job.user_id == user.id)
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_dict = job.to_dict()
    if job_dict["status"] != "completed":
        raise HTTPException(status_code=400, detail="Data not available")
    
    # Create a temporary file for the zip
    temp_zip = os.path.join("data", f"temp_scrape_{job_id}.zip")
    
    try:
        # Create a zip file containing all CSV files
        with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add all CSV files from the job
            for source in ["breakout", "rastah", "all"]:
                file_path = os.path.join("data", f"{source}_products_{job_id}.csv")
                if os.path.exists(file_path):
                    zip_file.write(file_path, f"{source}_products.csv")
        
        return FileResponse(
            temp_zip,
            media_type="application/zip",
            filename=f"scraped_data_{job_id}.zip",
            background=BackgroundTasks().add_task(lambda: os.unlink(temp_zip))
        )
    except Exception as e:
        if os.path.exists(temp_zip):
            os.unlink(temp_zip)
        raise HTTPException(status_code=500, detail=f"Error creating download: {str(e)}") 

@app.post("/api/analyze")
async def run_analysis(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Run market analysis on the latest product data"""
    try:
        # Create a job record
        job_id = str(uuid.uuid4())
        db_job = Job(
            id=job_id,
            user_id=user.id,
            status="running",
            progress_status="analyzing",
            question="Market Analysis",
            agent_messages=json.dumps([
                {"role": "system", "content": "Starting market analysis..."}
            ])
        )
        db.add(db_job)
        db.commit()

        try:
            # Run analysis
            analysis = analyze_products()  # This will use the latest CSV files
            
            # Update job record with success
            db.query(Job).filter(Job.id == job_id).update({
                Job.status: "completed",
                Job.progress_status: "completed",
                Job.report_path: str(Path('data') / "deep_analysis.txt"),
                Job.agent_messages: json.dumps([
                    {"role": "system", "content": "Analysis completed successfully. You can now view the results."}
                ])
            })
            db.commit()
            
            return {
                "job_id": job_id,
                "status": "completed",
                "message": "Analysis completed successfully"
            }
            
        except ValueError as e:
            # Handle expected errors (like missing data)
            error_msg = str(e)
            db.query(Job).filter(Job.id == job_id).update({
                Job.status: "failed",
                Job.progress_status: "failed",
                Job.error: error_msg,
                Job.agent_messages: json.dumps([
                    {"role": "system", "content": f"Analysis failed: {error_msg}"}
                ])
            })
            db.commit()
            raise HTTPException(
                status_code=400, 
                detail=error_msg
            )
            
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error during analysis: {str(e)}"
            db.query(Job).filter(Job.id == job_id).update({
                Job.status: "failed",
                Job.progress_status: "failed",
                Job.error: error_msg,
                Job.agent_messages: json.dumps([
                    {"role": "system", "content": error_msg}
                ])
            })
            db.commit()
            raise HTTPException(
                status_code=500, 
                detail=error_msg
            )
            
    except HTTPException:
        raise
    except Exception as e:
        # Handle database errors
        raise HTTPException(
            status_code=500, 
            detail=f"Database error occurred while processing the analysis: {str(e)}"
        )

class QARequest(BaseModel):
    question: str

@app.post("/api/qa")
async def ask_question(
    req: QARequest,
    user: User = Depends(get_current_user)
):
    try:
        question = req.question
        print(f"[QA API] Received question: {question}")
        answer_question = qa_chatbot()
        def answer_stream():
            try:
                answer = answer_question(question)
                yield answer
            except Exception as e:
                yield f"Error: {str(e)}"
        print(f"[QA API] Streaming answer...")
        return StreamingResponse(answer_stream(), media_type="text/plain")
    except Exception as e:
        print(f"[QA API] Error: {e}")
        def error_stream():
            yield f"Error: {str(e)}"
        return StreamingResponse(error_stream(), media_type="text/plain")

@app.post("/api/generate-report")
async def api_generate_report(user: User = Depends(get_current_user)):
    try:
        print("[Report API] Generating report...")
        generate_report()
        report_path = os.path.join("data", "generated_report.txt")
        if not os.path.exists(report_path):
            return {"error": "Report file not found after generation."}
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        print(f"[Report API] Error: {e}")
        return {"error": str(e)}

@app.get("/api/report-latest")
async def api_report_latest(user: User = Depends(get_current_user)):
    try:
        report_path = os.path.join("data", "generated_report.txt")
        if not os.path.exists(report_path):
            return {"error": "No report found. Please generate a report first."}
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        print(f"[Report API] Error: {e}")
        return {"error": str(e)}

@app.get("/api/report/{job_id}")
async def get_report(
    job_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(
        and_(Job.id == job_id, Job.user_id == user.id)
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Report not found")
    
    job_dict = job.to_dict()
    report_path = job_dict["report_path"]
    
    if not report_path or not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report file not found")
    
    try:
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 

@app.post("/start-scrape")
async def start_scrape_endpoint(max_products: int = 100):
    """Start the Playwright-based scraper and return the result as a CSV file (headless=True by default)."""
    try:
        result = await scrape_all_products(total_products=max_products, headless=True)
        all_file = result['files']['all']
        # Ensure the file exists before returning
        if not os.path.exists(all_file):
            return {"error": f"CSV file not found: {all_file}"}
        return FileResponse(
            all_file,
            media_type="text/csv",
            filename=os.path.basename(all_file)
        )
    except Exception as e:
        return {"error": str(e)}