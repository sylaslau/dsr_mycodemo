"""Monitor: one box per residence (colonisation and, if chosen, the next one) with one reading log each; the batch
bubble sits in the residence of its current stage. The stage changes only when the grower confirms it."""

import io
import json
from datetime import date

import streamlit as st

from dsr_mycodemo import pipeline
from dsr_mycodemo.app import flow, stage_ui
from dsr_mycodemo.cultivation import baseline_guide
from dsr_mycodemo.growth.coverage import days_since, photo_coverage, photo_datetime, photo_quality
from dsr_mycodemo.growth.forecast import restore_from_text

st.set_page_config(page_title="Monitor", page_icon="📷", layout="wide")
flow.init()
flow.header("Monitor")

# session-only stores (nothing is written to disk): stage_log {dish: [{stage, date, note}]},
# harvest {dish: [{date, g}]}, losses {dish: {...}}, dry_g {dish: g}, costs {batch: {...}},
# batch_fields {dataset: {...}}, dish_fields {dish: {...}}, upload_rows / restored_photos {key: [photo rows]},
# environments {name: pipeline.Environment} (kept for backups), monitor_env {residence: latest entry + "log"},
# sample_photos {sample ID: [photo rows]}, outcomes {sample ID: {colonised: date | None, mould: bool}},
# batch_stage (the grower's word, confirmed here) and
# next_start (date the next stage started)
ss = st.session_state
STAGE_LOG = ss.setdefault("stage_log", {})
HARVEST = ss.setdefault("harvest", {})
LOSSES = ss.setdefault("losses", {})
DRY_G = ss.setdefault("dry_g", {})
COSTS = ss.setdefault("costs", {})
BATCH_FIELDS = ss.setdefault("batch_fields", {})
DISH_FIELDS = ss.setdefault("dish_fields", {})
UPLOAD_ROWS = ss.setdefault("upload_rows", {})
RESTORED_PHOTOS = ss.setdefault("restored_photos", {})
ENVIRONMENTS = ss.setdefault("environments", {})
SAMPLE_PHOTOS = ss.setdefault("sample_photos", {})
OUTCOMES = ss.setdefault("outcomes", {})
RADIO = {"ref": "d005 (reference)", "syldd": "syldd (my batch)"}
WIDGET_PREFIXES = ("b_", "h_", "l_", "c_")      # their values come from the stores above after a restore
PLAN = ss["batch"]


def stage_from_backup(text):
    """batch_stage and next_start from a JSON backup (optional top-level keys; CSVs and older backups have none)."""
    if not text.lstrip().startswith("{"):
        return {}
    doc, out = json.loads(text), {}
    word = flow.OLD_STAGE_WORDS.get(doc.get("batch_stage"), doc.get("batch_stage"))
    if word in flow.STAGES_FOOD + flow.STAGES_MATERIAL:
        out["batch_stage"] = word
    if doc.get("next_start"):
        out["next_start"] = date.fromisoformat(str(doc["next_start"])[:10])
    return out


def apply_restore(p, stage=None):
    """Refill the stores from a restored log; a backup replaces everything, a CSV only its own containers.
    stage = {batch_stage, next_start} from the backup (stage_from_backup)."""
    if p["replace"]:
        for k in ("batch_stage", "next_start"):          # the restored batch has its own stage (or starts again)
            ss.pop(k, None)
    ss.update(stage or {})
    if p["replace"]:
        for store in (STAGE_LOG, HARVEST, LOSSES, DRY_G, COSTS, DISH_FIELDS, UPLOAD_ROWS, RESTORED_PHOTOS):
            store.clear()
    STAGE_LOG.update(p["stage_log"])
    HARVEST.update(p["harvest"])
    LOSSES.update(p["losses"])
    DRY_G.update(p["dry_g"])
    COSTS.update(p["costs"])
    DISH_FIELDS.update(p["dish_fields"])
    BATCH_FIELDS[p["dataset"]] = p["batch"]
    if p["replace"]:
        ENVIRONMENTS.clear()
    ENVIRONMENTS.update({k: pipeline.Environment.from_dict(v) for k, v in p.get("environments", {}).items()})
    for r in p["photos"]:
        if str(r["file"]).startswith("upload:"):
            RESTORED_PHOTOS.setdefault(r["series_id"], []).append(r)
    for k in [k for k in ss if k.startswith(WIDGET_PREFIXES)]:
        del ss[k]                                # widgets restart from the restored values
    ss["dataset_radio"] = RADIO[p["dataset"]]
    ss["dish_select"] = p["dish"]
    if p.get("pipeline"):                        # the batch record (older backups and CSVs have none)
        pb = pipeline.Batch.from_dict(p["pipeline"])
        ss["pipeline_batch"] = pb
        if pb.goal:                              # the plan keys the pages share follow the restored batch
            ss.update(goal=pb.goal, choice=pb.choice, custom_name=pb.custom_name, environment=pb.environment,
                      temp_c=pb.temp_c, recipe=pb.recipe, inoc_date=pb.inoc_date,
                      material_species=pipeline.material_species(pb), residences=dict(pb.residences))
            if pb.residences.get("colonisation"):   # older backups have no residences: env_where stays as it is
                ss["env_where"] = pb.residences["colonisation"]


# --- helpers -------------------------------------------------------------------------------
# book range for CO2 (ppm): colonisation tolerates a lot
CO2_COLONISING = (0.0, 20000.0)
MATERIALS = flow.is_materials()
STAGES = flow.STAGES_MATERIAL if MATERIALS else flow.STAGES_FOOD
FIRST_STAGE = "Spawn run"
# mode -> (stage after the spawn run, confirm button)
NEXT_STAGE = {False: ("Fruiting", "Induction done"),
              True: ("Post-treatment", "Confirm post-treatment started")}[MATERIALS]

SHOWN = stage_ui.SHOWN       # shown name; the saved value stays the same (old batches load)


def next_residence():
    """The residence chosen for the next stage on Recipe and actions, or None."""
    name = ss.get("residences", {}).get("next")
    return name if name in stage_ui.residence_options("next") else None


def residences():
    """Residences entered on Start a batch, in that order, then the next-stage residence if chosen."""
    names = [n for n in stage_ui.RESIDENCES if n in ss.get("env_size", {}) or n == ss.get("env_where")]
    nxt = next_residence()
    return names + ([nxt] if nxt and nxt not in names else [])


def batch_stage():
    """The stage the grower confirmed (session_state['batch_stage']); Spawn run until a confirm button is pressed."""
    ss["batch_stage"] = flow.OLD_STAGE_WORDS.get(ss.get("batch_stage"), ss.get("batch_stage"))
    if ss.get("batch_stage") not in STAGES:
        ss["batch_stage"] = FIRST_STAGE
    return ss["batch_stage"]


def batch_residence():
    """Where the batch is: the next residence once the next stage was confirmed (if one was chosen), else the
    colonisation residence."""
    return next_residence() if ss.get("next_start") and next_residence() else ss.get("env_where")


def wanted_ranges(batch):
    """Colonisation ranges {'temp': (lo, hi, optimum), 'rh': (lo, hi, target), 'co2': (lo, hi, target)} from the
    baseline, or None. (Fruiting ranges come from pipeline.next_stage_ranges.)"""
    br = pipeline.baseline_row(batch)
    if br is None:
        return None
    c = baseline_guide.colonisation(br[0])
    t, lo_h, hi_h = c["incubation_temp_C"], *pipeline.HUMIDITY_RANGE
    return {"temp": (t["min"], t["max"], t["opt"]), "rh": (lo_h, hi_h, float(c["incubation_rh_pct"])),
            "co2": (*CO2_COLONISING, 20000.0)}


def box_setup(batch, name):
    """(ranges, prefill kind, fields, caption) of one residence box: the ranges follow the stage of the batch in it
    (colonisation, fruiting, or a record only for post-treatment); with no batch in it, colonisation ranges."""
    if not (PLAN and name == batch_residence() and ss.get("next_start")):
        return wanted_ranges(batch), "grow", ("temp", "rh", "co2"), None
    if MATERIALS:
        return None, "post", ("temp", "rh"), ("Temperature and humidity are a record only: our data has no wanted "
                                              "ranges for post-treatment, so the lights stay yellow.")
    ranges = pipeline.next_stage_ranges(batch)
    return ranges, "fruit", ("temp", "rh", "co2"), ("Lights: fruiting ranges of the consensus guide." if ranges else
                                                    "No fruiting ranges are known for this mushroom.")


dot = stage_ui.dot                                 # traffic lights live in stage_ui (shared with page 8)


@st.cache_data(show_spinner=False, max_entries=64)
def analyse_photo(data: bytes):
    """Photo coverage (method choice) and quality check of one photo."""
    buf = io.BytesIO(data)
    cov_ = photo_coverage(buf)
    return {"coverage": cov_["coverage"], "method": cov_["method"],
            "quality": ", ".join(photo_quality(buf)["reasons"])}


def batch_record():
    """The one pipeline batch, with every sample photo copied in (a photo checked on Check image replaces its HSV
    value; one marked but not yet ticked is left out)."""
    return flow.sample_batch()


def sample_record(sample, inoc_date):
    """Outcome of one sample while colonising: fully colonised date and mould seen."""
    stage_ui.sample_log("colonisation", sample, inoc_date, materials=flow.is_materials())


# sharing for research: the "Share this batch for research" section was taken off this page (11-19); these two
# helpers and collect.py stay for when it comes back.
def supabase_config():
    """The [supabase] section of .streamlit/secrets.toml (url, anon_key), or None when sharing is not set up."""
    try:
        cfg = dict(st.secrets["supabase"])
    except (FileNotFoundError, KeyError):        # no secrets file or no [supabase] section
        return None
    return cfg if cfg.get("url") and cfg.get("anon_key") else None


def share_payload(rec, fill_g):
    """The batch as collect.submit_batch wants it, from the plan, the recipe and the Monitor stores."""
    inoc = PLAN["inoc_date"]
    spawn = float(rec["spawn_pct"])
    vessel = ss.get("env_container")
    samples = []
    for i in range(1, int(PLAN["n_containers"]) + 1):
        sid = f"{PLAN['batch_label']}-{i:02d}"
        rows = [r for r in SAMPLE_PHOTOS.get(sid, []) if r["day"] >= 0 and flow.in_forecast(r)]
        out = OUTCOMES.get(sid, {})
        samples.append({
            "checks": [{"day": r["day"], "coverage_pct": round(100 * r["coverage"], 1)} for r in rows],
            "colonised_day": days_since(out["colonised"], inoc) if out.get("colonised") else None,
            "mould": bool(out.get("mould")),
            "flushes": [{"day": days_since(f["date"], inoc), "fresh_g": f["g"]} for f in HARVEST.get(sid, [])],
            "photos": [{"day": r["day"], "date": r.get("date"), "data": r["data"]} for r in rows if r.get("data")]})
    return {"purpose": "material" if flow.is_materials() else "food", "species": PLAN["species"],
            "substrate": PLAN.get("substrate"), "ingredients": rec["ingredients"],
            "water_pct_wt": round(rec["moisture_pct"] * (1 - spawn / 100), 1),     # % of the whole mix
            "spawn_pct_wt": spawn, "temp_c": PLAN.get("temp_c"), "rh_pct": ss.get("rh_pct"),
            "vessel": vessel, "vessel_litres": ss.get("env_size", {}).get(vessel), "fill_weight_g": float(fill_g),
            "samples": samples}


# --- sidebar: the environment list above Restore --------------------------------------------
with st.sidebar:
    env_list = st.container()
    st.header("Restore")
    restore_file = st.file_uploader("Restore from backup", type=["json", "csv"], key="restore_file",
                                    help="A 'Download backup (JSON)' file, or the 'Download my log (CSV)' file.")
    if restore_file is not None:
        try:
            restored = restore_from_text(restore_file.getvalue().decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as err:
            st.error(f"Could not restore {restore_file.name}: {err}")
        else:
            if ss.get("restored_id") != restore_file.file_id:
                apply_restore(restored, stage_from_backup(restore_file.getvalue().decode("utf-8")))
                ss["restored_id"] = restore_file.file_id
            st.success(f"Restored from {restore_file.name}.")

# --- main area: one box per residence ----------------------------------------------------
def stage_controls(stage):
    """One row: the confirm button on the left (Spawn run -> next stage, with its date), Contaminated on the right."""
    if stage == "Contaminated":
        return
    left, right = st.columns([3, 1], vertical_alignment="bottom")
    if not ss.get("next_start"):
        nxt_stage, label = NEXT_STAGE
        with left:
            if next_residence():
                d_col, b_col = st.columns([1, 2], vertical_alignment="bottom")
                on = d_col.date_input("Started on", date.today(), key="confirm_date")
                if b_col.button(label, key="confirm_next", type="primary"):
                    ss["batch_stage"], ss["next_start"] = nxt_stage, on
                    st.rerun()
            elif st.button(label, key="confirm_next", type="primary"):     # no next residence yet: choose it there
                ss["show_next_steps"] = True
                st.switch_page("pages/2_Recipe_and_actions.py")
    with right.container(horizontal_alignment="right"):
        if st.button("Contaminated", key="mark_contaminated"):
            ss["batch_stage"] = "Contaminated"
            st.rerun()


def coverage_photo(name, sample):
    """Colonising: a photo of the sample with the quick coverage guess (feeds the Colonisation forecast)."""
    up = st.file_uploader("Photo of this sample", type=["jpg", "jpeg", "png"], key=f"photo_{name}_{sample}")
    if up is None:
        return
    try:
        taken = photo_datetime(up).date()
    except ValueError:
        taken = date.today()
    a_ = analyse_photo(up.getvalue())
    row = {"series_id": sample, "day": days_since(taken, batch.inoc_date), "file": f"upload: {up.name}",
           "coverage": a_["coverage"], "method": a_["method"], "quality": a_["quality"],
           "date": taken.isoformat(), "data": up.getvalue()}     # data: for Check image (session only)
    rows = SAMPLE_PHOTOS.setdefault(sample, [])
    if not any((r["file"], r["day"]) == (row["file"], row["day"]) for r in rows):
        rows.append(row)
    ss["pipeline_result"] = pipeline.run(batch_record())     # Photo coverage -> Colonisation forecast
    st.success(f"Photo saved under {sample}. Check the quick guess with your own marks on Check image.")
    m1, m2 = st.columns(2)
    m1.metric("Coverage (quick guess)", f"{100 * a_['coverage']:.0f} %", help=a_["method"])
    m2.metric("Day since inoculation", row["day"])
    if st.button("Check image", key=f"check_{name}_{sample}", type="primary"):
        ss["check_target"] = {"sample": sample, "file": row["file"]}
        st.switch_page("pages/5_Check_image.py")


def batch_bubble(batch, name):
    """The plan batch in its residence: the current stage bubble left of the batch name, the buttons, one sample's
    record."""
    stage = batch_stage()
    with st.container(border=True):
        st.markdown(stage_ui.stage_badge(stage, PLAN["batch_label"]), unsafe_allow_html=True)
        stage_controls(stage)
        samples = stage_ui.plan_samples(PLAN)
        sample = st.selectbox("Sample (one bag, jar or mould)", samples, key=f"sample_{name}")
        if ss.get("next_start"):                 # fruiting / harvested, or post-treatment
            stage_ui.sample_log("next", sample, PLAN["inoc_date"], materials=MATERIALS)
        else:
            coverage_photo(name, sample)
            sample_record(sample, batch.inoc_date)


batch = batch_record()
side_lights = {}
for name in residences():
    with st.container(border=True):
        st.subheader(SHOWN.get(name, name))
        has_batch = bool(PLAN) and name == batch_residence()
        rng, kind, fields, note = box_setup(batch, name)
        if note:
            st.caption(note)
        colour, entry = stage_ui.environment_log(name, rng, batch.inoc_date if has_batch else None,
                                                 kind, fields=fields)
        if entry is not None:
            values = entry
            ENVIRONMENTS[name] = pipeline.Environment(name, "Tub", float(values["temp"] if values["temp"] is not None
                                                                         else 21.0), values["rh"], values["measured_by"])
        side_lights[name] = colour
        if has_batch:
            batch_bubble(batch, name)

if not residences():
    st.info("Choose where you grow on Start a batch first.")
    st.page_link("pages/1_Start_a_batch.py", label="Start a batch", icon="🍄")

with env_list:
    for name, colour in side_lights.items():
        st.markdown(f"{dot(colour)} {SHOWN.get(name, name)}", unsafe_allow_html=True)
