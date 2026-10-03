"""
M1 — heuristic topic tagging for the MDCAT-sourced rows.

docs/phases/MENTORA_Phase4_Model_Training.md §4 assumes question_bank.csv
already has real per-question `topic` tags for multi-label classification.
It mostly doesn't: Phase 3's MDCAT extraction only ever assigned `subject`
(Biology/Chemistry/Physics/English/Logical Reasoning) — fine-grained topic
tagging was explicitly left as a manual TODO (see SOURCES.md). The 378 Math
rows already have real topic/subtopic from their source dataset and are left
untouched here.

This is a keyword-matching heuristic, same spirit as the M5 CERT/GPA regex
approach — a reasonable first pass, NOT a substitute for manual review. Topic
taxonomy follows the example in docs/phases/MENTORA_Phase3_Datasets.md §4.4.

Run: ~/.venvs/mentora-data/bin/python datasets/m1_gap_classifier/tag_topics.py
Output: mentora_data/processed/m1/question_bank_final.csv (topic/subtopic
        columns filled in for MDCAT rows; overwrites in place)
"""

from pathlib import Path

import pandas as pd

M1_DIR = Path(__file__).resolve().parents[2] / "mentora_data" / "processed" / "m1"

# subject -> {topic: [keywords]}. Keyword hits are case-insensitive substring
# matches against question_text; the topic with the most hits wins. No hits
# at all -> "General <Subject>" rather than forcing a bad guess.
TAXONOMY = {
    "Biology": {
        "Cell Biology": ["cell membrane", "mitochondria", "ribosome", "organelle", "cytoplasm", "golgi", "lysosome", "plasma membrane", "chloroplast", "nucleus"],
        "Genetics": ["gene", "chromosome", "dna", "rna", "allele", "mutation", "mendel", "heredity", "genotype", "phenotype", "transcription", "translation"],
        "Physiology": ["hormone", "nervous system", "digestion", "respiration", "circulation", "kidney", "heart", "brain", "muscle", "reflex", "synapse", "neuron", "action potential"],
        "Botany": ["plant", "photosynthesis", "xylem", "phloem", "seed", "pollination", "stomata", "chlorophyll"],
        "Zoology": ["animal", "vertebrate", "invertebrate", "mammal", "reptile", "amphibian", "insect", "arthropod"],
        "Ecology": ["ecosystem", "population", "habitat", "food chain", "biodiversity", "species"],
        "Evolution": ["evolution", "natural selection", "adaptation", "darwin", "speciation"],
        "Biochemistry": ["enzyme", "protein", "amino acid", "carbohydrate", "lipid", "metabolism", "atp", "krebs"],
        "Microbiology": ["virus", "bacteria", "bacterial", "pathogen", "antibiotic", "immune"],
    },
    "Chemistry": {
        "Organic Chemistry": ["alkane", "alkene", "alkyne", "benzene", "hydrocarbon", "carboxylic", "ester", "alcohol", "ketone", "aldehyde", "polymer", "organic"],
        "Inorganic Chemistry": ["periodic table", "transition metal", "ionic bond", "coordination compound", "acid", "base", "salt", "oxidation", "reduction"],
        "Physical Chemistry": ["equilibrium", "thermodynamics", "kinetics", "rate of reaction", "ph ", "molarity", "mole", "gas law", "entropy", "enthalpy", "electrochemistry"],
        "Biochemistry": ["protein", "enzyme", "amino acid", "carbohydrate", "lipid", "nucleic acid"],
    },
    "Physics": {
        "Mechanics": ["force", "velocity", "acceleration", "momentum", "newton", "friction", "projectile", "torque", "gravity", "work done", "kinetic energy", "potential energy"],
        "Electricity & Magnetism": ["electric field", "magnetic field", "current", "voltage", "resistance", "capacitor", "circuit", "charge", "ohm", "electromagnetic"],
        "Waves & Optics": ["wave", "sound", "frequency", "wavelength", "lens", "mirror", "refraction", "reflection", "interference", "diffraction"],
        "Thermodynamics": ["heat", "temperature", "thermal", "entropy", "specific heat", "calorimetry"],
        "Modern Physics": ["photoelectric", "quantum", "nuclear", "radioactive", "atom", "electron", "proton", "isotope"],
    },
    "English": {
        "Grammar": ["tense", "verb", "voice", "preposition", "conjunction", "subject-verb", "article", "clause"],
        "Vocabulary": ["similar in meaning", "opposite", "synonym", "antonym", "capitalized"],
        "Reading Comprehension": ["passage", "according to the author", "main idea", "paragraph"],
        "Writing & Punctuation": ["punctuation", "sentence", "underlined", "error", "comma", "semicolon"],
    },
    "Logical Reasoning": {
        "Logical Reasoning": [],  # single bucket — not worth subdividing a 216-question set
    },
}


def tag_one(subject: str, text: str) -> tuple[str, str]:
    topics = TAXONOMY.get(subject)
    if not topics:
        return subject, ""
    text_lower = str(text).lower()
    best_topic, best_hits = None, 0
    for topic, keywords in topics.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        if hits > best_hits:
            best_topic, best_hits = topic, hits
    if best_topic is None:
        return f"General {subject}", ""
    return best_topic, ""


def main():
    path = M1_DIR / "question_bank_final.csv"
    df = pd.read_csv(path)
    df["topic"] = df["topic"].astype(object)
    df["subtopic"] = df["subtopic"].astype(object)

    needs_tagging = df["topic"].isna() | (df["topic"] == "")
    print(f"Tagging {needs_tagging.sum()} rows (Math rows already have real topic/subtopic, left untouched)")

    for idx in df[needs_tagging].index:
        topic, subtopic = tag_one(df.at[idx, "subject"], df.at[idx, "question_text"])
        df.at[idx, "topic"] = topic
        df.at[idx, "subtopic"] = subtopic

    df.to_csv(path, index=False)
    print(f"Saved to {path}")

    print("\nTopic distribution (MDCAT-derived rows only):")
    print(df[needs_tagging.values]["topic"].value_counts())

    general_fallback = df[needs_tagging.values]["topic"].str.startswith("General").sum()
    print(f"\n[{'OK' if general_fallback < len(df[needs_tagging]) * 0.3 else 'HIGH'}] "
          f"fell back to 'General <Subject>' (no keyword match): {general_fallback} "
          f"of {needs_tagging.sum()} ({general_fallback / needs_tagging.sum():.0%})")


if __name__ == "__main__":
    main()
