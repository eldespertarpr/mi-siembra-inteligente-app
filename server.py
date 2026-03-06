from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from enum import Enum


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'mi-siembra-inteligente-secret-key-2024')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app
app = FastAPI(title="Mi Siembra Inteligente API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== ENUMS ====================
class UserRole(str, Enum):
    owner = "owner"
    member = "member"

class BedMethod(str, Enum):
    suelo = "suelo"
    hidro = "hidro"

class CropStage(str, Enum):
    germinacion = "germinación"
    vegetativo = "vegetativo"
    cosecha = "cosecha"
    finalizado = "finalizado"

class TaskType(str, Enum):
    riego = "riego"
    fertilizacion = "fertilización"
    siembra = "siembra"
    trasplante = "trasplante"
    poda = "poda"
    cosecha = "cosecha"
    otro = "otro"

class TaskStatus(str, Enum):
    pendiente = "pendiente"
    completada = "completada"
    atrasada = "atrasada"

class HarvestDestination(str, Enum):
    casa = "casa"
    venta = "venta"


# ==================== MODELS ====================

# Auth Models
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    email: str
    role: str
    garden_id: Optional[str] = None
    created_at: str


# Garden Models
class GardenCreate(BaseModel):
    name: str
    location_text: Optional[str] = None

class GardenResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    owner_user_id: str
    name: str
    location_text: Optional[str] = None
    created_at: str


# Bed Models
class BedCreate(BaseModel):
    name: str
    method: BedMethod
    notes: Optional[str] = None

class BedResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    garden_id: str
    name: str
    method: str
    notes: Optional[str] = None


# Crop Models
class CropCreate(BaseModel):
    bed_id: str
    name: str
    variety: Optional[str] = None
    stage: CropStage = CropStage.germinacion
    sow_date: str
    transplant_date: Optional[str] = None
    est_days_to_harvest: int = 60
    notes: Optional[str] = None

class CropUpdate(BaseModel):
    name: Optional[str] = None
    variety: Optional[str] = None
    stage: Optional[CropStage] = None
    transplant_date: Optional[str] = None
    est_days_to_harvest: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

class CropResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    garden_id: str
    bed_id: str
    name: str
    variety: Optional[str] = None
    stage: str
    sow_date: str
    transplant_date: Optional[str] = None
    est_days_to_harvest: int
    target_harvest_date: str
    notes: Optional[str] = None
    is_active: bool
    bed_name: Optional[str] = None
    bed_method: Optional[str] = None


# Task Models
class RepeatRule(BaseModel):
    type: str  # none, daily, weekly, custom
    interval: Optional[int] = None  # for custom: every N days

class TaskCreate(BaseModel):
    title: str
    type: TaskType
    due_datetime: str
    priority: int = 1
    assigned_user_id: Optional[str] = None
    crop_id: Optional[str] = None
    repeat_rule: Optional[RepeatRule] = None
    notes: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[TaskType] = None
    due_datetime: Optional[str] = None
    priority: Optional[int] = None
    assigned_user_id: Optional[str] = None
    crop_id: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[TaskStatus] = None

class TaskComplete(BaseModel):
    notes: Optional[str] = None

class TaskResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    garden_id: str
    crop_id: Optional[str] = None
    title: str
    type: str
    due_datetime: str
    repeat_rule: Optional[dict] = None
    priority: int
    assigned_user_id: Optional[str] = None
    status: str
    completed_at: Optional[str] = None
    notes: Optional[str] = None
    crop_name: Optional[str] = None
    is_overdue: bool = False


# Log Models
class LogCreate(BaseModel):
    crop_id: Optional[str] = None
    date: str
    note: str
    tags: List[str] = []
    photo_urls: List[str] = []

class LogResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    garden_id: str
    crop_id: Optional[str] = None
    date: str
    note: str
    tags: List[str]
    photo_urls: List[str]
    created_by_user_id: str
    crop_name: Optional[str] = None
    user_name: Optional[str] = None


# Inventory Models
class InventoryItemCreate(BaseModel):
    name: str
    category: str
    qty: float
    unit: str
    min_qty: float = 0

class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    qty: Optional[float] = None
    unit: Optional[str] = None
    min_qty: Optional[float] = None

class InventoryItemResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    garden_id: str
    name: str
    category: str
    qty: float
    unit: str
    min_qty: float
    is_low_stock: bool = False


# Harvest Models
class HarvestCreate(BaseModel):
    crop_id: str
    date: str
    qty: float
    unit: str
    destination: HarvestDestination
    price: Optional[float] = None

class HarvestResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    garden_id: str
    crop_id: str
    date: str
    qty: float
    unit: str
    destination: str
    price: Optional[float] = None
    crop_name: Optional[str] = None


# ==================== AUTH HELPERS ====================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise credentials_exception
    return user


# ==================== AUTH ROUTES ====================
@api_router.post("/auth/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if email exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    user_id = str(uuid.uuid4())
    garden_id = str(uuid.uuid4())
    
    # Create user
    user_doc = {
        "id": user_id,
        "name": user_data.name,
        "email": user_data.email,
        "password_hash": get_password_hash(user_data.password),
        "role": UserRole.owner.value,
        "garden_id": garden_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user_doc)
    
    # Create default garden
    garden_doc = {
        "id": garden_id,
        "owner_user_id": user_id,
        "name": "Mi Huerto",
        "location_text": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.gardens.insert_one(garden_doc)
    
    # Create token
    access_token = create_access_token(data={"sub": user_id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "name": user_data.name,
            "email": user_data.email,
            "role": UserRole.owner.value,
            "garden_id": garden_id
        }
    }


@api_router.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    
    access_token = create_access_token(data={"sub": user["id"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"],
            "garden_id": user.get("garden_id")
        }
    }


@api_router.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        name=current_user["name"],
        email=current_user["email"],
        role=current_user["role"],
        garden_id=current_user.get("garden_id"),
        created_at=current_user["created_at"]
    )


# ==================== GARDEN ROUTES ====================
@api_router.get("/garden", response_model=GardenResponse)
async def get_garden(current_user: dict = Depends(get_current_user)):
    garden = await db.gardens.find_one({"id": current_user.get("garden_id")}, {"_id": 0})
    if not garden:
        raise HTTPException(status_code=404, detail="Huerto no encontrado")
    return garden


@api_router.put("/garden", response_model=GardenResponse)
async def update_garden(data: GardenCreate, current_user: dict = Depends(get_current_user)):
    garden_id = current_user.get("garden_id")
    await db.gardens.update_one(
        {"id": garden_id},
        {"$set": {"name": data.name, "location_text": data.location_text}}
    )
    garden = await db.gardens.find_one({"id": garden_id}, {"_id": 0})
    return garden


# ==================== BED ROUTES ====================
@api_router.get("/beds", response_model=List[BedResponse])
async def get_beds(current_user: dict = Depends(get_current_user)):
    garden_id = current_user.get("garden_id")
    beds = await db.beds.find({"garden_id": garden_id}, {"_id": 0}).to_list(100)
    return beds


@api_router.post("/beds", response_model=BedResponse)
async def create_bed(data: BedCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != UserRole.owner.value:
        raise HTTPException(status_code=403, detail="Solo el dueño puede crear camas")
    
    bed_id = str(uuid.uuid4())
    bed_doc = {
        "id": bed_id,
        "garden_id": current_user.get("garden_id"),
        "name": data.name,
        "method": data.method.value,
        "notes": data.notes
    }
    await db.beds.insert_one(bed_doc)
    return BedResponse(**bed_doc)


@api_router.delete("/beds/{bed_id}")
async def delete_bed(bed_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != UserRole.owner.value:
        raise HTTPException(status_code=403, detail="Solo el dueño puede eliminar camas")
    
    result = await db.beds.delete_one({"id": bed_id, "garden_id": current_user.get("garden_id")})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cama no encontrada")
    return {"message": "Cama eliminada"}


# ==================== CROP ROUTES ====================
@api_router.get("/crops", response_model=List[CropResponse])
async def get_crops(
    stage: Optional[str] = None,
    bed_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    garden_id = current_user.get("garden_id")
    query = {"garden_id": garden_id}
    
    if stage:
        query["stage"] = stage
    if bed_id:
        query["bed_id"] = bed_id
    
    crops = await db.crops.find(query, {"_id": 0}).to_list(500)
    
    # Add bed info and filter by search
    beds_map = {}
    beds = await db.beds.find({"garden_id": garden_id}, {"_id": 0}).to_list(100)
    for bed in beds:
        beds_map[bed["id"]] = bed
    
    result = []
    for crop in crops:
        if search and search.lower() not in crop["name"].lower():
            continue
        bed = beds_map.get(crop["bed_id"], {})
        crop["bed_name"] = bed.get("name")
        crop["bed_method"] = bed.get("method")
        result.append(crop)
    
    return result


@api_router.get("/crops/{crop_id}", response_model=CropResponse)
async def get_crop(crop_id: str, current_user: dict = Depends(get_current_user)):
    garden_id = current_user.get("garden_id")
    crop = await db.crops.find_one({"id": crop_id, "garden_id": garden_id}, {"_id": 0})
    if not crop:
        raise HTTPException(status_code=404, detail="Cultivo no encontrado")
    
    bed = await db.beds.find_one({"id": crop["bed_id"]}, {"_id": 0})
    if bed:
        crop["bed_name"] = bed.get("name")
        crop["bed_method"] = bed.get("method")
    
    return crop


@api_router.post("/crops", response_model=CropResponse)
async def create_crop(data: CropCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != UserRole.owner.value:
        raise HTTPException(status_code=403, detail="Solo el dueño puede crear cultivos")
    
    crop_id = str(uuid.uuid4())
    sow_date = datetime.fromisoformat(data.sow_date.replace('Z', '+00:00'))
    target_harvest = sow_date + timedelta(days=data.est_days_to_harvest)
    
    crop_doc = {
        "id": crop_id,
        "garden_id": current_user.get("garden_id"),
        "bed_id": data.bed_id,
        "name": data.name,
        "variety": data.variety,
        "stage": data.stage.value,
        "sow_date": data.sow_date,
        "transplant_date": data.transplant_date,
        "est_days_to_harvest": data.est_days_to_harvest,
        "target_harvest_date": target_harvest.isoformat(),
        "notes": data.notes,
        "is_active": True
    }
    await db.crops.insert_one(crop_doc)
    
    bed = await db.beds.find_one({"id": data.bed_id}, {"_id": 0})
    crop_doc["bed_name"] = bed.get("name") if bed else None
    crop_doc["bed_method"] = bed.get("method") if bed else None
    
    return crop_doc


@api_router.put("/crops/{crop_id}", response_model=CropResponse)
async def update_crop(crop_id: str, data: CropUpdate, current_user: dict = Depends(get_current_user)):
    garden_id = current_user.get("garden_id")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if "stage" in update_data:
        update_data["stage"] = update_data["stage"].value
    
    if update_data:
        await db.crops.update_one(
            {"id": crop_id, "garden_id": garden_id},
            {"$set": update_data}
        )
    
    crop = await db.crops.find_one({"id": crop_id, "garden_id": garden_id}, {"_id": 0})
    if not crop:
        raise HTTPException(status_code=404, detail="Cultivo no encontrado")
    
    bed = await db.beds.find_one({"id": crop["bed_id"]}, {"_id": 0})
    if bed:
        crop["bed_name"] = bed.get("name")
        crop["bed_method"] = bed.get("method")
    
    return crop


@api_router.delete("/crops/{crop_id}")
async def delete_crop(crop_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != UserRole.owner.value:
        raise HTTPException(status_code=403, detail="Solo el dueño puede eliminar cultivos")
    
    result = await db.crops.delete_one({"id": crop_id, "garden_id": current_user.get("garden_id")})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cultivo no encontrado")
    return {"message": "Cultivo eliminado"}


@api_router.post("/crops/{crop_id}/suggest-tasks")
async def suggest_tasks_for_crop(crop_id: str, current_user: dict = Depends(get_current_user)):
    """Create suggested recurring tasks for a crop based on its bed method"""
    garden_id = current_user.get("garden_id")
    crop = await db.crops.find_one({"id": crop_id, "garden_id": garden_id}, {"_id": 0})
    if not crop:
        raise HTTPException(status_code=404, detail="Cultivo no encontrado")
    
    bed = await db.beds.find_one({"id": crop["bed_id"]}, {"_id": 0})
    if not bed:
        raise HTTPException(status_code=404, detail="Cama no encontrada")
    
    tasks_created = []
    now = datetime.now(timezone.utc)
    
    # Riego task based on method
    riego_interval = 1 if bed["method"] == "hidro" else 2
    riego_task = {
        "id": str(uuid.uuid4()),
        "garden_id": garden_id,
        "crop_id": crop_id,
        "title": f"Riego - {crop['name']}",
        "type": TaskType.riego.value,
        "due_datetime": now.isoformat(),
        "repeat_rule": {"type": "custom", "interval": riego_interval},
        "priority": 1,
        "assigned_user_id": None,
        "status": TaskStatus.pendiente.value,
        "completed_at": None,
        "notes": f"Riego cada {riego_interval} día(s)"
    }
    await db.tasks.insert_one(riego_task)
    tasks_created.append(riego_task)
    
    # Fertilization task (weekly)
    fertilizacion_task = {
        "id": str(uuid.uuid4()),
        "garden_id": garden_id,
        "crop_id": crop_id,
        "title": f"Fertilización - {crop['name']}",
        "type": TaskType.fertilizacion.value,
        "due_datetime": now.isoformat(),
        "repeat_rule": {"type": "weekly", "interval": 7},
        "priority": 2,
        "assigned_user_id": None,
        "status": TaskStatus.pendiente.value,
        "completed_at": None,
        "notes": "Fertilización semanal"
    }
    await db.tasks.insert_one(fertilizacion_task)
    tasks_created.append(fertilizacion_task)
    
    return {"message": f"Se crearon {len(tasks_created)} tareas sugeridas", "tasks": tasks_created}


# ==================== TASK ROUTES ====================
@api_router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[str] = None,
    type: Optional[str] = None,
    crop_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    garden_id = current_user.get("garden_id")
    query = {"garden_id": garden_id}
    
    if status:
        query["status"] = status
    if type:
        query["type"] = type
    if crop_id:
        query["crop_id"] = crop_id
    
    tasks = await db.tasks.find(query, {"_id": 0}).to_list(1000)
    
    # Get crops map for names
    crops = await db.crops.find({"garden_id": garden_id}, {"_id": 0}).to_list(500)
    crops_map = {c["id"]: c["name"] for c in crops}
    
    now = datetime.now(timezone.utc)
    result = []
    
    for task in tasks:
        # Check if overdue
        due_dt = datetime.fromisoformat(task["due_datetime"].replace('Z', '+00:00'))
        is_overdue = due_dt < now and task["status"] == TaskStatus.pendiente.value
        
        # Filter by date range
        if date_from:
            from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            if due_dt < from_dt:
                continue
        if date_to:
            to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            if due_dt > to_dt:
                continue
        
        task["crop_name"] = crops_map.get(task.get("crop_id"))
        task["is_overdue"] = is_overdue
        result.append(task)
    
    # Sort by due date
    result.sort(key=lambda x: x["due_datetime"])
    
    return result


@api_router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    garden_id = current_user.get("garden_id")
    task = await db.tasks.find_one({"id": task_id, "garden_id": garden_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    if task.get("crop_id"):
        crop = await db.crops.find_one({"id": task["crop_id"]}, {"_id": 0})
        task["crop_name"] = crop.get("name") if crop else None
    
    now = datetime.now(timezone.utc)
    due_dt = datetime.fromisoformat(task["due_datetime"].replace('Z', '+00:00'))
    task["is_overdue"] = due_dt < now and task["status"] == TaskStatus.pendiente.value
    
    return task


@api_router.post("/tasks", response_model=TaskResponse)
async def create_task(data: TaskCreate, current_user: dict = Depends(get_current_user)):
    task_id = str(uuid.uuid4())
    
    task_doc = {
        "id": task_id,
        "garden_id": current_user.get("garden_id"),
        "crop_id": data.crop_id,
        "title": data.title,
        "type": data.type.value,
        "due_datetime": data.due_datetime,
        "repeat_rule": data.repeat_rule.model_dump() if data.repeat_rule else None,
        "priority": data.priority,
        "assigned_user_id": data.assigned_user_id,
        "status": TaskStatus.pendiente.value,
        "completed_at": None,
        "notes": data.notes
    }
    await db.tasks.insert_one(task_doc)
    
    if data.crop_id:
        crop = await db.crops.find_one({"id": data.crop_id}, {"_id": 0})
        task_doc["crop_name"] = crop.get("name") if crop else None
    
    task_doc["is_overdue"] = False
    return task_doc


@api_router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, data: TaskUpdate, current_user: dict = Depends(get_current_user)):
    garden_id = current_user.get("garden_id")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if "type" in update_data:
        update_data["type"] = update_data["type"].value
    if "status" in update_data:
        update_data["status"] = update_data["status"].value
    
    if update_data:
        await db.tasks.update_one(
            {"id": task_id, "garden_id": garden_id},
            {"$set": update_data}
        )
    
    task = await db.tasks.find_one({"id": task_id, "garden_id": garden_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    if task.get("crop_id"):
        crop = await db.crops.find_one({"id": task["crop_id"]}, {"_id": 0})
        task["crop_name"] = crop.get("name") if crop else None
    
    now = datetime.now(timezone.utc)
    due_dt = datetime.fromisoformat(task["due_datetime"].replace('Z', '+00:00'))
    task["is_overdue"] = due_dt < now and task["status"] == TaskStatus.pendiente.value
    
    return task


@api_router.post("/tasks/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: str, data: TaskComplete, current_user: dict = Depends(get_current_user)):
    garden_id = current_user.get("garden_id")
    task = await db.tasks.find_one({"id": task_id, "garden_id": garden_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    
    now = datetime.now(timezone.utc)
    
    # Update task as completed
    update_data = {
        "status": TaskStatus.completada.value,
        "completed_at": now.isoformat()
    }
    if data.notes:
        update_data["notes"] = (task.get("notes") or "") + f"\n[Completado] {data.notes}"
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    
    # If recurring, create next task
    repeat_rule = task.get("repeat_rule")
    if repeat_rule and repeat_rule.get("type") != "none":
        due_dt = datetime.fromisoformat(task["due_datetime"].replace('Z', '+00:00'))
        
        if repeat_rule["type"] == "daily":
            next_due = due_dt + timedelta(days=1)
        elif repeat_rule["type"] == "weekly":
            next_due = due_dt + timedelta(days=7)
        elif repeat_rule["type"] == "custom" and repeat_rule.get("interval"):
            next_due = due_dt + timedelta(days=repeat_rule["interval"])
        else:
            next_due = None
        
        if next_due:
            new_task = {
                "id": str(uuid.uuid4()),
                "garden_id": garden_id,
                "crop_id": task.get("crop_id"),
                "title": task["title"],
                "type": task["type"],
                "due_datetime": next_due.isoformat(),
                "repeat_rule": repeat_rule,
                "priority": task["priority"],
                "assigned_user_id": task.get("assigned_user_id"),
                "status": TaskStatus.pendiente.value,
                "completed_at": None,
                "notes": task.get("notes", "").split("\n[Completado]")[0] if task.get("notes") else None
            }
            await db.tasks.insert_one(new_task)
    
    # Return updated task
    task = await db.tasks.find_one({"id": task_id, "garden_id": garden_id}, {"_id": 0})
    if task.get("crop_id"):
        crop = await db.crops.find_one({"id": task["crop_id"]}, {"_id": 0})
        task["crop_name"] = crop.get("name") if crop else None
    task["is_overdue"] = False
    
    return task


@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.tasks.delete_one({"id": task_id, "garden_id": current_user.get("garden_id")})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return {"message": "Tarea eliminada"}


# ==================== LOG ROUTES ====================
@api_router.get("/logs", response_model=List[LogResponse])
async def get_logs(
    crop_id: Optional[str] = None,
    tag: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    garden_id = current_user.get("garden_id")
    query = {"garden_id": garden_id}
    
    if crop_id:
        query["crop_id"] = crop_id
    if tag:
        query["tags"] = tag
    
    logs = await db.logs.find(query, {"_id": 0}).sort("date", -1).to_list(500)
    
    # Get crops and users maps
    crops = await db.crops.find({"garden_id": garden_id}, {"_id": 0}).to_list(500)
    crops_map = {c["id"]: c["name"] for c in crops}
    
    users = await db.users.find({"garden_id": garden_id}, {"_id": 0}).to_list(100)
    users_map = {u["id"]: u["name"] for u in users}
    
    for log in logs:
        log["crop_name"] = crops_map.get(log.get("crop_id"))
        log["user_name"] = users_map.get(log.get("created_by_user_id"))
    
    return logs


@api_router.post("/logs", response_model=LogResponse)
async def create_log(data: LogCreate, current_user: dict = Depends(get_current_user)):
    log_id = str(uuid.uuid4())
    
    log_doc = {
        "id": log_id,
        "garden_id": current_user.get("garden_id"),
        "crop_id": data.crop_id,
        "date": data.date,
        "note": data.note,
        "tags": data.tags,
        "photo_urls": data.photo_urls,
        "created_by_user_id": current_user["id"]
    }
    await db.logs.insert_one(log_doc)
    
    if data.crop_id:
        crop = await db.crops.find_one({"id": data.crop_id}, {"_id": 0})
        log_doc["crop_name"] = crop.get("name") if crop else None
    log_doc["user_name"] = current_user["name"]
    
    return log_doc


@api_router.delete("/logs/{log_id}")
async def delete_log(log_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.logs.delete_one({"id": log_id, "garden_id": current_user.get("garden_id")})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    return {"message": "Nota eliminada"}


# ==================== INVENTORY ROUTES ====================
@api_router.get("/inventory", response_model=List[InventoryItemResponse])
async def get_inventory(current_user: dict = Depends(get_current_user)):
    garden_id = current_user.get("garden_id")
    items = await db.inventory_items.find({"garden_id": garden_id}, {"_id": 0}).to_list(500)
    
    for item in items:
        item["is_low_stock"] = item["qty"] <= item["min_qty"]
    
    return items


@api_router.post("/inventory", response_model=InventoryItemResponse)
async def create_inventory_item(data: InventoryItemCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != UserRole.owner.value:
        raise HTTPException(status_code=403, detail="Solo el dueño puede crear items de inventario")
    
    item_id = str(uuid.uuid4())
    
    item_doc = {
        "id": item_id,
        "garden_id": current_user.get("garden_id"),
        "name": data.name,
        "category": data.category,
        "qty": data.qty,
        "unit": data.unit,
        "min_qty": data.min_qty
    }
    await db.inventory_items.insert_one(item_doc)
    item_doc["is_low_stock"] = data.qty <= data.min_qty
    
    return item_doc


@api_router.put("/inventory/{item_id}", response_model=InventoryItemResponse)
async def update_inventory_item(item_id: str, data: InventoryItemUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != UserRole.owner.value:
        raise HTTPException(status_code=403, detail="Solo el dueño puede modificar inventario")
    
    garden_id = current_user.get("garden_id")
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    if update_data:
        await db.inventory_items.update_one(
            {"id": item_id, "garden_id": garden_id},
            {"$set": update_data}
        )
    
    item = await db.inventory_items.find_one({"id": item_id, "garden_id": garden_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    
    item["is_low_stock"] = item["qty"] <= item["min_qty"]
    return item


@api_router.delete("/inventory/{item_id}")
async def delete_inventory_item(item_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != UserRole.owner.value:
        raise HTTPException(status_code=403, detail="Solo el dueño puede eliminar inventario")
    
    result = await db.inventory_items.delete_one({"id": item_id, "garden_id": current_user.get("garden_id")})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    return {"message": "Item eliminado"}


# ==================== HARVEST ROUTES ====================
@api_router.get("/harvests", response_model=List[HarvestResponse])
async def get_harvests(
    crop_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    garden_id = current_user.get("garden_id")
    query = {"garden_id": garden_id}
    
    if crop_id:
        query["crop_id"] = crop_id
    
    harvests = await db.harvests.find(query, {"_id": 0}).sort("date", -1).to_list(500)
    
    # Get crops map
    crops = await db.crops.find({"garden_id": garden_id}, {"_id": 0}).to_list(500)
    crops_map = {c["id"]: c["name"] for c in crops}
    
    for harvest in harvests:
        harvest["crop_name"] = crops_map.get(harvest.get("crop_id"))
    
    return harvests


@api_router.post("/harvests", response_model=HarvestResponse)
async def create_harvest(data: HarvestCreate, current_user: dict = Depends(get_current_user)):
    harvest_id = str(uuid.uuid4())
    
    harvest_doc = {
        "id": harvest_id,
        "garden_id": current_user.get("garden_id"),
        "crop_id": data.crop_id,
        "date": data.date,
        "qty": data.qty,
        "unit": data.unit,
        "destination": data.destination.value,
        "price": data.price
    }
    await db.harvests.insert_one(harvest_doc)
    
    crop = await db.crops.find_one({"id": data.crop_id}, {"_id": 0})
    harvest_doc["crop_name"] = crop.get("name") if crop else None
    
    return harvest_doc


@api_router.delete("/harvests/{harvest_id}")
async def delete_harvest(harvest_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.harvests.delete_one({"id": harvest_id, "garden_id": current_user.get("garden_id")})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cosecha no encontrada")
    return {"message": "Cosecha eliminada"}


# ==================== DASHBOARD / STATS ====================
@api_router.get("/dashboard")
async def get_dashboard(current_user: dict = Depends(get_current_user)):
    garden_id = current_user.get("garden_id")
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = today_start + timedelta(days=7)
    
    # Get all tasks
    tasks = await db.tasks.find({"garden_id": garden_id}, {"_id": 0}).to_list(1000)
    
    # Get crops map
    crops = await db.crops.find({"garden_id": garden_id}, {"_id": 0}).to_list(500)
    crops_map = {c["id"]: c["name"] for c in crops}
    
    today_tasks = []
    week_tasks = []
    pending_count = 0
    
    for task in tasks:
        due_dt = datetime.fromisoformat(task["due_datetime"].replace('Z', '+00:00'))
        task["crop_name"] = crops_map.get(task.get("crop_id"))
        task["is_overdue"] = due_dt < now and task["status"] == TaskStatus.pendiente.value
        
        if task["status"] == TaskStatus.pendiente.value:
            pending_count += 1
            if today_start <= due_dt < today_start + timedelta(days=1):
                today_tasks.append(task)
            elif today_start <= due_dt < week_end:
                week_tasks.append(task)
    
    # Active crops
    active_crops = [c for c in crops if c.get("is_active", True)]
    
    # Crops near harvest (within 7 days)
    near_harvest = []
    for crop in active_crops:
        target = datetime.fromisoformat(crop["target_harvest_date"].replace('Z', '+00:00'))
        if now <= target <= week_end:
            near_harvest.append(crop)
    
    # Low stock inventory
    inventory = await db.inventory_items.find({"garden_id": garden_id}, {"_id": 0}).to_list(500)
    low_stock = [item for item in inventory if item["qty"] <= item["min_qty"]]
    
    # Harvests this week
    harvests = await db.harvests.find({"garden_id": garden_id}, {"_id": 0}).to_list(500)
    week_harvests = []
    for h in harvests:
        h_date = datetime.fromisoformat(h["date"].replace('Z', '+00:00'))
        if today_start <= h_date < week_end:
            h["crop_name"] = crops_map.get(h.get("crop_id"))
            week_harvests.append(h)
    
    return {
        "today_tasks": sorted(today_tasks, key=lambda x: x["due_datetime"])[:10],
        "week_tasks": sorted(week_tasks, key=lambda x: x["due_datetime"])[:10],
        "active_crops_count": len(active_crops),
        "pending_tasks_count": pending_count,
        "near_harvest_crops": near_harvest[:5],
        "low_stock_items": low_stock[:5],
        "week_harvests": week_harvests[:5]
    }


@api_router.get("/reports")
async def get_reports(current_user: dict = Depends(get_current_user)):
    garden_id = current_user.get("garden_id")
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    
    # Get all harvests
    harvests = await db.harvests.find({"garden_id": garden_id}, {"_id": 0}).to_list(1000)
    
    # Get crops map
    crops = await db.crops.find({"garden_id": garden_id}, {"_id": 0}).to_list(500)
    crops_map = {c["id"]: c["name"] for c in crops}
    
    # Filter last 30 days
    recent_harvests = []
    for h in harvests:
        h_date = datetime.fromisoformat(h["date"].replace('Z', '+00:00'))
        if h_date >= thirty_days_ago:
            h["crop_name"] = crops_map.get(h.get("crop_id"))
            recent_harvests.append(h)
    
    # Total by crop
    by_crop = {}
    total_sales = 0
    for h in recent_harvests:
        crop_name = h.get("crop_name", "Sin nombre")
        if crop_name not in by_crop:
            by_crop[crop_name] = {"qty": 0, "unit": h["unit"], "sales": 0}
        by_crop[crop_name]["qty"] += h["qty"]
        if h.get("price") and h["destination"] == "venta":
            by_crop[crop_name]["sales"] += h["qty"] * h["price"]
            total_sales += h["qty"] * h["price"]
    
    # Top 5 crops
    top_crops = sorted(by_crop.items(), key=lambda x: x[1]["qty"], reverse=True)[:5]
    
    return {
        "period": "30 días",
        "total_harvests": len(recent_harvests),
        "by_crop": by_crop,
        "top_crops": [{"name": name, **data} for name, data in top_crops],
        "total_sales": total_sales
    }


# ==================== SEED DATA ====================
@api_router.post("/seed")
async def seed_demo_data(current_user: dict = Depends(get_current_user)):
    """Create demo data for the garden"""
    garden_id = current_user.get("garden_id")
    user_id = current_user["id"]
    
    # Update garden name
    await db.gardens.update_one(
        {"id": garden_id},
        {"$set": {"name": "Huerto Casa", "location_text": "Patio trasero"}}
    )
    
    # Clear existing data
    await db.beds.delete_many({"garden_id": garden_id})
    await db.crops.delete_many({"garden_id": garden_id})
    await db.tasks.delete_many({"garden_id": garden_id})
    await db.logs.delete_many({"garden_id": garden_id})
    await db.inventory_items.delete_many({"garden_id": garden_id})
    await db.harvests.delete_many({"garden_id": garden_id})
    
    now = datetime.now(timezone.utc)
    
    # Create beds
    beds_data = [
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "name": "Mesa Hidro 1", "method": "hidro", "notes": "Sistema NFT con 20 espacios"},
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "name": "Cama Tierra A", "method": "suelo", "notes": "3m x 1m, tierra abonada"},
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "name": "Cama Tierra B", "method": "suelo", "notes": "2m x 1m, semi-sombra"}
    ]
    await db.beds.insert_many(beds_data)
    
    # Create crops
    crops_data = [
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "bed_id": beds_data[0]["id"],
            "name": "Lechuga Romana", "variety": "Parris Island", "stage": "vegetativo",
            "sow_date": (now - timedelta(days=20)).isoformat(),
            "transplant_date": (now - timedelta(days=10)).isoformat(),
            "est_days_to_harvest": 45, "target_harvest_date": (now + timedelta(days=25)).isoformat(),
            "notes": "Creciendo bien, hojas verdes", "is_active": True
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "bed_id": beds_data[0]["id"],
            "name": "Bok Choy", "variety": "Baby Bok Choy", "stage": "vegetativo",
            "sow_date": (now - timedelta(days=15)).isoformat(),
            "transplant_date": None,
            "est_days_to_harvest": 30, "target_harvest_date": (now + timedelta(days=15)).isoformat(),
            "notes": None, "is_active": True
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "bed_id": beds_data[1]["id"],
            "name": "Cilantrillo", "variety": "Slow Bolt", "stage": "germinación",
            "sow_date": (now - timedelta(days=5)).isoformat(),
            "transplant_date": None,
            "est_days_to_harvest": 40, "target_harvest_date": (now + timedelta(days=35)).isoformat(),
            "notes": "Sembrado directo", "is_active": True
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "bed_id": beds_data[1]["id"],
            "name": "Albahaca", "variety": "Genovese", "stage": "vegetativo",
            "sow_date": (now - timedelta(days=30)).isoformat(),
            "transplant_date": (now - timedelta(days=15)).isoformat(),
            "est_days_to_harvest": 60, "target_harvest_date": (now + timedelta(days=30)).isoformat(),
            "notes": "Lista para primer corte", "is_active": True
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "bed_id": beds_data[2]["id"],
            "name": "Recao", "variety": "Culantro", "stage": "cosecha",
            "sow_date": (now - timedelta(days=60)).isoformat(),
            "transplant_date": None,
            "est_days_to_harvest": 75, "target_harvest_date": (now + timedelta(days=5)).isoformat(),
            "notes": "Hojas grandes, listo para cosechar", "is_active": True
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "bed_id": beds_data[2]["id"],
            "name": "Tomate", "variety": "Cherry", "stage": "vegetativo",
            "sow_date": (now - timedelta(days=45)).isoformat(),
            "transplant_date": (now - timedelta(days=25)).isoformat(),
            "est_days_to_harvest": 90, "target_harvest_date": (now + timedelta(days=45)).isoformat(),
            "notes": "Empezando a florecer", "is_active": True
        }
    ]
    await db.crops.insert_many(crops_data)
    
    # Create tasks (recurring + punctual)
    tasks_data = [
        # Recurring - Riego hidro (daily)
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[0]["id"],
            "title": "Riego - Lechuga Romana", "type": "riego",
            "due_datetime": now.isoformat(),
            "repeat_rule": {"type": "custom", "interval": 1},
            "priority": 1, "assigned_user_id": None, "status": "pendiente", "completed_at": None,
            "notes": "Revisar nivel de agua y pH"
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[1]["id"],
            "title": "Riego - Bok Choy", "type": "riego",
            "due_datetime": now.isoformat(),
            "repeat_rule": {"type": "custom", "interval": 1},
            "priority": 1, "assigned_user_id": None, "status": "pendiente", "completed_at": None,
            "notes": None
        },
        # Recurring - Riego suelo (every 2 days)
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[2]["id"],
            "title": "Riego - Cilantrillo", "type": "riego",
            "due_datetime": (now + timedelta(days=1)).isoformat(),
            "repeat_rule": {"type": "custom", "interval": 2},
            "priority": 1, "assigned_user_id": None, "status": "pendiente", "completed_at": None,
            "notes": None
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[3]["id"],
            "title": "Riego - Albahaca", "type": "riego",
            "due_datetime": now.isoformat(),
            "repeat_rule": {"type": "custom", "interval": 2},
            "priority": 1, "assigned_user_id": None, "status": "pendiente", "completed_at": None,
            "notes": None
        },
        # Recurring - Fertilization (weekly)
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": None,
            "title": "Fertilización general - Hidro", "type": "fertilización",
            "due_datetime": (now + timedelta(days=3)).isoformat(),
            "repeat_rule": {"type": "weekly", "interval": 7},
            "priority": 2, "assigned_user_id": None, "status": "pendiente", "completed_at": None,
            "notes": "Mezcla A+B según dosificación"
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": None,
            "title": "Fertilización - Camas Tierra", "type": "fertilización",
            "due_datetime": (now + timedelta(days=5)).isoformat(),
            "repeat_rule": {"type": "weekly", "interval": 7},
            "priority": 2, "assigned_user_id": None, "status": "pendiente", "completed_at": None,
            "notes": "Fertilizante orgánico"
        },
        # Punctual tasks
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[2]["id"],
            "title": "Trasplante - Cilantrillo", "type": "trasplante",
            "due_datetime": (now + timedelta(days=10)).isoformat(),
            "repeat_rule": None,
            "priority": 2, "assigned_user_id": None, "status": "pendiente", "completed_at": None,
            "notes": "Mover plántulas más fuertes"
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[4]["id"],
            "title": "Cosecha - Recao", "type": "cosecha",
            "due_datetime": (now + timedelta(days=2)).isoformat(),
            "repeat_rule": None,
            "priority": 1, "assigned_user_id": None, "status": "pendiente", "completed_at": None,
            "notes": "Cosechar hojas externas"
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[5]["id"],
            "title": "Poda - Tomate", "type": "poda",
            "due_datetime": (now + timedelta(days=4)).isoformat(),
            "repeat_rule": None,
            "priority": 2, "assigned_user_id": None, "status": "pendiente", "completed_at": None,
            "notes": "Remover chupones laterales"
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[0]["id"],
            "title": "Revisar pH - Sistema Hidro", "type": "otro",
            "due_datetime": (now + timedelta(days=1)).isoformat(),
            "repeat_rule": None,
            "priority": 1, "assigned_user_id": None, "status": "pendiente", "completed_at": None,
            "notes": "pH ideal: 5.8-6.2"
        },
        # Overdue task
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[3]["id"],
            "title": "Aplicar neem - Albahaca", "type": "otro",
            "due_datetime": (now - timedelta(days=2)).isoformat(),
            "repeat_rule": None,
            "priority": 1, "assigned_user_id": None, "status": "pendiente", "completed_at": None,
            "notes": "Prevención de plagas"
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[1]["id"],
            "title": "Cosecha - Bok Choy", "type": "cosecha",
            "due_datetime": (now + timedelta(days=15)).isoformat(),
            "repeat_rule": None,
            "priority": 2, "assigned_user_id": None, "status": "pendiente", "completed_at": None,
            "notes": None
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[0]["id"],
            "title": "Cosecha - Lechuga Romana", "type": "cosecha",
            "due_datetime": (now + timedelta(days=25)).isoformat(),
            "repeat_rule": None,
            "priority": 2, "assigned_user_id": None, "status": "pendiente", "completed_at": None,
            "notes": "Cosechar por la mañana"
        }
    ]
    await db.tasks.insert_many(tasks_data)
    
    # Create logs
    logs_data = [
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[0]["id"],
            "date": (now - timedelta(days=5)).isoformat(), "note": "Las lechugas están creciendo muy bien, hojas verdes y crujientes.",
            "tags": ["crecimiento"], "photo_urls": ["https://images.unsplash.com/photo-1622206151226-18ca2c9ab4a1?w=400"],
            "created_by_user_id": user_id
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[3]["id"],
            "date": (now - timedelta(days=4)).isoformat(), "note": "Detecté algunos áfidos en la albahaca. Aplicaré aceite de neem mañana.",
            "tags": ["plaga"], "photo_urls": [],
            "created_by_user_id": user_id
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[5]["id"],
            "date": (now - timedelta(days=3)).isoformat(), "note": "Los tomates cherry empezaron a florecer. Primeras flores amarillas visibles.",
            "tags": ["crecimiento"], "photo_urls": ["https://images.unsplash.com/photo-1592841200221-a6898f307baa?w=400"],
            "created_by_user_id": user_id
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": None,
            "date": (now - timedelta(days=3)).isoformat(), "note": "Día muy caluroso, aumenté la frecuencia de riego en las camas de tierra.",
            "tags": ["clima", "riego"], "photo_urls": [],
            "created_by_user_id": user_id
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[1]["id"],
            "date": (now - timedelta(days=2)).isoformat(), "note": "El bok choy se ve un poco amarillento. Revisaré los nutrientes.",
            "tags": ["nutrición"], "photo_urls": ["https://images.unsplash.com/photo-1540420773420-3366772f4999?w=400"],
            "created_by_user_id": user_id
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[4]["id"],
            "date": (now - timedelta(days=2)).isoformat(), "note": "El recao tiene hojas grandes y aromáticas. Listo para primera cosecha.",
            "tags": ["crecimiento", "cosecha"], "photo_urls": [],
            "created_by_user_id": user_id
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[2]["id"],
            "date": (now - timedelta(days=1)).isoformat(), "note": "Las semillas de cilantro están germinando, se ven los primeros brotes.",
            "tags": ["crecimiento"], "photo_urls": [],
            "created_by_user_id": user_id
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": None,
            "date": (now - timedelta(days=1)).isoformat(), "note": "Ajusté el pH del sistema hidropónico a 6.0. Estaba en 6.5.",
            "tags": ["nutrición"], "photo_urls": [],
            "created_by_user_id": user_id
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[0]["id"],
            "date": now.isoformat(), "note": "Mediciones del día: EC 1.2, pH 6.0. Todo en rango óptimo.",
            "tags": ["nutrición"], "photo_urls": [],
            "created_by_user_id": user_id
        },
        {
            "id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": None,
            "date": now.isoformat(), "note": "Lluvia ligera por la tarde. No fue necesario regar las camas de tierra.",
            "tags": ["clima", "riego"], "photo_urls": [],
            "created_by_user_id": user_id
        }
    ]
    await db.logs.insert_many(logs_data)
    
    # Create inventory items
    inventory_data = [
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "name": "Semillas Lechuga", "category": "semillas", "qty": 50, "unit": "unidades", "min_qty": 20},
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "name": "Semillas Tomate Cherry", "category": "semillas", "qty": 30, "unit": "unidades", "min_qty": 15},
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "name": "Nutriente A (Flora)", "category": "nutrientes", "qty": 500, "unit": "ml", "min_qty": 200},
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "name": "Nutriente B (Flora)", "category": "nutrientes", "qty": 450, "unit": "ml", "min_qty": 200},
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "name": "Sustrato Coco", "category": "sustrato", "qty": 5, "unit": "kg", "min_qty": 10},  # LOW STOCK
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "name": "Perlita", "category": "sustrato", "qty": 2, "unit": "kg", "min_qty": 5},  # LOW STOCK
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "name": "Aceite de Neem", "category": "herramientas", "qty": 100, "unit": "ml", "min_qty": 50},
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "name": "pH Down", "category": "nutrientes", "qty": 200, "unit": "ml", "min_qty": 100}
    ]
    await db.inventory_items.insert_many(inventory_data)
    
    # Create harvests
    harvests_data = [
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[0]["id"], "date": (now - timedelta(days=20)).isoformat(), "qty": 0.5, "unit": "kg", "destination": "casa", "price": None},
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[3]["id"], "date": (now - timedelta(days=15)).isoformat(), "qty": 0.2, "unit": "kg", "destination": "casa", "price": None},
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[4]["id"], "date": (now - timedelta(days=12)).isoformat(), "qty": 0.3, "unit": "kg", "destination": "venta", "price": 5.00},
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[0]["id"], "date": (now - timedelta(days=10)).isoformat(), "qty": 0.8, "unit": "kg", "destination": "venta", "price": 3.50},
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[3]["id"], "date": (now - timedelta(days=8)).isoformat(), "qty": 0.15, "unit": "kg", "destination": "casa", "price": None},
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[4]["id"], "date": (now - timedelta(days=5)).isoformat(), "qty": 0.25, "unit": "kg", "destination": "venta", "price": 5.00},
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[0]["id"], "date": (now - timedelta(days=3)).isoformat(), "qty": 0.6, "unit": "kg", "destination": "casa", "price": None},
        {"id": str(uuid.uuid4()), "garden_id": garden_id, "crop_id": crops_data[3]["id"], "date": (now - timedelta(days=1)).isoformat(), "qty": 0.1, "unit": "kg", "destination": "venta", "price": 8.00}
    ]
    await db.harvests.insert_many(harvests_data)
    
    return {
        "message": "Datos demo creados exitosamente",
        "created": {
            "beds": len(beds_data),
            "crops": len(crops_data),
            "tasks": len(tasks_data),
            "logs": len(logs_data),
            "inventory_items": len(inventory_data),
            "harvests": len(harvests_data)
        }
    }


# ==================== ROOT ====================
@api_router.get("/")
async def root():
    return {"message": "Mi Siembra Inteligente API", "version": "1.0.0"}


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
