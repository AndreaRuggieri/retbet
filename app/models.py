# app/models.py
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List, Dict

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    Date,
    ForeignKey,
    UniqueConstraint,
    JSON,
)
from sqlalchemy import Date, UniqueConstraint

from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


# -----------------------------
# Master data
# -----------------------------
class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)        # "Italy"
    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)     # "ITA"


class Competition(Base):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), nullable=False)
    division: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=Serie A, 2=Serie B ...

    country: Mapped["Country"] = relationship()


class Season(Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)  # "2025-2026"

    competition: Mapped["Competition"] = relationship()

    __table_args__ = (
        UniqueConstraint("competition_id", "name", name="uq_season_comp_name"),
    )


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    crest_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    extras: Mapped[Dict] = mapped_column(JSON, default=dict)  # ✅ callable


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)

    first_name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    last_name: Mapped[str] = mapped_column(String, index=True, nullable=False)

    country_id: Mapped[Optional[int]] = mapped_column(ForeignKey("countries.id"), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    age_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    macro_role: Mapped[Optional[str]] = mapped_column(String, nullable=True)     # GK/DF/MF/ST
    micro_roles: Mapped[List[str]] = mapped_column(JSON, default=list)          # ✅ callable

    # current_team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"), nullable=True)
    jersey_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    extras: Mapped[Dict] = mapped_column(JSON, default=dict)  # ✅ callable

    country: Mapped[Optional["Country"]] = relationship()
    current_team_season_id: Mapped[int | None] = mapped_column(
        ForeignKey("team_seasons.id"), nullable=True
    )

    current_team_season: Mapped["TeamSeason | None"] = relationship()



# -----------------------------
# Match + events
# -----------------------------
class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False)
    matchday: Mapped[int] = mapped_column(Integer, nullable=False)
    kickoff: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)

    referee: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    extras: Mapped[Dict] = mapped_column(JSON, default=dict)  # ✅ callable

    # campi denormalizzati + risultato
    home_team_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    away_team_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    home_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    away_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # relazioni utili
    season: Mapped["Season"] = relationship()
    home_team: Mapped["Team"] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship(foreign_keys=[away_team_id])

    goals: Mapped[List["Goal"]] = relationship(
        "Goal",
        back_populates="match",
        cascade="all, delete-orphan",
    )

    cards: Mapped[List["Card"]] = relationship(
        "Card",
        back_populates="match",
        cascade="all, delete-orphan",
    )


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)

    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)

    scorer_player_id: Mapped[Optional[int]] = mapped_column(ForeignKey("players.id"), nullable=True)
    assist_player_id: Mapped[Optional[int]] = mapped_column(ForeignKey("players.id"), nullable=True)

    minute: Mapped[int] = mapped_column(Integer, nullable=False)
    period: Mapped[str] = mapped_column(String, nullable=False)      # "1T","2T"
    goal_type: Mapped[str] = mapped_column(String, nullable=False)   # "open_play","penalty","free_kick","own_goal"

    extras: Mapped[Dict] = mapped_column(JSON, default=dict)  # ✅ callable

    match: Mapped["Match"] = relationship("Match", back_populates="goals")
    team: Mapped["Team"] = relationship()

    scorer: Mapped[Optional["Player"]] = relationship("Player", foreign_keys=[scorer_player_id])
    assist: Mapped[Optional["Player"]] = relationship("Player", foreign_keys=[assist_player_id])


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)

    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    player_id: Mapped[Optional[int]] = mapped_column(ForeignKey("players.id"), nullable=True)

    minute: Mapped[int] = mapped_column(Integer, nullable=False)
    period: Mapped[str] = mapped_column(String, nullable=False)
    card_type: Mapped[str] = mapped_column(String, nullable=False)  # "yellow","red","second_yellow"

    extras: Mapped[Dict] = mapped_column(JSON, default=dict)  # ✅ callable

    match: Mapped["Match"] = relationship("Match", back_populates="cards")
    team: Mapped["Team"] = relationship()
    player: Mapped[Optional["Player"]] = relationship()


class TeamSeason(Base):
    __tablename__ = "team_seasons"

    id: Mapped[int] = mapped_column(primary_key=True)

    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False)

    team: Mapped["Team"] = relationship()
    season: Mapped["Season"] = relationship()

    __table_args__ = (
        UniqueConstraint("team_id", "season_id", name="uq_team_season"),
    )
