import uuid
from datetime import datetime
from typing import List, Optional

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint


# NOTE: These models replace the previous Image/ShareableLink/Vote/Comment schema.
# Run the latest Alembic migration before starting the app:
#   alembic upgrade head


class User(SQLModel, table=True):
    """Facebook-authenticated user, keyed by Facebook user_id."""
    __tablename__ = "fb_user"

    id: str = Field(primary_key=True)           # Facebook user_id, e.g. "123456789"
    name: str
    email: Optional[str] = Field(default=None)
    picture_url: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Updated every time the user authenticates — shows who accessed the link and when.
    last_seen_at: Optional[datetime] = Field(default=None)

    posts: List["Post"] = Relationship(back_populates="creator")
    votes: List["Vote"] = Relationship(back_populates="voter")


class Post(SQLModel, table=True):
    """A photo collection created by a user. Identified externally by shareable_code."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    creator_id: str = Field(foreign_key="fb_user.id")
    shareable_code: str = Field(unique=True)                   # random token used in share URL
    facebook_post_id: Optional[str] = Field(default=None)     # FB post ID if published to Facebook
    caption: Optional[str] = Field(default=None)              # optional caption shown on the post
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Denormalised counter — incremented atomically when a vote is cast.
    # Accurate at a glance without counting Vote rows.
    total_votes: int = Field(default=0)

    creator: Optional[User] = Relationship(back_populates="posts")
    photos: List["Photo"] = Relationship(back_populates="post")
    votes: List["Vote"] = Relationship(back_populates="post")


class Photo(SQLModel, table=True):
    """A single image within a Post."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    post_id: str = Field(foreign_key="post.id")
    media_url: str                                             # Full S3 URL (display / presign source)
    # Unique S3 object key (e.g. "uploads/abc123.jpg").
    # This is the stable, unique marker that ties every vote row to exactly one physical photo,
    # independent of bucket name, region, or URL format changes.
    s3_key: Optional[str] = Field(default=None, unique=True)
    facebook_media_id: Optional[str] = Field(default=None)   # FB photo object ID if staged on FB
    position: int = Field(default=0)                          # ordering within the post
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Denormalised counter — incremented atomically with the Vote insert.
    # Shows per-photo vote totals directly in the DB without aggregation.
    vote_count: int = Field(default=0)

    post: Optional[Post] = Relationship(back_populates="photos")
    votes_received: List["Vote"] = Relationship(back_populates="photo")


class Vote(SQLModel, table=True):
    """
    One vote per authenticated user per post.
    Source of truth for all voting data.
    Records which photo the voter selected and an optional free-text comment.
    The photo is identified by both photo_id (FK) and the photo's s3_key (via JOIN)
    ensuring accuracy even if URLs change.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    post_id: str = Field(foreign_key="post.id")
    photo_id: str = Field(foreign_key="photo.id")             # photo the voter selected
    voter_id: str = Field(foreign_key="fb_user.id")
    comment: Optional[str] = Field(default=None)              # optional comment (max 1000 chars)
    voted_at: datetime = Field(default_factory=datetime.utcnow)
    # Legacy column kept NOT NULL in DB — always written on insert for backward compatibility
    created_at: datetime = Field(default_factory=datetime.utcnow)

    post: Optional[Post] = Relationship(back_populates="votes")
    photo: Optional[Photo] = Relationship(back_populates="votes_received")
    voter: Optional[User] = Relationship(back_populates="votes")

    __table_args__ = (
        UniqueConstraint("post_id", "voter_id", name="uq_one_vote_per_user_per_post"),
    )
