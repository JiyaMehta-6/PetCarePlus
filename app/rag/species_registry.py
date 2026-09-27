"""Species registry for PetCare+.

A single source of truth for the 30 supported pet types, used by both the
knowledge-base builder (developer) and the runtime query-understanding layer.
Adding a future species means adding one entry here -- species logic is never
hard-coded across the UI or retrieval code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

# Pet "classes" drive cross-cutting retrieval and KB generation patterns.
CLASS_DOG = "dog"
CLASS_CAT = "cat"
CLASS_SMALL_MAMMAL = "small_mammal"
CLASS_BIRD = "bird"
CLASS_FISH = "fish"
CLASS_REPTILE = "reptile"


@dataclass
class Species:
    key: str
    display: str
    klass: str
    aliases: List[str] = field(default_factory=list)
    # Common breeds recognised for this species (may be empty for non-dog/cat).
    breeds: List[str] = field(default_factory=list)
    # Short human label for UI grouping.
    group: str = ""

    def all_keywords(self) -> List[str]:
        return [self.display.lower(), self.key.lower()] + [a.lower() for a in self.aliases]


SPECIES: List[Species] = [
    # ----- DOGS -----
    Species("indie_dog", "Indian/Indie Dog", CLASS_DOG, ["indie dog", "indian dog", "desi dog", "street dog", "pariah dog"], group="Dog"),
    Species("labrador", "Labrador Retriever", CLASS_DOG, ["labrador", "lab", "labrador retriever"], breeds=["Labrador Retriever"], group="Dog"),
    Species("golden_retriever", "Golden Retriever", CLASS_DOG, ["golden retriever", "golden"], breeds=["Golden Retriever"], group="Dog"),
    Species("german_shepherd", "German Shepherd", CLASS_DOG, ["german shepherd", "gsd", "alsatian"], breeds=["German Shepherd"], group="Dog"),
    Species("spitz_pomeranian", "Indian Spitz / Pomeranian", CLASS_DOG, ["indian spitz", "spitz", "pomeranian", "pom"], breeds=["Indian Spitz", "Pomeranian"], group="Dog"),
    Species("shih_tzu", "Shih Tzu", CLASS_DOG, ["shih tzu", "shihtzu"], breeds=["Shih Tzu"], group="Dog"),
    Species("beagle", "Beagle", CLASS_DOG, ["beagle"], breeds=["Beagle"], group="Dog"),
    Species("rottweiler", "Rottweiler", CLASS_DOG, ["rottweiler", "rottie"], breeds=["Rottweiler"], group="Dog"),
    Species("dachshund", "Dachshund", CLASS_DOG, ["dachshund", "sausage dog", "wiener dog"], breeds=["Dachshund"], group="Dog"),
    Species("pug", "Pug", CLASS_DOG, ["pug"], breeds=["Pug"], group="Dog"),
    Species("english_bulldog", "English Bulldog", CLASS_DOG, ["bulldog", "english bulldog"], breeds=["English Bulldog"], group="Dog"),
    Species("boxer", "Boxer", CLASS_DOG, ["boxer", "boxer dog"], breeds=["Boxer"], group="Dog"),
    Species("standard_poodle", "Standard Poodle", CLASS_DOG, ["poodle", "standard poodle"], breeds=["Standard Poodle"], group="Dog"),
    Species("siberian_husky", "Siberian Husky", CLASS_DOG, ["husky", "siberian husky"], breeds=["Siberian Husky"], group="Dog"),
    Species("doberman", "Doberman Pinscher", CLASS_DOG, ["doberman", "dobermann", "dobie"], breeds=["Doberman Pinscher"], group="Dog"),
    Species("cocker_spaniel", "Cocker Spaniel", CLASS_DOG, ["cocker spaniel", "cocker", "spaniel"], breeds=["Cocker Spaniel"], group="Dog"),
    Species("border_collie", "Border Collie", CLASS_DOG, ["border collie", "collie"], breeds=["Border Collie"], group="Dog"),
    Species("chihuahua", "Chihuahua", CLASS_DOG, ["chihuahua", "chihuahua dog"], breeds=["Chihuahua"], group="Dog"),
    Species("yorkshire_terrier", "Yorkshire Terrier", CLASS_DOG, ["yorkshire terrier", "yorkie", "yorkies"], breeds=["Yorkshire Terrier"], group="Dog"),
    Species("dalmatian", "Dalmatian", CLASS_DOG, ["dalmatian", "dalmatian dog"], breeds=["Dalmatian"], group="Dog"),
    Species("jack_russell", "Jack Russell Terrier", CLASS_DOG, ["jack russell", "jack russell terrier", "jrt"], breeds=["Jack Russell Terrier"], group="Dog"),
    Species("cane_corso", "Cane Corso", CLASS_DOG, ["cane corso", "corso", "italian mastiff"], breeds=["Cane Corso"], group="Dog"),
    # ----- CATS -----
    Species("domestic_shorthair", "Indian/Domestic Shorthair", CLASS_CAT, ["domestic shorthair", "indian cat", "desi cat", "mixed breed cat", "moggy"], group="Cat"),
    Species("persian", "Persian", CLASS_CAT, ["persian", "persian cat"], breeds=["Persian"], group="Cat"),
    Species("maine_coon", "Maine Coon", CLASS_CAT, ["maine coon", "maine coon cat"], breeds=["Maine Coon"], group="Cat"),
    Species("siamese", "Siamese", CLASS_CAT, ["siamese", "siamese cat"], breeds=["Siamese"], group="Cat"),
    Species("bengal", "Bengal", CLASS_CAT, ["bengal", "bengal cat"], breeds=["Bengal"], group="Cat"),
    Species("ragdoll", "Ragdoll", CLASS_CAT, ["ragdoll", "ragdoll cat"], breeds=["Ragdoll"], group="Cat"),
    Species("british_shorthair", "British Shorthair", CLASS_CAT, ["british shorthair", "british cat"], breeds=["British Shorthair"], group="Cat"),
    Species("sphynx", "Sphynx", CLASS_CAT, ["sphynx", "sphinx cat"], breeds=["Sphynx"], group="Cat"),
    Species("exotic_shorthair", "Exotic Shorthair", CLASS_CAT, ["exotic shorthair"], breeds=["Exotic Shorthair"], group="Cat"),
    Species("scottish_fold", "Scottish Fold", CLASS_CAT, ["scottish fold", "fold cat"], breeds=["Scottish Fold"], group="Cat"),
    # ----- SMALL MAMMALS -----
    Species("rabbit", "Rabbit", CLASS_SMALL_MAMMAL, ["rabbit", "bunny", "rabbits"], group="Small mammal"),
    Species("guinea_pig", "Guinea Pig", CLASS_SMALL_MAMMAL, ["guinea pig", "guinea pigs", "cavy", "cavies"], group="Small mammal"),
    Species("syrian_hamster", "Syrian Hamster", CLASS_SMALL_MAMMAL, ["syrian hamster", "hamster", "golden hamster"], group="Small mammal"),
    Species("fancy_rat", "Fancy Rat", CLASS_SMALL_MAMMAL, ["rat", "fancy rat", "pet rat", "rats"], group="Small mammal"),
    Species("chinchilla", "Chinchilla", CLASS_SMALL_MAMMAL, ["chinchilla", "chinchillas"], group="Small mammal"),
    Species("house_mouse", "House Mouse (Fancy Mouse)", CLASS_SMALL_MAMMAL, ["mouse", "fancy mouse", "mice", "pet mouse"], group="Small mammal"),
    Species("gerbil", "Gerbil", CLASS_SMALL_MAMMAL, ["gerbil", "gerbils"], group="Small mammal"),
    Species("hedgehog", "Hedgehog (Pet)", CLASS_SMALL_MAMMAL, ["hedgehog", "hedgehogs", "pet hedgehog"], group="Small mammal"),
    Species("ferret", "Ferret", CLASS_SMALL_MAMMAL, ["ferret", "ferrets"], group="Small mammal"),
    # ----- BIRDS -----
    Species("budgerigar", "Budgerigar / Budgie", CLASS_BIRD, ["budgerigar", "budgie", "budgies", "parakeet"], group="Bird"),
    Species("cockatiel", "Cockatiel", CLASS_BIRD, ["cockatiel", "cockatiels"], group="Bird"),
    Species("lovebird", "Lovebird", CLASS_BIRD, ["lovebird", "lovebirds"], group="Bird"),
    Species("indian_ringneck", "Indian Ringneck Parakeet", CLASS_BIRD, ["indian ringneck", "ringneck", "rose-ringed parakeet", "ring neck"], group="Bird"),
    Species("canary", "Canary", CLASS_BIRD, ["canary", "canaries"], group="Bird"),
    Species("zebra_finch", "Zebra Finch", CLASS_BIRD, ["zebra finch", "finch", "finches"], group="Bird"),
    Species("african_grey", "African Grey Parrot", CLASS_BIRD, ["african grey", "african grey parrot", "grey parrot", "congo grey"], group="Bird"),
    Species("green_cheeked_conure", "Green-cheeked Conure", CLASS_BIRD, ["green cheeked conure", "conure", "green cheek"], group="Bird"),
    Species("blue_gold_macaw", "Blue-and-Gold Macaw", CLASS_BIRD, ["blue and gold macaw", "macaw"], group="Bird"),
    # ----- AQUARIUM FISH -----
    Species("goldfish", "Goldfish", CLASS_FISH, ["goldfish"], group="Aquarium fish"),
    Species("betta", "Betta", CLASS_FISH, ["betta", "betta fish", "siamese fighting fish"], group="Aquarium fish"),
    Species("guppy", "Guppy", CLASS_FISH, ["guppy", "guppies"], group="Aquarium fish"),
    Species("molly", "Molly", CLASS_FISH, ["molly", "mollies"], group="Aquarium fish"),
    Species("platy", "Platy", CLASS_FISH, ["platy", "platies"], group="Aquarium fish"),
    Species("angelfish", "Angelfish", CLASS_FISH, ["angelfish", "angel fish"], group="Aquarium fish"),
    Species("neon_tetra", "Neon Tetra", CLASS_FISH, ["neon tetra", "tetra", "tetras", "neon"], group="Aquarium fish"),
    Species("discus", "Discus", CLASS_FISH, ["discus", "discus fish"], group="Aquarium fish"),
    Species("convict_cichlid", "Convict Cichlid", CLASS_FISH, ["convict cichlid", "convict", "cichlid", "cichlids"], group="Aquarium fish"),
    Species("bristlenose_pleco", "Bristlenose Pleco", CLASS_FISH, ["bristlenose pleco", "pleco", "plecostomus"], group="Aquarium fish"),
    Species("swordtail", "Swordtail", CLASS_FISH, ["swordtail", "swordtail fish"], group="Aquarium fish"),
    Species("dwarf_gourami", "Dwarf Gourami", CLASS_FISH, ["dwarf gourami", "gourami", "gouramis"], group="Aquarium fish"),
    Species("oscar", "Oscar", CLASS_FISH, ["oscar", "oscar fish"], group="Aquarium fish"),
    # ----- REPTILES -----
    Species("aquatic_turtle", "Freshwater Aquatic Turtle", CLASS_REPTILE, ["aquatic turtle", "turtle", "red eared slider", "pond turtle", "water turtle"], group="Reptile"),
    Species("bearded_dragon", "Bearded Dragon", CLASS_REPTILE, ["bearded dragon", "beardie", "bearded dragons"], group="Reptile"),
    Species("leopard_gecko", "Leopard Gecko", CLASS_REPTILE, ["leopard gecko", "gecko", "geckos"], group="Reptile"),
    Species("corn_snake", "Corn Snake", CLASS_REPTILE, ["corn snake"], group="Reptile"),
    Species("ball_python", "Ball Python", CLASS_REPTILE, ["ball python", "python", "royal python"], group="Reptile"),
    Species("indian_star_tortoise", "Indian Star Tortoise", CLASS_REPTILE, ["star tortoise", "indian star tortoise", "tortoise", "tortoises"], group="Reptile"),
    Species("veiled_chameleon", "Veiled Chameleon", CLASS_REPTILE, ["veiled chameleon", "chameleon", "chamaeleo"], group="Reptile"),
]

SPECIES_BY_KEY = {s.key: s for s in SPECIES}

# Map any species term (key, display, alias, or class name) to its class. Used by
# retrieval to match query species against chunk species robustly (e.g. "dog"
# should match a "beagle" chunk, and "small_mammal" should match a "rabbit" chunk).
TERM_TO_CLASS: dict[str, str] = {}
for _sp in SPECIES:
    for _kw in set(_sp.all_keywords() + [_sp.key.lower(), _sp.display.lower()]):
        TERM_TO_CLASS[_kw] = _sp.klass
for _cls in {s.klass for s in SPECIES}:
    TERM_TO_CLASS[_cls] = _cls


# Generic class-level keywords (used in addition to per-species aliases so that
# queries like "my parrot" or "my dog" still route to the right class).
GENERIC_CLASS_KEYWORDS = {
    "dog": CLASS_DOG, "dogs": CLASS_DOG, "puppy": CLASS_DOG, "puppies": CLASS_DOG, "pup": CLASS_DOG,
    "cat": CLASS_CAT, "cats": CLASS_CAT, "kitten": CLASS_CAT, "kittens": CLASS_CAT, "kitties": CLASS_CAT,
    "rabbit": CLASS_SMALL_MAMMAL, "bunny": CLASS_SMALL_MAMMAL,
    "guinea pig": CLASS_SMALL_MAMMAL, "guinea pigs": CLASS_SMALL_MAMMAL,
    "hamster": CLASS_SMALL_MAMMAL, "cavy": CLASS_SMALL_MAMMAL, "cavies": CLASS_SMALL_MAMMAL,
    "rat": CLASS_SMALL_MAMMAL, "rats": CLASS_SMALL_MAMMAL, "mouse": CLASS_SMALL_MAMMAL,
    "mice": CLASS_SMALL_MAMMAL, "chinchilla": CLASS_SMALL_MAMMAL, "gerbil": CLASS_SMALL_MAMMAL,
    "hedgehog": CLASS_SMALL_MAMMAL, "ferret": CLASS_SMALL_MAMMAL,
    "bird": CLASS_BIRD, "birds": CLASS_BIRD, "parrot": CLASS_BIRD, "parrots": CLASS_BIRD,
    "avian": CLASS_BIRD, "parakeet": CLASS_BIRD, "budgie": CLASS_BIRD,
    "cockatiel": CLASS_BIRD, "lovebird": CLASS_BIRD, "canary": CLASS_BIRD, "canaries": CLASS_BIRD,
    "finch": CLASS_BIRD, "finches": CLASS_BIRD, "macaw": CLASS_BIRD, "conure": CLASS_BIRD,
    "fish": CLASS_FISH, "fishes": CLASS_FISH, "goldfish": CLASS_FISH, "betta": CLASS_FISH,
    "tetra": CLASS_FISH, "tetras": CLASS_FISH, "discus": CLASS_FISH, "discus fish": CLASS_FISH,
    "cichlid": CLASS_FISH, "cichlids": CLASS_FISH, "pleco": CLASS_FISH, "gourami": CLASS_FISH,
    "oscar fish": CLASS_FISH, "aquarium fish": CLASS_FISH, "tank fish": CLASS_FISH,
    "reptile": CLASS_REPTILE, "reptiles": CLASS_REPTILE, "turtle": CLASS_REPTILE,
    "tortoise": CLASS_REPTILE, "tortoises": CLASS_REPTILE, "lizard": CLASS_REPTILE,
    "lizards": CLASS_REPTILE, "gecko": CLASS_REPTILE, "geckos": CLASS_REPTILE,
    "snake": CLASS_REPTILE, "snakes": CLASS_REPTILE, "python": CLASS_REPTILE,
    "chameleon": CLASS_REPTILE, "dragon": CLASS_REPTILE, "bearded dragon": CLASS_REPTILE,
}


def detect_species(query: str) -> List[str]:
    """Return the pet *class* names mentioned in a free-text query.

    Class names (``dog``, ``cat``, ``bird``, ...) are what the knowledge base
    uses in chunk ``species`` metadata, so returning classes lets retrieval
    apply metadata-aware boosting directly.
    """
    q = query.lower()
    found = set()
    for sp in SPECIES:
        for kw in sp.all_keywords():
            if kw in q:
                found.add(sp.klass)
                break
    for kw, klass in GENERIC_CLASS_KEYWORDS.items():
        if kw in q:
            found.add(klass)
    return list(found)


def detect_breed(query: str) -> List[str]:
    """Return breed names mentioned in a free-text query."""
    q = query.lower()
    breeds = []
    for sp in SPECIES:
        for b in sp.breeds:
            if b.lower() in q:
                breeds.append(b)
    return breeds


def detect_life_stage(query: str) -> List[str]:
    q = query.lower()
    stages = []
    mapping = {
        "puppy": ["puppy", "pup", "puppies", "newborn dog"],
        "kitten": ["kitten", "kittens", "newborn cat"],
        "baby": ["baby", "infant", "juvenile", "young"],
        "adult": ["adult", "grown", "mature"],
        "senior": ["senior", "old", "elderly", "aging", "aged", "geriatric"],
    }
    for stage, kws in mapping.items():
        if any(k in q for k in kws):
            stages.append(stage)
    return stages
