from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Имя файла базы данных (вот именно ЭТОТ файл можно удалять для сброса)
DATABASE_URL = "sqlite:///./aperture.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    guest_id = Column(String, default="guest")
    wallet = Column(String, unique=True, index=True)
    balance = Column(Float, default=0.0)
    is_demo = Column(Boolean, default=False)

# Создаем таблицы, если их нет
Base.metadata.create_all(bind=engine)