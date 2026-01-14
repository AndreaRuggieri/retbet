import sys
from pathlib import Path
from datetime import date
from sqlalchemy.exc import IntegrityError

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import SessionLocal, engine
from app.models import Base, Team, Player, Country

Base.metadata.create_all(bind=engine)
db = SessionLocal()

st.set_page_config(page_title="Gestione Giocatori", layout="wide")
st.title("👤 Inserimento / Gestione Giocatori")

MACRO = ["GK", "DF", "MF", "ST"]
MICRO = ["GK", "LB", "RB", "CB", "DM", "CM", "AM", "LM", "RM", "CF", "SS", "LW", "LF", "RW", "RF"]


def get_or_create(model, **kwargs):
    obj = db.query(model).filter_by(**kwargs).first()
    if obj:
        return obj
    obj = model(**kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_or_create_country(name: str, code: str):
    name = (name or "").strip()
    code = (code or "").strip().upper()

    if not name or not code:
        return None

    existing = db.query(Country).filter(Country.code == code).first()
    if existing:
        return existing

    existing = db.query(Country).filter(Country.name == name).first()
    if existing:
        return existing

    try:
        country = Country(name=name, code=code)
        db.add(country)
        db.commit()
        db.refresh(country)
        return country
    except IntegrityError:
        db.rollback()
        return db.query(Country).filter(Country.code == code).first()


def compute_age_years(birth: date | None) -> int | None:
    if not birth:
        return None
    today = date.today()
    years = today.year - birth.year
    if (today.month, today.day) < (birth.month, birth.day):
        years -= 1
    return years


def start_edit(player_id: int):
    p = db.query(Player).get(player_id)
    if not p:
        return

    st.session_state["edit_player_id"] = p.id
    st.session_state["first_name_val"] = p.first_name or ""
    st.session_state["last_name_val"] = p.last_name or ""
    st.session_state["full_name_val"] = p.full_name or ""

    st.session_state["birth_date_val"] = p.birth_date or date(2000, 1, 1)
    st.session_state["jersey_val"] = int(p.jersey_number or 0)
    st.session_state["macro_val"] = p.macro_role or "GK"
    st.session_state["micro_val"] = p.micro_roles or []

    # salva ID paese (int), NON oggetto
    st.session_state["country_pick_val"] = int(p.country_id or 0)
    st.session_state["country_code_val"] = ""
    st.session_state["country_name_val"] = ""


def reset_name_fields_only():
    st.session_state["first_name_val"] = ""
    st.session_state["last_name_val"] = ""
    st.session_state["full_name_val"] = ""


def submit_player(team_id: int):
    first_name = (st.session_state.get("first_name_val") or "").strip()
    last_name = (st.session_state.get("last_name_val") or "").strip()
    full_name = (st.session_state.get("full_name_val") or "").strip() or None

    birth_date = st.session_state.get("birth_date_val")
    jersey = int(st.session_state.get("jersey_val") or 0)
    macro_role = st.session_state.get("macro_val")
    micro_roles = st.session_state.get("micro_val") or []

    # nazionalità: pick ID
    country_pick_id = int(st.session_state.get("country_pick_val") or 0)
    country_obj = db.query(Country).get(country_pick_id) if country_pick_id != 0 else None

    # nazionalità: creazione da input
    country_code_in = (st.session_state.get("country_code_val") or "").strip()
    country_name_in = (st.session_state.get("country_name_val") or "").strip()

    if country_name_in and country_code_in:
        country_obj = get_or_create_country(country_name_in, country_code_in)
        # reset campi manuali (evita ricreazioni/ri-click)
        st.session_state["country_code_val"] = ""
        st.session_state["country_name_val"] = ""

    # validazione
    if not (first_name and last_name and birth_date):
        st.session_state["form_error"] = "Nome, Cognome e Data di nascita sono obbligatori."
        return
    st.session_state["form_error"] = ""

    existing = db.query(Player).filter(
        Player.first_name == first_name,
        Player.last_name == last_name,
        Player.birth_date == birth_date,
    ).first()

    age_years = compute_age_years(birth_date)

    if existing:
        existing.full_name = full_name
        existing.jersey_number = jersey
        existing.country_id = country_obj.id if country_obj else None
        existing.macro_role = macro_role
        existing.micro_roles = micro_roles
        existing.current_team_id = team_id
        existing.age_years = age_years
        db.commit()
    else:
        newp = Player(
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            birth_date=birth_date,
            age_years=age_years,
            country_id=country_obj.id if country_obj else None,
            macro_role=macro_role,
            micro_roles=micro_roles,
            current_team_id=team_id,
            jersey_number=jersey,
        )
        db.add(newp)
        db.commit()

    reset_name_fields_only()
    st.session_state["edit_player_id"] = None


# ---------------- Session defaults ----------------
if "edit_player_id" not in st.session_state:
    st.session_state["edit_player_id"] = None

if "birth_date_val" not in st.session_state:
    st.session_state["birth_date_val"] = date(2000, 1, 1)
if "jersey_val" not in st.session_state:
    st.session_state["jersey_val"] = 0
if "macro_val" not in st.session_state:
    st.session_state["macro_val"] = "GK"
if "micro_val" not in st.session_state:
    st.session_state["micro_val"] = []

# ora è int (0 = nessuno)
if "country_pick_val" not in st.session_state:
    st.session_state["country_pick_val"] = 0
if "country_code_val" not in st.session_state:
    st.session_state["country_code_val"] = ""
if "country_name_val" not in st.session_state:
    st.session_state["country_name_val"] = ""

if "first_name_val" not in st.session_state:
    st.session_state["first_name_val"] = ""
if "last_name_val" not in st.session_state:
    st.session_state["last_name_val"] = ""
if "full_name_val" not in st.session_state:
    st.session_state["full_name_val"] = ""

if "form_error" not in st.session_state:
    st.session_state["form_error"] = ""


# ---------------- Sidebar: setup rapido ----------------
with st.sidebar:
    st.header("Setup rapido")

    st.subheader("Aggiungi Team")
    t_name = st.text_input("Nome squadra", key="tname", placeholder="Milan")
    if st.button("➕ Crea squadra"):
        if t_name.strip():
            get_or_create(Team, name=t_name.strip())
            st.success("Squadra aggiunta")
        else:
            st.warning("Inserisci nome squadra")

st.divider()

# ---------------- Selezione squadra ----------------
teams = db.query(Team).order_by(Team.name).all()
if not teams:
    st.info("Aggiungi almeno una squadra dalla sidebar.")
    st.stop()

team_options = {t.name: t.id for t in teams}
team_name = st.selectbox("Seleziona squadra (rosa)", list(team_options.keys()))
team_id = team_options[team_name]
team = db.query(Team).get(team_id)

# ---------------- Lista giocatori squadra + ricerca ----------------
colA, colB, colC = st.columns([2, 1, 1])
with colA:
    search = st.text_input("Cerca (cognome/nome/full name)", placeholder="es: Leao / Lautaro / Rafael Leão")
with colB:
    show_all = st.checkbox("Mostra tutti (anche altre squadre)", value=False)
with colC:
    st.write("")  # spacer

q = db.query(Player)
if not show_all:
    q = q.filter(Player.current_team_id == team_id)

if search.strip():
    s = f"%{search.strip()}%"
    q = q.filter(
        (Player.last_name.ilike(s)) |
        (Player.first_name.ilike(s)) |
        (Player.full_name.ilike(s))
    )

players = q.order_by(Player.last_name, Player.first_name).all()

st.subheader(f"📋 Giocatori (vista: {team.name})")

# layout righe: Nome | Squadra | Nat | DoB | Age | Macro | Micro | ✏️ | ❌
for p in players:
    cols = st.columns([2.6, 1.4, 0.8, 1.3, 0.6, 0.8, 2.8, 0.5, 0.5])

    with cols[0]:
        display = f"{p.last_name} {p.first_name}".strip()
        if p.full_name:
            display = f"{display} · ({p.full_name})"
        st.write(display)

    with cols[1]:
        st.write(p.current_team.name if getattr(p, "current_team", None) else "")

    with cols[2]:
        st.write(p.country.code if p.country else "")

    with cols[3]:
        st.write(p.birth_date.strftime("%d/%m/%Y") if p.birth_date else "")

    with cols[4]:
        st.write(p.age_years if p.age_years is not None else "")

    with cols[5]:
        st.write(p.macro_role or "")

    with cols[6]:
        st.write(", ".join(p.micro_roles or []))

    with cols[7]:
        st.button("✏️", key=f"edit_btn_{p.id}", on_click=start_edit, args=(p.id,))

    with cols[8]:
        if st.button("❌", key=f"del_btn_{p.id}"):
            st.session_state["delete_player_id"] = p.id
            st.session_state["delete_player_name"] = f"{p.last_name} {p.first_name}"

# --- popup conferma delete ---
if st.session_state.get("delete_player_id") is not None:
    pid = st.session_state["delete_player_id"]
    pname = st.session_state.get("delete_player_name", "")

    @st.dialog("Delete player")
    def confirm_delete():
        st.write(f"Are you sure to delete this player from DB?\n\n**{pname}** (ID={pid})")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Yes, delete"):
                obj = db.query(Player).get(pid)
                if obj:
                    db.delete(obj)
                    db.commit()

                st.session_state["delete_player_id"] = None
                st.session_state["delete_player_name"] = None

                if st.session_state.get("edit_player_id") == pid:
                    st.session_state["edit_player_id"] = None

                st.rerun()
        with c2:
            if st.button("No"):
                st.session_state["delete_player_id"] = None
                st.session_state["delete_player_name"] = None
                st.rerun()

    confirm_delete()

st.divider()
st.subheader("➕ Inserisci / Modifica giocatore")

if st.session_state["edit_player_id"] is not None:
    st.info(
        f"✏️ Modalità modifica attiva (Player ID={st.session_state['edit_player_id']}). "
        "Premi 'Crea giocatore' per sovrascrivere (match su Nome+Cognome+Data)."
    )

countries = db.query(Country).order_by(Country.name).all()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.text_input("Nome", key="first_name_val", placeholder="Rafael")
with c2:
    st.text_input("Cognome", key="last_name_val", placeholder="Leao")
with c3:
    st.text_input("Nome completo (opzionale)", key="full_name_val",
                  placeholder="Rafael Alexandre da Conceição Leão")
with c4:
    st.number_input("Numero maglia", min_value=0, max_value=99, step=1, key="jersey_val")

c5, c6, c7 = st.columns([2, 1, 2])
with c5:
    country_id_options = [0] + [c.id for c in countries]
    country_id_to_label = {0: "—"} | {c.id: f"{c.name} ({c.code})" for c in countries}

    st.selectbox(
        "Nazionalità (seleziona esistente - opzionale)",
        country_id_options,
        format_func=lambda cid: country_id_to_label.get(cid, "—"),
        key="country_pick_val",
    )
with c6:
    st.text_input("Codice (3)", max_chars=3, key="country_code_val")
with c7:
    st.text_input("Nome paese", key="country_name_val")

c8, c9, c10 = st.columns([2, 3, 2])
with c8:
    st.date_input("Data di nascita", key="birth_date_val")
with c9:
    st.selectbox("Macroruolo", MACRO, key="macro_val")
with c10:
    st.multiselect("Microruoli", MICRO, key="micro_val")

if st.session_state["form_error"]:
    st.error(st.session_state["form_error"])

st.button(
    "💾 Crea giocatore",
    type="primary",
    on_click=submit_player,
    args=(team_id,)
)
