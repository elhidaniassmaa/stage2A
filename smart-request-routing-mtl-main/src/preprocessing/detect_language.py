import re
from langdetect import detect_langs
from langdetect.lang_detect_exception import LangDetectException
from langdetect import DetectorFactory
DetectorFactory.seed = 0

# Mots-clés caractéristiques de la darija écrite en alphabet latin,
# utilisés pour éviter qu'un message darija ne soit classé "fr" à cause
# de quelques mots français (formules de politesse, ex. "Bonjour", "Pour rappel").
MOTS_DARIJA_LATIN = {
    '2idan', '3aadatan', '3aammatan', '3adatan', '3amatan', '3amdan',
    '3ammatan', '3awdtani', '3awtani', '3awttani', '3erram', '3l3omom',
    '3la', '3lach', '3omoman', '3omouman', '3rram', '5aarj',
    '5arj', '7aalian', '7alian', '7aliyan', '7alyan', '7arfian',
    '7arfyyan', '7da', '7erfian', '7int', '7intach', '7it',
    '7itach', '7na', '7rfyyan', '7tal', '8ia', '8na',
    '8naya', '8oa', '8oma', '8ouma', '8owa', '8ya',
    '9al', '9ariban', '9aryban', '9at3an', '9bal', '9bel',
    '9bl', '9el', '9rib', 'a7yanan', 'a9al', 'aala',
    'aalach', 'abadan', 'aghlab', 'aghlabia', 'akher', 'akhiran',
    'akhor', 'akhr', 'aktar', 'asaasan', 'asasan', 'aslan',
    'automatikian', 'awalan', 'awwalan', 'b3d', 'b3om9', 'b7al',
    'ba3d', 'bach', 'barki', 'batatan', 'bayna', 'bchwia',
    'bchwiyya', 'bchwya', 'bchwyya', 'bdarora', 'bddarora', 'bddaroura',
    'be3d', 'bekri', 'bel3adl', 'bel9a3ida', 'belkamil', 'belm39ol',
    'belm39oul', 'bezaf', 'bezzaf', 'bhal', 'bibasata', 'bin',
    'binaja7', 'bintidam', 'bisalam', 'bistimrar', 'bittali', 'bjoj',
    'bjouj', 'bkri', 'bl2a7ra', 'bl3adl', 'bl8adawa', 'bl9a3ida',
    'blkamil', 'blm39ol', 'blm39oul', 'bnaja7', 'bnisba', 'bnnisba',
    'bntidam', 'bsabab', 'bsbab', 'bso8ola', 'bso8oula', 'bsohoula',
    'bsou8oula', 'bstimrar', 'bttali', 'bwasitat', 'bwodo7', 'bwodou7',
    'bzaf', 'bzerba', 'bzzaf', 'bzzarba', 'bzzerba', 'bzzrba',
    'chakhsyyan', 'chi7ed', 'chi7edd', 'chkhsian', 'chkhsyan', 'chkhsyya',
    'chkon', 'chno', 'chwia', 'da2iman', 'da5l', 'daa5l',
    'daakhl', 'daba', 'dadd', 'daghya', 'daiman', 'dak',
    'dakhl', 'dayman', 'dedd', 'deghya', 'dghia', 'dghya',
    'dial8a', 'dial8om', 'dialha', 'dialhom', 'diali', 'dialna',
    'dialo', 'dialou', 'diawl8a', 'diawl8om', 'diawlha', 'diawlhom',
    'diawli', 'diawlo', 'diawlou', 'dima', 'direct', 'dirict',
    'dirikt', 'dyal8a', 'dyalha', 'dyalhom', 'dyalhoum', 'dyali',
    'dyalna', 'dyalo', 'dyalou', 'dyawl8a', 'dyawlha', 'dyawlhom',
    'dyawlhoum', 'dyawli', 'dyawlna', 'dyawlo', 'dyawlou', 'faj2atan',
    'fel2asas', 'fel7a9i9a', 'felbdia', 'felblasa', 'fi3lian', 'fi3liyan',
    'fi3liyyan', 'fi3lyyan', 'fin', 'fine', 'finemma', 'finmma',
    'fl2asas', 'fl7a9i9a', 'flbdya', 'flblasa', 'flekher', 'flkher',
    'flkhr', 'fllekher', 'fo9ach', 'fog', 'foqach', 'fost',
    'fou9t', 'foug', 'ftija8', 'fttijah', 'fw9t', 'ga3',
    'gddam', 'gddgdd', 'gdgd', 'gedged', 'ghaaliban', 'ghaliban',
    'godam', 'goddam', 'had', 'hada', 'hadak', 'hadchi',
    'hadi', 'hadik', 'hado', 'hadou', 'hda', 'hia',
    'hoa', 'homa', 'houma', 'howa', 'hya', 'idan',
    'ila', 'imken', 'imkn', 'imta', 'jojmrrat', 'kaafi',
    'kafi', 'khaarj', 'khaasatan', 'kharj', 'khasatan', 'khassatan',
    'khososan', 'khosousan', 'kifach', 'kolchi', 'kollchi', 'kolliyan',
    'koulchi', 'koullchi', 'l8i8', 'l9ddam', 'l9eddam', 'lfo9',
    'lfog', 'lfou9', 'lfoug', 'lgddam', 'lgeddam', 'lhih',
    'lil2asaf', 'lilasaf', 'lt7t', 'm3a', 'ma3ada', 'maa',
    'machi', 'mazal', 'mejmo3in', 'mejmou3in', 'men', 'mjmo3in',
    'mjmou3in', 'mnb3d', 'mnbe3d', 'mo255aran', 'mo2kharan', 'mo2khkharan',
    'mora', 'moura', 'naadiran', 'nadiran', 'nisbian', 'nisbiyan',
    'nisbyan', 'nisbyyan', 'nta', 'nti', 'ntoma', 'ntouma',
    'otomatikian', 'otomatikyan', 'qariban', 'qaryban', 'qbel', 'saabi9an',
    'sabi9an', 'sabiqan', 'sara7atan', 'saraa7atan', 't7t', 't9riban',
    't9ryba', 'ta7t', 'ta9riban', 'taab3', 'tab3', 'tab3an',
    'tabaa', 'taht', 'tamaaman', 'tamaman', 'taqriban', 'te7t',
    'te9riban', 'w9tach', 'wa9tach', 'walakin', 'we9tach', 'wra',
    'yawmian', 'yawmiyyan', 'yawmyyan', 'yemken', 'za2id', "kayn", "kayna", "kaynin", "wach", "chno", "dyal", "dyali", "diali",
    "3la", "3lach", "3endi", "3ndi", "bghit", "bzaf", "bezaf", "ghadi",
    "kifach", "n9der", "nta", "nti", "chi", "hadchi", "hadi", "khoya",
    "khti", "mzyan", "mora", "howa", "hiya", "fin", "kanti", "knti",
    "dertik", "labas", "salam", "bla", "daba", "rah", "rak", "mafiha",
    "makayn", "walo", "zwina", "khayb", "khayba", "temchi", "yallah"
}

MOTS_DARIJA_ARABE = {
     'أش', 'أصلا','كيتأخر', 'أُتوماتيكيا', 'إدن', 'إمتا', 'باش', 'باينة','بغيت',
     'بجوج', 'بحال', 'بزّاف', 'بزّربة', 'بسباب','بشويا', 'بشوية',
     'بكري', 'بلعدل', 'بلكامل', 'بلمعقول', 'بلهداوة',
    'بنتضام', 'حتال', 'حدا','حنا', 'حيت', 'دابا', 'داك', 'دغيا', 'ديالنا', 'ديالها',
    'ديالهوم', 'ديالو', 'ديالي', 'دياولنا', 'دياولها', 'دياولهوم',
    'دياولو', 'دياولي', 'ديريكت', 'ديما', 'زائد', 'شكون', 'شنو', 'شويا',
    'طابعا', 'عاوتّاني', 'عرّام', 'علا', 'علاش', 'فلبدية', 'فلبلاصا', 'فلبلاصة', 'فلحقيقة', 'فلخر',
    'فوسط', 'فوقاش', 'فوقت', 'فوڭ', 'فينمّا',
    'قاطعا', 'كتر', 'كولشي', 'كيفاش', 'لفوق', 'لهيه', 'لڭدّام', 'مازال', 'ماشي',
    'مجموعين',  'منبعد', 'مورا',
    'نادر', 'نتا', 'نتوما', 'نتي', 'هادا',
    'هاداك', 'هادو', 'هاديك','هنايا', 
    'هوما', 'وقتاش', 'ڭاع',
    'ڭدّام', 'ڭدڭد', "ديال", "ديالي", "ديالك", "واش", "بزاف", "كاين", "كاينة", "كاينين",
    "غادي", "بغيت", "دابا", "شنو", "علاش", "كيفاش", "راه", "راك",
    "ماكاين", "والو", "زوين", "زوينة", "بحال", "حيت", "هادشي", "هاد",
    "ديك", "خاصني", "تع", "واخا", "دغيا", "مزيان", "خويا", "ختي",
    "نتا", "نتي", "حنا", "بصح", "ماشي", "غا", "دابا", "شحال", "فاش"
}


def _contient_darija_latin(text_lower: str, seuil_mots: int = 2) -> bool:
    """
    Détecte la présence de vocabulaire darija transcrit en alphabet latin,
    en cherchant au moins `seuil_mots` mots caractéristiques dans le texte.
    """
    mots = set(re.findall(r"\b[a-z0-9]+\b", text_lower))
    return len(mots & MOTS_DARIJA_LATIN) >= seuil_mots


def _contient_darija_arabe(text: str, seuil_mots: int = 2) -> bool:
    """
    Détecte la présence de vocabulaire darija en écriture arabe,
    en cherchant au moins `seuil_mots` mots caractéristiques dans le texte.
    """
    mots = set(re.findall(r'[\u0600-\u06FF]+', text))
    return len(mots & MOTS_DARIJA_ARABE) >= seuil_mots


def detect_language(text: str, confidence_threshold: float = 0.7, proximity_threshold: float = 0.3) -> str:
    """
    Détecte la langue dominante d'un texte parmi 5 catégories :
    - 'ar_standard'    : arabe standard (MSA), sans vocabulaire darija détecté.
    - 'darija_arabe'   : darija marocaine écrite en alphabet arabe.
    - 'fr'             : français.
    - 'darija_latin'   : darija transcrite en alphabet latin (arabizi/franco-arabe).
    - 'mixte'          : mélange significatif d'arabe et de français, ou ambigu.
    """
    if not text or not isinstance(text, str):
        return "mixte"

    # FIX : on garde les LETTRES + les CHIFFRES (isalnum) + les ESPACES (isspace).
    # - isalnum() seul aurait supprimé les chiffres si on avait utilisé isalpha() -> cassait
    #   les mots du dictionnaire écrits avec des chiffres (3la, 9bel, n9der...).
    # - il faut IMPÉRATIVEMENT garder aussi les espaces, sinon les mots fusionnent
    #   ("tari9 e" -> "tari9e", "dyal transport" -> "dyaltransport") et la regex
    #   de recherche de mots-clés (\b...\b) ne matche plus rien.
    text_alpha = "".join(c for c in text if c.isalnum() or c.isspace())
    if not text_alpha.strip():
        return "mixte"

    text_lower = text_alpha.lower()

    nb_arabic = len(re.findall(r'[\u0600-\u06FF]', text_alpha))
    nb_latin = len(re.findall(r'[a-zA-ZÀ-ÿ]', text_alpha))
    total_letters = nb_arabic + nb_latin

    if total_letters > 0:
        prop_arabic = nb_arabic / total_letters
        prop_latin = nb_latin / total_letters
        if prop_arabic > 0.15 and prop_latin > 0.15:
            return "mixte"

    if len(text_alpha.strip()) < 20:
        if nb_arabic > 0 and nb_latin == 0:
            return "darija_arabe" if _contient_darija_arabe(text_alpha, seuil_mots=1) else "ar_standard"
        elif nb_latin > 0 and nb_arabic == 0:
            if _contient_darija_latin(text_lower, seuil_mots=1):
                return "darija_latin"
            return "fr"
        else:
            return "mixte"

    if nb_arabic > 0 and nb_latin == 0:
        return "darija_arabe" if _contient_darija_arabe(text_alpha) else "ar_standard"

    try:
        predictions = detect_langs(text_alpha)
        if not predictions:
            return "darija_latin" if _contient_darija_latin(text_lower) else "mixte"

        dominant = predictions[0]
        dom_lang = dominant.lang
        dom_prob = dominant.prob

        prob_ar = next((p.prob for p in predictions if p.lang == 'ar'), 0.0)
        prob_fr = next((p.prob for p in predictions if p.lang == 'fr'), 0.0)

        if prob_ar > 0.0 and prob_fr > 0.0 and abs(prob_ar - prob_fr) < proximity_threshold:
            return "mixte"

        if _contient_darija_latin(text_lower):
            return "darija_latin"

        if dom_prob < confidence_threshold:
            return "mixte"

        if dom_lang == 'fr' and nb_latin > 0:
            return 'fr'
        elif dom_lang == 'ar' and nb_arabic > 0:
            return "darija_arabe" if _contient_darija_arabe(text_alpha) else "ar_standard"
        else:
            return "mixte"

    except LangDetectException:
        return "darija_latin" if _contient_darija_latin(text_lower) else "mixte"