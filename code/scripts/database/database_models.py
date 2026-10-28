from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "DB" / "basketbal_da.db"
DB_PATH.parent.mkdir(exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH.as_posix()}", echo=False)
Base = declarative_base()


class Players(Base):
    __tablename__ = "players"

    # Columns
    player_id = Column(String, primary_key=True)
    name = Column(String)
    birth_date = Column(Date)
    height_cm = Column(Float)
    weight_kg = Column(Float)
    birth_country = Column(String)

    # Relationships
    season_stats = relationship("Player_of_season", back_populates="player")
    mvp_votes = relationship("Mvp_Votes", back_populates="player")
    experiences = relationship("Experience", back_populates="player")


class Team(Base):
    __tablename__ = "team"

    # Columns
    team_id = Column(Integer, primary_key=True)
    team_label = Column(String)

    # Relationships
    season_stats = relationship("Player_of_season", back_populates="team")
    champions = relationship("Champions", back_populates="team", uselist=False)
    experiences = relationship("Experience", back_populates="team")


class Position(Base):
    __tablename__ = "positions"

    # Columns
    position_id = Column(Integer, primary_key=True)
    position = Column(String)

    # Relationships
    season_stats = relationship("Player_of_season", back_populates="position")


class Season(Base):
    __tablename__ = "seasons"

    # Columns
    season_id = Column(Integer, primary_key=True)
    season = Column(Integer, nullable=False)

    # Relationships
    player_stats = relationship("Player_of_season", back_populates="season")
    mvp_votes = relationship("Mvp_Votes", back_populates="season")
    champions = relationship("Champions", back_populates="season", uselist=False)
    experiences = relationship("Experience", back_populates="season")


class Player_of_season(Base):
    __tablename__ = "player_season"

    # Columns
    player_season_id = Column(Integer, primary_key=True)

    season_id = Column(Integer, ForeignKey("seasons.season_id"), nullable=False)
    player_id = Column(String, ForeignKey("players.player_id"), nullable=False)
    team_id = Column(Integer, ForeignKey("team.team_id"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.position_id"), nullable=False)
    is_total = Column(Boolean)
    age = Column(Integer)
    games = Column(Integer)
    games_started = Column(Integer)
    minutes_per_game = Column(Float)
    field_goals_per_game = Column(Float)
    field_goal_attempts_per_game = Column(Float)
    field_goal_pct = Column(Float)
    three_pointers_per_game = Column(Float)
    three_point_attempts_per_game = Column(Float)
    three_point_pct = Column(Float)
    two_pointers_per_game = Column(Float)
    two_point_attempts_per_game = Column(Float)
    two_point_pct = Column(Float)
    effective_field_goal_pct = Column(Float)
    free_throws_per_game = Column(Float)
    free_throw_attempts_per_game = Column(Float)
    free_throw_pct = Column(Float)
    offensive_rebounds_per_game = Column(Float)
    defensive_rebounds_per_game = Column(Float)
    rebounds_per_game = Column(Float)
    assists_per_game = Column(Float)
    steals_per_game = Column(Float)
    blocks_per_game = Column(Float)
    turnovers_per_game = Column(Float)
    personal_fouls_per_game = Column(Float)
    points_per_game = Column(Float)
    per = Column(Float)
    true_shooting_pct = Column(Float)
    usage_pct = Column(Float)
    ws = Column(Float)
    ws_per_48 = Column(Float)
    bpm = Column(Float)
    vorp = Column(Float)

    # Relationships
    player = relationship("Players", back_populates="season_stats")
    season = relationship("Season", back_populates="player_stats")
    team = relationship("Team", back_populates="season_stats")
    position = relationship("Position", back_populates="season_stats")


class Champions(Base):
    __tablename__ = "champions"

    # Columns
    season_id = Column(Integer, ForeignKey("seasons.season_id"), primary_key=True)
    team_id = Column(Integer, ForeignKey("team.team_id"), primary_key=True)

    # Relationships
    season = relationship("Season", back_populates="champions")
    team = relationship("Team", back_populates="champions")


class Mvp_Votes(Base):
    __tablename__ = "mvp_votes"

    # Columns
    mvp_id = Column(Integer, primary_key=True)
    season_id = Column(Integer, ForeignKey("seasons.season_id"), nullable=False)
    player_id = Column(String, ForeignKey("players.player_id"), nullable=False)
    rank = Column(Integer)
    first_place_votes = Column(Integer)
    points_won = Column(Integer)
    points_max = Column(Integer)
    vote_share = Column(Float)

    # Relationships
    player = relationship("Players", back_populates="mvp_votes")
    season = relationship("Season", back_populates="mvp_votes")


class Experience(Base):
    __tablename__ = "experience"

    # Columns
    experience_id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("team.team_id"), nullable=False)
    player_id = Column(String, ForeignKey("players.player_id"), nullable=False)
    season_id = Column(Integer, ForeignKey("seasons.season_id"), nullable=False)
    experience_years = Column(Integer)

    # Relationships
    player = relationship("Players", back_populates="experiences")
    team = relationship("Team", back_populates="experiences")
    season = relationship("Season", back_populates="experiences")


Base.metadata.create_all(engine)
