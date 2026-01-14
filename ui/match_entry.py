import sys
from pathlib import Path
from datetime import datetime
import datetime as dt

import streamlit as st
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[1]  # ...\retbet
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, engine
from app.models import Base, Competition, Season, Team, Player, Match, Goal, Country

Base.metadata.create_all(bind=engine)

st.set_page_config(page_title="Inserimento Partite", layout="wide")
st.title("📥 Inserimento partita")

db = SessionLocal()


# ---------------- Utils ----------------
def get_or_create_country(name: str, code: str):
    name = (name or "").strip()
    code = (code or "").strip().upper()

    if not name or not code:
        return None

    # match sicuro su code (UNIQUE)
    existing = db.query(Country).filter(Country.code == code).first()
    if existing:
        return existing

    # match su nome
    existing = db.query(Country).filter(Country.name == name).first()
    if existing:
        return existing

    try:
        c = Country(name=name, code=code)
        db.add(c)
        db.commit()
        db.refresh(c)
        return c
    except IntegrityError:
        db.rollback()
        return db.query(Country).filter(Country.code == code).first()


def get_or_create(model, **kwargs):
    obj = db.query(model).filter_by(**kwargs).first()
    if obj:
        return obj
    obj = model(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def compute_live_score(goals, home_id, away_id):
    hs, as_ = 0, 0
    for g in goals:
        player_team_id = g["player_team_id"]
        is_og = g["goal_type"] == "own_goal"
        goal_team_id = (home_id if player_team_id == away_id else away_id) if is_og else player_team_id
        if goal_team_id == home_id:
            hs += 1
        elif goal_team_id == away_id:
            as_ += 1
    return hs, as_


# ---------------- Sidebar: setup rapido ----------------
with st.sidebar:
    st.header("Setup rapido")

    comp_name = st.text_input("Competizione (es. Serie A)", value="Serie A")
    season_name = st.text_input("Stagione (es. 2025-2026)", value="2025-2026")

    st.subheader("Paese competizione (obbligatorio)")
    countries = db.query(Country).order_by(Country.name).all()

    country_id_options = [0] + [c.id for c in countries]
    country_id_to_label = {0: "—"} | {c.id: f"{c.name} ({c.code})" for c in countries}

    country_pick_id = st.selectbox(
        "Seleziona esistente (opzionale)",
        country_id_options,
        format_func=lambda cid: country_id_to_label.get(cid, "—"),
        key="comp_country_pick",
    )

    ccol1, ccol2 = st.columns(2)
    with ccol1:
        country_code_in = st.text_input("Codice (3)", max_chars=3, key="comp_country_code")
    with ccol2:
        country_name_in = st.text_input("Nome paese", key="comp_country_name")

    division = st.number_input("Division (1=top league)", min_value=1, max_value=20, value=1, step=1)

    if st.button("Crea/Carica competizione+stagione"):
        # risolvi country
        country_obj = db.query(Country).get(country_pick_id) if country_pick_id != 0 else None
        if country_name_in.strip() and country_code_in.strip():
            country_obj = get_or_create_country(country_name_in, country_code_in)

        if not country_obj:
            st.error("Seleziona o inserisci un Paese per la competizione.")
            st.stop()

        comp = db.query(Competition).filter_by(name=comp_name.strip()).first()
        if not comp:
            comp = Competition(
                name=comp_name.strip(),
                country_id=country_obj.id,
                division=int(division),
            )
            db.add(comp)
            db.commit()
            db.refresh(comp)
        else:
            # allinea eventuali cambiamenti
            changed = False
            if comp.country_id != country_obj.id:
                comp.country_id = country_obj.id
                changed = True
            if comp.division != int(division):
                comp.division = int(division)
                changed = True
            if changed:
                db.commit()

        # stagione
        season = db.query(Season).filter_by(competition_id=comp.id, name=season_name.strip()).first()
        if not season:
            season = Season(competition_id=comp.id, name=season_name.strip())
            db.add(season)
            db.commit()

        st.success("OK")

    st.divider()
    st.subheader("Aggiungi squadra")
    new_team = st.text_input("Nome squadra", key="new_team_sidebar")
    if st.button("Aggiungi squadra") and new_team.strip():
        get_or_create(Team, name=new_team.strip())
        st.success("Squadra aggiunta")


st.divider()

# ---------------- Selezione stagione/competizione ----------------
comps = db.query(Competition).order_by(Competition.name).all()
comp = st.selectbox("Competizione", comps, format_func=lambda x: x.name) if comps else None
seasons = db.query(Season).filter_by(competition_id=comp.id).order_by(Season.name).all() if comp else []
season = st.selectbox("Stagione", seasons, format_func=lambda x: x.name) if seasons else None

teams = db.query(Team).order_by(Team.name).all()

col1, col2, col3 = st.columns(3)
with col1:
    matchday = st.number_input("Giornata", min_value=1, max_value=60, value=1, step=1)
with col2:
    kickoff_date = st.date_input("Data kickoff", value=datetime.now().date())
with col3:
    kickoff_time_str = st.selectbox(
        "Ora kickoff",
        ["12:30", "15:00", "18:00", "18:30", "20:30", "20:45", "21:00"]
    )
    hh, mm = map(int, kickoff_time_str.split(":"))
    kickoff_time = dt.time(hh, mm)

colA, colB = st.columns(2)
with colA:
    home = st.selectbox("Casa", teams, format_func=lambda x: x.name) if teams else None
with colB:
    away = st.selectbox("Trasferta", teams, format_func=lambda x: x.name) if teams else None


# ---------------- Match card (solo grafica) ----------------
st.markdown("""
<style>
.card {padding:16px; border-radius:16px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);}
.small {opacity:0.75; font-size:0.9rem;}
</style>
""", unsafe_allow_html=True)

if "goals" not in st.session_state:
    st.session_state.goals = []

hs, as_ = (0, 0)
if home and away:
    hs, as_ = compute_live_score(st.session_state.goals, home.id, away.id)

st.markdown(f"""
<div class="card">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <div>
      <div class="small">Match</div>
      <div style="font-size:1.4rem; font-weight:700;">{home.name if home else "—"} vs {away.name if away else "—"}</div>
      <div class="small">{kickoff_date.strftime("%d/%m/%Y")} · {kickoff_time_str} · Giornata {int(matchday)}</div>
    </div>
    <div style="font-size:2rem; font-weight:800;">{hs} - {as_}</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.write("")


# ---------------- Marcatori ----------------
st.subheader("⚽ Marcatori")
st.caption("Seleziona squadra → giocatore (filtrato). Own goal assegna il gol alla squadra avversaria.")

team_for_player = st.selectbox(
    "Squadra del giocatore",
    [home, away] if (home and away) else [],
    format_func=lambda x: x.name,
    key="team_for_player"
)

players_team = []
if team_for_player:
    players_team = (
        db.query(Player)
        .filter(Player.current_team_id == team_for_player.id)
        .order_by(Player.last_name, Player.first_name)
        .all()
    )

player_mode = st.radio(
    "Giocatore: seleziona o inserisci",
    ["Seleziona esistente", "Inserisci nuovo"],
    horizontal=True,
    key="player_mode"
)

scorer_player_id = None

if player_mode == "Seleziona esistente":
    if not players_team:
        st.warning("Nessun giocatore registrato per questa squadra. Inseriscilo prima nella UI giocatori.")
    else:
        scorer_player = st.selectbox(
            "Marcatore",
            players_team,
            format_func=lambda p: f"{p.last_name} {p.first_name} (#{p.jersey_number or '-'})",
            key="scorer_select"
        )
        scorer_player_id = scorer_player.id
else:
    fn = st.text_input("Nome", key="new_fn")
    ln = st.text_input("Cognome", key="new_ln")
    by = st.number_input("Anno nascita", min_value=1900, max_value=2100, value=2000, step=1, key="new_by")
    jersey_new = st.number_input("Numero maglia", min_value=0, max_value=99, value=0, step=1, key="new_jersey")

    macro = st.selectbox("Macroruolo", ["GK", "DF", "MF", "ST"], key="new_macro")
    micro = st.multiselect(
        "Microruoli",
        ["GK","LB","RB","CB","DM","CM","AM","LM","RM","CF","SS","LW","LF","RW","RF"],
        key="new_micro"
    )

    if st.button("Crea giocatore", key="create_player_btn"):
        if not (fn.strip() and ln.strip()):
            st.error("Nome e cognome obbligatori.")
        else:
            newp = Player(
                first_name=fn.strip(),
                last_name=ln.strip(),
                birth_year=int(by),
                macro_role=macro,
                micro_roles=micro,
                current_team_id=team_for_player.id if team_for_player else None,
                jersey_number=int(jersey_new) if jersey_new else None,
            )
            db.add(newp)
            db.commit()
            db.refresh(newp)
            st.success(f"Giocatore creato: {newp.last_name} {newp.first_name}")
            scorer_player_id = newp.id

assist_player_id = None
if players_team:
    assist_player = st.selectbox(
        "Assist (opzionale)",
        [None] + players_team,
        format_func=lambda p: "—" if p is None else f"{p.last_name} {p.first_name}",
        key="assist_select"
    )
    assist_player_id = None if assist_player is None else assist_player.id

gcol1, gcol2, gcol3 = st.columns([1, 1, 2])
with gcol1:
    minute = st.number_input("Minuto", min_value=0, max_value=130, value=1, step=1, key="goal_minute")
with gcol2:
    period = st.selectbox("Periodo", ["1T", "2T"], key="goal_period")
with gcol3:
    goal_type = st.selectbox("Tipo gol", ["open_play","penalty","free_kick","own_goal"], key="goal_type")

if st.button("➕ Aggiungi gol", key="add_goal_btn"):
    if not team_for_player:
        st.error("Seleziona la squadra del giocatore.")
    elif scorer_player_id is None:
        st.error("Seleziona o crea il marcatore.")
    else:
        st.session_state.goals.append({
            "scorer_player_id": scorer_player_id,
            "assist_player_id": assist_player_id,
            "player_team_id": team_for_player.id,
            "minute": int(minute),
            "period": period,
            "goal_type": goal_type,
        })


# ---------------- Lista gol inseriti ----------------
st.subheader("🧾 Gol inseriti")

pretty = []
for g in st.session_state.goals:
    scorer = db.query(Player).get(g["scorer_player_id"])
    assist = db.query(Player).get(g["assist_player_id"]) if g["assist_player_id"] else None
    team_p = db.query(Team).get(g["player_team_id"])

    tipo = "⚽" if g["goal_type"] != "own_goal" else "🔁 OG"

    pretty.append({
        "Squadra giocatore": team_p.name if team_p else None,
        "Marcatore": f"{scorer.last_name} {scorer.first_name}" if scorer else None,
        "Assist": f"{assist.last_name} {assist.first_name}" if assist else None,
        "Min": g["minute"],
        "Periodo": g["period"],
        "Tipo": tipo
    })

st.dataframe(pretty, use_container_width=True, hide_index=True)

st.divider()


# ---------------- Salvataggio match ----------------
if st.button("💾 Salva partita nel DB", type="primary"):
    if not season or not home or not away:
        st.error("Seleziona stagione e squadre.")
    elif home.id == away.id:
        st.error("Casa e trasferta non possono essere uguali.")
    else:
        kickoff = datetime.combine(kickoff_date, kickoff_time)

        # ✅ FIX: inizializza score
        home_score = 0
        away_score = 0

        match = Match(
            season_id=season.id,
            matchday=int(matchday),
            kickoff=kickoff,
            home_team_id=home.id,
            away_team_id=away.id,

            # ✅ nuovi campi in matches
            home_team_name=home.name,
            away_team_name=away.name,
            home_score=0,
            away_score=0,
        )
        db.add(match)
        db.commit()
        db.refresh(match)

        for g in st.session_state.goals:
            player_team_id = g["player_team_id"]
            is_owngoal = g["goal_type"] == "own_goal"

            # ✅ se autogol => gol alla squadra avversaria
            if is_owngoal:
                goal_team_id = home.id if player_team_id == away.id else away.id
            else:
                goal_team_id = player_team_id

            # ✅ aggiorna risultato
            if goal_team_id == home.id:
                home_score += 1
            elif goal_team_id == away.id:
                away_score += 1

            goal = Goal(
                match_id=match.id,
                team_id=goal_team_id,
                scorer_player_id=g["scorer_player_id"],
                assist_player_id=g["assist_player_id"],
                minute=g["minute"],
                period=g["period"],
                goal_type=g["goal_type"],
            )
            db.add(goal)

        db.commit()

        # ✅ salva risultato nel match
        match.home_score = home_score
        match.away_score = away_score
        db.commit()

        st.success(f"Partita salvata (ID={match.id}) · Risultato: {home_score}-{away_score}")
        st.session_state.goals = []
        st.rerun()
