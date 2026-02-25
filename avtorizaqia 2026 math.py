# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from passlib.context import CryptContext
from datetime import datetime, timedelta

# Настройки JWT
SECRET_KEY = "your-secret-key"  # рекомендуется заменить на безопасный ключ из переменной окружения
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# База данных
DATABASE_URL = "sqlite:///./egetest.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модели БД
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Progress(Base):
    __tablename__ = "progress"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    task_id = Column(Integer)
    solved = Column(Integer, default=0)  # 0/1

Base.metadata.create_all(bind=engine)

# Безопасность
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="ЕГЭ 2026: профильная математика - тренажёр (с авторизацией)")

# Pydantic модели
class UserCreate(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Невалидный токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    with SessionLocal() as db:
        user = get_user(db, username)
        if user is None:
            raise credentials_exception
        return user

# Основные эндпойнты
@app.post("/register")
def register(user_in: UserCreate):
    with SessionLocal() as db:
        if get_user(db, user_in.username):
            raise HTTPException(status_code=400, detail="Пользователь уже существует")
        user = User(
            username=user_in.username,
            hashed_password=get_password_hash(user_in.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"msg": "Пользователь зарегистрирован"}

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    with SessionLocal() as db:
        user = authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверное имя пользователя или пароль",
                headers={"WWW-Authenticate": "Bearer"},
            )
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=timedelta(minutes=60)
        )
        return {"access_token": access_token, "token_type": "bearer"}

# Защищённый пример: прогресс по задачам
class ProgressInput(BaseModel):
    task_id: int
    solved: int  # 0/1

@app.post("/progress")
def set_progress(pl: ProgressInput, current_user: User = Depends(get_current_user)):
    with SessionLocal() as db:
        # простой upsert
        existing = db.query(Progress).filter(
            Progress.user_id == current_user.id, Progress.task_id == pl.task_id
        ).first()
        if existing:
            existing.solved = pl.solved
        else:
            new = Progress(user_id=current_user.id, task_id=pl.task_id, solved=pl.solved)
            db.add(new)
        db.commit()
        return {"ok": True, "task_id": pl.task_id, "solved": pl.solved}

# Простой тестовый защищённый эндпойнт
@app.get("/me")
def read_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "id": current_user.id}

# Простой фронтенд (то же минимальное представление задач, без изменений)
HTML_PAGE = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8" />
<title>Тренажёр ЕГЭ 2026 (с авторизацией)</title>
</head>
<body>
<h1>Добро пожаловать в тренажер ЕГЭ 2026 (JWT-авторизация)</h1>
<p>Используйте /register для регистрации и /token для входа.</p>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
