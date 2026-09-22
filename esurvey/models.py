from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password: Mapped[str] = mapped_column(String(255))

class Business(Base):
    __tablename__ = 'businesses'
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    name: Mapped[str] = mapped_column(String(120))
    industry: Mapped[str] = mapped_column(String(60), default='Restaurant')

class Survey(Base):
    __tablename__ = 'surveys'
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey('businesses.id'), index=True)
    title: Mapped[str] = mapped_column(String(150))
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    description: Mapped[str] = mapped_column(Text, default='Tell us what worked and what we can do better.')
    categories: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default='active')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Review(Base):
    __tablename__ = 'reviews'
    __table_args__ = (UniqueConstraint('survey_id', 'submission_key'), Index('ix_review_business_date', 'business_id', 'created_at'))
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey('businesses.id'))
    survey_id: Mapped[int] = mapped_column(ForeignKey('surveys.id'), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String(80))
    comment: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(String(100), default='Anonymous')
    status: Mapped[str] = mapped_column(String(20), default='new')
    submission_key: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Action(Base):
    __tablename__ = 'actions'
    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey('businesses.id'), index=True)
    title: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default='planned')
    priority: Mapped[str] = mapped_column(String(20), default='medium')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class RateLimit(Base):
    __tablename__ = 'rate_limits'
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(default=1)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
