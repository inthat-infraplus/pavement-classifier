import os
import shutil
import zipfile
import tempfile
from pathlib import Path
from fastapi import FastAPI, Depends, Request, Form, HTTPException, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from .db import engine, Base, get_db
from .models import User, Task, Image
from .auth import get_password_hash, verify_password, get_current_user, require_user, require_l1, require_l2

@asynccontextmanager
async def lifespan(app: FastAPI):
    # App startup logic if needed
    yield

app = FastAPI(lifespan=lifespan)

# Create folders if they don't exist
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Path conversion for Windows paths to container paths
def convert_path_to_container(folder_path: str) -> str:
    r"""
    Convert Windows paths to container paths.
    Examples:
    - E:\S25_DRR\xeno\survey_data_20250504\PAVE\20250504_1\PAVE-0 -> /xeno/survey_data_20250504/PAVE/20250504_1/PAVE-0
    - E:/S25_DRR/xeno/... -> /xeno/...
    """
    # Normalize the path (handle both / and \)
    path = folder_path.replace("\\", "/")
    
    # Remove drive letter if present (e.g., E:)
    if len(path) > 2 and path[1] == ":":
        path = path[2:]
    
    # Match the mounted volume: E:\S25_DRR\xeno -> /xeno
    # Remove leading /S25_DRR/ to get /xeno/...
    if "/S25_DRR/xeno" in path:
        path = path.split("S25_DRR/xeno")[1]
        if not path.startswith("/"):
            path = "/" + path
        return "/xeno" + path
    elif "/xeno" in path:
        # Path already contains /xeno
        return path
    
    # If none of the above, return original (for testing or other cases)
    return folder_path

@app.get("/", response_class=HTMLResponse)
def root(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    if user.role == "L1":
        return RedirectResponse(url="/l1_dashboard", status_code=302)
    elif user.role == "L2":
        return RedirectResponse(url="/l2_dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)

@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.post("/login")
def login_post(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Invalid credentials"})
    
    # Set cookie
    res = RedirectResponse(url="/", status_code=302)
    res.set_cookie(key="user_id", value=str(user.id), httponly=True)
    return res

@app.get("/logout")
def logout():
    res = RedirectResponse(url="/login", status_code=302)
    res.delete_cookie("user_id")
    return res

@app.get("/l1_dashboard", response_class=HTMLResponse)
def l1_dashboard(request: Request, user: User = Depends(require_l1), db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    l2_users = db.query(User).filter(User.role == "L2").all()
    return templates.TemplateResponse(request=request, name="l1_dashboard.html", context={
        "user": user, "tasks": tasks, "l2_users": l2_users
    })

@app.post("/users/create_l2")
def create_l2_user(
    username: str = Form(...),
    password: str = Form(...),
    user: User = Depends(require_l1),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.username == username).first()
    if not existing:
        new_user = User(username=username, role="L2", hashed_password=get_password_hash(password))
        db.add(new_user)
        db.commit()
    return RedirectResponse(url="/l1_dashboard", status_code=302)

@app.post("/tasks")
def create_task(
    folder_path: str = Form(...),
    assignee_id: int = Form(...),
    user: User = Depends(require_l1),
    db: Session = Depends(get_db)
):
    # Convert Windows path to container path if needed
    folder_path = convert_path_to_container(folder_path)
    
    if not os.path.isdir(folder_path):
        # We can handle this more gracefully in UI, but this suffices
        raise HTTPException(status_code=400, detail="Invalid folder path")
    
    new_task = Task(assigner_id=user.id, assignee_id=assignee_id, folder_path=folder_path)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # scan images
    supported_exts = {".jpg", ".jpeg", ".png", ".bmp"}
    for filename in os.listdir(folder_path):
        ext = os.path.splitext(filename)[1].lower()
        if ext in supported_exts:
            img = Image(task_id=new_task.id, filename=filename)
            db.add(img)
    db.commit()
    
    return RedirectResponse(url="/l1_dashboard", status_code=302)

@app.get("/l2_dashboard", response_class=HTMLResponse)
def l2_dashboard(request: Request, user: User = Depends(require_l2), db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.assignee_id == user.id).all()
    return templates.TemplateResponse(request=request, name="l2_dashboard.html", context={"user": user, "tasks": tasks})

@app.get("/tasks/{task_id}/classify", response_class=HTMLResponse)
def classify_get(request: Request, task_id: int, user: User = Depends(require_l2), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id, Task.assignee_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Find next unclassified image
    next_image = db.query(Image).filter(Image.task_id == task_id, Image.label == None).first()
    
    total = db.query(Image).filter(Image.task_id == task_id).count()
    classified = db.query(Image).filter(Image.task_id == task_id, Image.label != None).count()
    
    return templates.TemplateResponse(request=request, name="classify.html", context={
        "user": user, "task": task, "image": next_image,
        "total": total, "classified": classified
    })

@app.post("/api/images/{image_id}/classify")
def submit_classification(
    request: Request,
    image_id: int,
    label: str = Form(...), # 'pavement' or 'normal'
    user: User = Depends(require_l2),
    db: Session = Depends(get_db)
):
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
        
    task = db.query(Task).filter(Task.id == image.task_id).first()
    if task.assignee_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    if label not in ["pavement", "normal"]:
        raise HTTPException(status_code=400, detail="Invalid label")
        
    image.label = label
    db.commit()
    
    # Check if task is completed
    unclassified_count = db.query(Image).filter(Image.task_id == task.id, Image.label == None).count()
    if unclassified_count == 0:
        task.status = "completed"
        db.commit()
        
    return RedirectResponse(url=f"/tasks/{task.id}/classify", status_code=302)

@app.get("/api/images/serve/{image_id}")
def serve_image(image_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)):
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    task = db.query(Task).filter(Task.id == image.task_id).first()
    if user.role == "L2" and task.assignee_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
        # Handle old /images paths -> convert to /xeno
        folder_path = task.folder_path
        if folder_path.startswith("/images"):
            folder_path = folder_path.replace("/images", "/xeno", 1)
        
        filepath = os.path.join(folder_path, image.filename)
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="File not found on disk")
        
        return FileResponse(filepath)

@app.get("/tasks/{task_id}/qc", response_class=HTMLResponse)
def qc_check_get(request: Request, task_id: int, user: User = Depends(require_l1), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    images = db.query(Image).filter(Image.task_id == task_id).all()
    
    return templates.TemplateResponse(request=request, name="qc_check.html", context={
        "user": user, "task": task, "images": images
    })

@app.post("/api/images/{image_id}/qc_update")
def qc_update_image(
    image_id: int,
    label: str = Form(...),
    user: User = Depends(require_l1),
    db: Session = Depends(get_db)
):
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
        
    if label not in ["pavement", "normal"]:
        raise HTTPException(status_code=400, detail="Invalid label")
        
    image.label = label
    db.commit()
    
    return RedirectResponse(url=f"/tasks/{image.task_id}/qc", status_code=302)

@app.get("/tasks/{task_id}/export")
def export_task(task_id: int, user: User = Depends(require_l1), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
        # Handle old /images paths -> convert to /xeno
        folder_path = task.folder_path
        if folder_path.startswith("/images"):
            folder_path = folder_path.replace("/images", "/xeno", 1)
    
    images = db.query(Image).filter(Image.task_id == task_id).all()
    
    # We will build the zip file in a temporary file and return it directly.
    # To clean up properly after returning a FileResponse from a temp file,
    # we can just yield the file, but standard FileResponse works if we don't delete immediately.
    # Alternatively, use a predictable temp location.
    
    temp_dir_obj = tempfile.TemporaryDirectory()
    temp_dir = temp_dir_obj.name
    
    dataset_dir = os.path.join(temp_dir, "dataset")
    pavement_dir = os.path.join(dataset_dir, "pavement")
    normal_dir = os.path.join(dataset_dir, "normal")
    os.makedirs(pavement_dir, exist_ok=True)
    os.makedirs(normal_dir, exist_ok=True)
    
    for img in images:
        if not img.label:
            continue # Skip unclassified
            
        src_path = os.path.join(folder_path, img.filename)
        if not os.path.exists(src_path):
            continue
            
        dest_dir = pavement_dir if img.label == "pavement" else normal_dir
        dest_path = os.path.join(dest_dir, img.filename)
        shutil.copy2(src_path, dest_path)
        
    zip_path = os.path.join(temp_dir, f"task_{task_id}_export")
    shutil.make_archive(zip_path, 'zip', dataset_dir)
    
    return FileResponse(
        f"{zip_path}.zip",
        media_type="application/zip",
        filename=f"task_{task_id}_export.zip"
    )

@app.get("/tasks/{task_id}/export_txt/{label}", response_class=PlainTextResponse)
def export_txt(task_id: int, label: str, user: User = Depends(require_l1), db: Session = Depends(get_db)):
    if label not in ["pavement", "normal"]:
        raise HTTPException(status_code=400, detail="Invalid label")
        
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    images = db.query(Image).filter(Image.task_id == task_id, Image.label == label).all()
    
    content = "\n".join([img.filename for img in images])
    
    headers = {
        "Content-Disposition": f"attachment; filename=\"{label}.txt\""
    }
    return PlainTextResponse(content=content, headers=headers)

