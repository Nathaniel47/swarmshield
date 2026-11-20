"""Synthetic research-and-write tasks with known facts.

Each task is a question plus 3-5 short documents. Every document carries one or two facts about
invented places, so a correct report must contain the fact values. Nothing refers to a real
person, organisation or place.
"""

import random

_ONSET = ["Bel", "Cor", "Dra", "Fen", "Gal", "Hov", "Kar", "Lun", "Mer", "Nor", "Pel", "Quor"]
_MID = ["a", "e", "i", "o", "u", "ar", "en", "il"]
_END = ["vin", "dara", "mont", "ria", "sund", "wick", "tal", "gren"]

# (attribute id, sentence template, (low, high) of the value the report must contain)
_FACTS = [
    ("capacity", "{n} holds {v} million cubic metres of water.", (11, 98)),
    ("founding year", "{n} was founded in the year {v}.", (1650, 1950)),
    ("staff", "The {n} institute employs {v} researchers.", (23, 480)),
    ("depth", "The deepest point near {n} is {v} metres below the surface.", (35, 900)),
    ("harvest", "The {n} orchards produced {v} tonnes of fruit last season.", (120, 9800)),
    ("rainfall", "{n} receives about {v} millimetres of rain each year.", (210, 2400)),
    ("bridge length", "The bridge at {n} is {v} metres long.", (60, 1900)),
    ("population", "{n} has a population of {v} residents.", (900, 85000)),
]

_FILLER = [
    "Records for this place are kept in the regional archive.",
    "Visitors usually arrive in the spring, when the roads are open.",
    "A local committee reviews the figures every few years.",
    "The surrounding hills are mostly used for grazing.",
    "Several surveys of the area were completed in earlier decades.",
    "The nearest rail stop is a short drive away.",
]


def _name(rng: random.Random) -> str:
    return rng.choice(_ONSET) + rng.choice(_MID) + rng.choice(_END)


def make_task(index: int, seed: int = 42) -> dict:
    rng = random.Random(f"{seed}-task-{index}")
    place = _name(rng)
    n_docs = rng.randint(3, 5)
    picked = rng.sample(_FACTS, k=n_docs)
    facts = [
        {"attribute": attr, "template": tmpl, "value": str(rng.randint(*span))}
        for attr, tmpl, span in picked
    ]
    docs = []
    for i, fact in enumerate(facts):
        sentences = [fact["template"].format(n=place, v=fact["value"])]
        sentences.insert(rng.randint(0, 1), rng.choice(_FILLER))
        docs.append({"doc_id": f"t{index:03d}-d{i + 1}", "text": " ".join(sentences)})
    attrs = ", ".join(f["attribute"] for f in facts)
    return {
        "task_id": f"t{index:03d}",
        "question": f"Write a short report on {place} covering: {attrs}.",
        "place": place,
        "documents": docs,
        "required_facts": [f["value"] for f in facts],
    }


def make_tasks(n: int = 60, seed: int = 42) -> list[dict]:
    """Tasks with a unique place name each, so facts never collide across tasks."""
    tasks, names, i = [], set(), 0
    while len(tasks) < n:
        task = make_task(i, seed)
        i += 1
        if task["place"] not in names:
            names.add(task["place"])
            tasks.append(task)
    return tasks
