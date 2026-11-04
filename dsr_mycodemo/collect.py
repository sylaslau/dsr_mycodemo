"""Share a batch with the Mycelly research database (Supabase): photo shrinking, BE maths and the row writer.

The rows use the column names of data/interim/extracted/*.csv (references/supabase_schema.sql). The client is passed
in (supabase.create_client with the anon key, or a fake in tests); the anon role may only INSERT.

batch is a plain dict built by the Monitor page:
    {"purpose": "food" | "material", "species": "Pleurotus ostreatus", "substrate": "sawdust",
     "ingredients": [{"name", "kg"}] (dry, as weighed), "water_pct_wt", "spawn_pct_wt", "temp_c", "rh_pct",
     "vessel": "Grow bag", "vessel_litres": 1.0, "fill_weight_g": wet fill per container,
     "samples": [{"checks": [{"day", "coverage_pct"}], "colonised_day": int | None, "mould": bool,
                  "flushes": [{"day", "fresh_g"}], "photos": [{"day", "date", "data": bytes}]}]}
"""

import io
import secrets
import string

from PIL import Image, ImageOps

BUCKET = "photos"
LONG_SIDE = 1280                      # px; photos are shrunk to this, never enlarged
JPEG_QUALITY = 85
CODE_CHARS = string.ascii_lowercase + string.digits
LICENCE = "CC BY 4.0"
SHARE_TEXT = ("Sends your recipe, conditions, checks, yields and shrunk photos to the Mycelly research database "
              f"under {LICENCE}. No name or email is stored.")


def new_contributor_code():
    """'u-' + 6 random lowercase letters/digits; the dataset_id of one shared batch."""
    return "u-" + "".join(secrets.choice(CODE_CHARS) for _ in range(6))


def prepare_photo(file) -> bytes:
    """JPEG bytes: EXIF rotation applied, RGB, long side at most 1280 px, quality 85, no EXIF or other metadata."""
    data = file if isinstance(file, bytes) else file.read()     # bytes or an open file / Streamlit upload
    with Image.open(io.BytesIO(data)) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((LONG_SIDE, LONG_SIDE), Image.Resampling.LANCZOS)       # keeps the aspect ratio, never enlarges
    clean = Image.new("RGB", im.size)                          # a fresh image carries no info/EXIF over
    clean.paste(im)
    out = io.BytesIO()
    clean.save(out, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return out.getvalue()


def dry_substrate_g(fill_weight_g, water_pct_wt):
    return fill_weight_g * (1 - water_pct_wt / 100)


def biological_efficiency_pct(fresh_g, fill_weight_g, water_pct_wt):
    """BE % = fresh harvest weight / dry substrate weight x 100 (dry = wet fill x (1 - water %))."""
    dry = dry_substrate_g(fill_weight_g, water_pct_wt)
    if dry <= 0:
        raise ValueError("dry substrate weight must be above 0")
    return 100 * fresh_g / dry


def outcome_code(colonised_day, mould):
    """Short sample.growth_outcome code: 'colonised_d21_no_mould', 'not_colonised_mould', ..."""
    grown = f"colonised_d{colonised_day}" if colonised_day is not None else "not_colonised"
    return grown + ("_mould" if mould else "_no_mould")


def build_rows(dataset_id, batch, licence):
    """{table: [rows]} and [(bucket path, jpeg bytes)] for one batch; nothing is sent here."""
    genus, _, species = str(batch["species"]).partition(" ")
    fer_id, sub_id, con_id = f"{dataset_id}-FER-1", f"{dataset_id}-SUB-1", f"{dataset_id}-C-1"
    water, spawn = batch.get("water_pct_wt"), batch.get("spawn_pct_wt")
    dry = [i for i in batch.get("ingredients", []) if i.get("kg")]
    dry_total = sum(i["kg"] for i in dry)
    components = {}
    for k, ing in enumerate(dry[:3], start=1):
        components[f"component_{k}"] = ing["name"]
        components[f"pct_dry_{k}"] = round(100 * ing["kg"] / dry_total, 1)
    rows = {
        "dataset": [{"dataset_id": dataset_id, "citation": "Mycelly app contribution", "license": licence,
                     "purpose": batch["purpose"], "status": "submitted"}],
        "fermentation": [{"fermentation_id": fer_id, "genus": genus or None, "species": species or None,
                          "fibre_pct_wt": None if water is None or spawn is None else 100 - water - spawn,
                          "water_pct_wt": water, "spawn_pct_wt": spawn, "container_id": con_id,
                          "incubation_temp_c": batch.get("temp_c"), "rh_pct": batch.get("rh_pct")}],
        "substrate": [{"substrate_id": sub_id, "plant_name": batch.get("substrate"), **components}],
        "container": [{"container_id": con_id, "container_type": batch.get("vessel"),
                       "notes": None if batch.get("vessel_litres") is None else f"{batch['vessel_litres']:g} L"}],
        "sample": [], "measurement": [], "image": [], "flag": [],
    }
    photos = []
    fill = batch.get("fill_weight_g")
    for i, s in enumerate(batch["samples"], start=1):
        sample_id = f"{dataset_id}-S-{i:02d}"
        rows["sample"].append({"sample_id": sample_id, "dataset_id": dataset_id, "replicate_no": i,
                               "n_specimens": 1, "growth_outcome": outcome_code(s.get("colonised_day"), s.get("mould")),
                               "substrate_id": sub_id, "fermentation_id": fer_id, "initial_fill_weight_g": fill})
        meas = {"dataset_id": dataset_id, "sample_id": sample_id, "measurement_type": "raw"}
        for c in s.get("checks", []):
            rows["measurement"].append({**meas, "day_of_growth": c["day"], "colonisation_score": c.get("score"),
                                        "surface_colonised_pct": c["coverage_pct"]})
        if s.get("colonised_day") is not None:
            rows["measurement"].append({**meas, "day_of_growth": s["colonised_day"], "surface_colonised_pct": 100})
        for f in s.get("flushes", []):
            rows["measurement"].append({**meas, "day_of_growth": f["day"], "biological_efficiency_pct": round(
                biological_efficiency_pct(f["fresh_g"], fill, water), 2)})
        if s.get("mould"):
            rows["flag"].append({"dataset_id": dataset_id, "table_name": "sample", "key_value": sample_id,
                                 "flag_code": "MOULD", "note": "Mould seen by the grower"})
        used = set()
        for k, p in enumerate(s.get("photos", []), start=1):
            name, n = f"day_{p['day']}", 2
            while name in used:                  # two photos on one day: day_5.jpg, day_5_2.jpg
                name, n = f"day_{p['day']}_{n}", n + 1
            used.add(name)
            path = f"{dataset_id}/{sample_id}/{name}.jpg"
            photos.append((path, prepare_photo(p["data"])))
            rows["image"].append({"image_id": f"{sample_id}-I-{k:03d}", "dataset_id": dataset_id,
                                  "sample_id": sample_id, "image_type": "user_photo", "file_path": path,
                                  "acquired_date": p.get("date"), "day_of_growth": p["day"]})
    return rows, photos


TABLE_ORDER = ("dataset", "fermentation", "substrate", "container", "sample", "measurement")


def submit_batch(client, batch, consent_licence):
    """Write one batch and upload its shrunk photos; returns the contributor code (dataset_id).

    consent_licence is the licence text the grower agreed to (e.g. 'CC BY 4.0'); falsy = no consent, nothing is sent
    and None is returned."""
    if not consent_licence:
        return None
    dataset_id = batch.get("dataset_id") or new_contributor_code()
    rows, photos = build_rows(dataset_id, batch, consent_licence)

    def insert(table):
        if rows[table]:
            client.table(table).insert(rows[table], returning="minimal").execute()   # anon cannot read rows back

    for table in TABLE_ORDER:
        insert(table)
    bucket = client.storage.from_(BUCKET)
    for path, data in photos:
        bucket.upload(path, data, {"content-type": "image/jpeg"})
    insert("image")
    insert("flag")
    return dataset_id
