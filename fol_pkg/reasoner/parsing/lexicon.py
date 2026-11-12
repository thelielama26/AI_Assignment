from __future__ import annotations

import re

DETERMINERS = {"a", "an", "the"}
COPULAS = {"is", "are", "was", "were", "be", "been", "being", "am"}
DO = {"do", "does", "did"}
HAVE = {"has", "have", "had"}
MODALS = {"can", "could", "will", "would", "should", "may", "might", "must", "shall"}
FILLERS = {"regularly", "often", "usually", "frequently", "really", "also", "currently", "typically",
           "generally", "just", "already", "actually", "still"}
PREPOSITIONS = {"in", "on", "at", "of", "from", "by", "to", "with", "for", "near", "into", "about", "as",
                "under", "over", "after", "before", "during", "between", "against", "through", "across",
                "around", "within", "without", "than", "among", "upon", "via"}
PRONOUNS = {"he", "she", "it", "they", "him", "her", "them"}
GENERIC_NOUNS = {"person", "people", "thing", "one", "individual", "ones"}
GENERIC_PRONOUN_QUANTIFIERS = {
    "someone": "exists", "somebody": "exists", "something": "exists",
    "everyone": "forall", "everybody": "forall", "everything": "forall",
    "anyone": "forall", "anybody": "forall", "anything": "forall",
    "nobody": "none", "nothing": "none",
}
QUANTIFIERS = {"all": "forall", "every": "forall", "each": "forall", "any": "forall",
               "no": "none", "some": "exists", "several": "exists"}

IRREGULAR_STEMS = {
    "people": "person", "men": "man", "women": "woman", "children": "child", "feet": "foot",
    "teeth": "tooth", "mice": "mouse", "geese": "goose", "wives": "wife", "lives": "life",
    "knives": "knife", "leaves": "leaf", "persons": "person",
}

IRREGULAR_PAST = {
    "ate": "eat", "wrote": "write", "drank": "drink", "went": "go", "saw": "see", "took": "take",
    "gave": "give", "made": "make", "won": "win", "lost": "lose", "led": "lead", "ran": "run",
    "came": "come", "sat": "sit", "stood": "stand", "told": "tell", "thought": "think",
    "brought": "bring", "built": "build", "bought": "buy", "caught": "catch", "fought": "fight",
    "held": "hold", "kept": "keep", "left": "leave", "met": "meet", "paid": "pay", "said": "say",
    "sold": "sell", "sent": "send", "spent": "spend", "taught": "teach", "understood": "understand",
    "wore": "wear", "began": "begin", "broke": "break", "chose": "choose", "drove": "drive",
    "fell": "fall", "flew": "fly", "forgot": "forget", "got": "get", "grew": "grow", "knew": "know",
    "rode": "ride", "rose": "rise", "sang": "sing", "spoke": "speak", "swam": "swim", "threw": "throw",
    "found": "find", "heard": "hear", "felt": "feel", "became": "become", "put": "put", "set": "set",
    "slept": "sleep", "stole": "steal", "shot": "shoot", "wrote": "write", "hid": "hide", "bit": "bite",
}

BASE_VERBS = """
accept achieve act add admit affect agree allow announce appear apply argue arrive ask attack attend
avoid bake base bear beat become begin believe belong bite break bring build buy call care carry catch
cause celebrate change charge chase check choose claim clean climb close collect come compete complete
compose conduct consider consist contain continue control cook cost count cover create cross cry cut
dance deal decide defeat deliver depend describe design destroy develop die discover discuss draw dream
drink drive drop eat earn edit employ enjoy enter establish exist expect explain face fail fall feed feel
fight fill find finish fit fly focus follow form found gain get give go graduate grow guide handle happen
hate head hear help hit hold hope host hunt identify imagine improve include increase indicate involve
join jump keep kill kiss know lack land last lead learn leave lend let lie like listen live look lose
love maintain make manage mean meet mention move name need notice obtain occur offer open operate order
own participate pass pay perform pick place plan plant play point possess prefer prepare present press
prevent produce promote protect prove provide publish pull push put qualify raise reach read realize
receive recognize record reduce refer reflect refuse regret relate release remain remember remove repeat
replace represent require resist respond rest result return reveal review ride ring rise rule run save
say score search see seek seem sell send serve set share show sign sing sit sleep smell solve speak spend
split stand start stay steal stop study succeed suffer suggest support suppose surprise survive swim take
talk teach tell tend test thank think throw touch train travel treat try turn understand use visit vote
wait walk want warn wash watch wear win wish wonder work worry write jog chaperone premiere locate situate
organize operate publish compose conduct direct produce record release star feature wish pursue further
furthermore teach lecture tour hike fish camp skate ski surf bowl paint draw sketch photograph apply
register enroll attend graduate retire resign hire fire employ dislike admire respect trust fear annoy
bother amuse entertain inspire influence impress defend attack assist advise recommend suggest request
demand declare state report examine inspect investigate analyze measure weigh calculate predict estimate
join leave arrive depart enter exit cross pass reach approach visit host invite welcome greet meet
contribute donate give lend borrow rent lease buy sell trade exchange sponsor fund finance own possess
""".split()


def stem(word: str) -> str:
    w = word.lower()
    if w in IRREGULAR_STEMS:
        return IRREGULAR_STEMS[w]
    if w in IRREGULAR_PAST and w not in {"left", "saw", "found", "set", "put", "bit"}:
        return IRREGULAR_PAST[w]
    if "'" in w or "’" in w or any(c.isdigit() for c in w) or len(w) <= 3:
        return w
    if w.endswith("ies") and len(w) > 4:
        w = w[:-3] + "y"
    elif w.endswith("sses"):
        w = w[:-2]
    elif re.search(r"(ches|shes|xes|zes)$", w):
        w = w[:-2]
    elif w.endswith("ing") and len(w) > 5:
        w = w[:-3]
    elif w.endswith("ed") and len(w) > 4:
        w = w[:-2]
    elif w.endswith("s") and not w.endswith(("ss", "us", "is")):
        w = w[:-1]
    if w.endswith("e") and len(w) > 3:
        w = w[:-1]
    return w


VERB_STEMS = {stem(v) for v in BASE_VERBS}


def is_verb(word: str) -> bool:
    w = word.lower()
    if w in DETERMINERS or w in PREPOSITIONS:
        return False
    return w in IRREGULAR_PAST or stem(w) in VERB_STEMS
