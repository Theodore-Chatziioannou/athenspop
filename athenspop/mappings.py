"""
Mappings between travel survey labels and MATSim population labels 
"""

gender = {
    '0: feamale': 'female',
    '1: male': 'male'
}

education = {
    '1: primary school': 'primary',
    '2: high school': 'secondary',
    '3: bachelor': 'tertiary',
    '4: master or phd': 'tertiary'
}

employment = {
    '1: inactive': 'inactive',
    '2: unemployed': 'unemployed',
    '3: student': 'student',
    '4: active': 'active'
}

car_own = {
    '0: no': 'no',
    '1: yes': 'yes',
}

modes = {
    '1: car': 'car',
    '2: taxi': 'car',
    '3: bus': 'bus',
    '4: train': 'rail',
    '5: motorcycle': 'motorcycle',
    '6: bicycle': 'bike',
    '7: walk': 'walk',
    '8: escooter': 'escooter',
}

purpose = {
    '1: work': 'work',
    '2: return home': 'home',
    '3: education': 'education',
    '4: market': 'shop',
    '5: recreation': 'recreation',
    '6: service': 'other', # small sample size
    '7: other': 'other',
}

income = {
    '0: no income': 'zero',
    '1: 750 or less': 'low',
    '2: 750-1500': 'medium',
    '3: 1500-2500': 'high',
    '4: 2500 or more': 'high',
}

# income_all_categories = {
#     '0: no income': 'zero',
#     '1: 750 or less': 'low',
#     '2: 750-1500': 'medium_low',
#     '3: 1500-2500': 'medium_high',
#     '4: 2500 or more': 'high',
# }

income_all_categories = {
    '0: no income': 'zero',
    '1: 750 or less': 'low',
    '2: 750-1500': 'medium',
    '3: 1500-2500': 'high',
    '4: 2500 or more': 'very_high',
}

age_group = {
    **{x: '0to20' for x in range(0, 21)},
    **{x: '21to39' for x in range(21, 40)},
    **{x: '40to59' for x in range(40, 60)},
    **{x: '60plus' for x in range(60, 120)},
}

zones = {
    1: '1ο Δημοτικό Διαμέρισμα (περιλ. Πλάκα, Κολωνάκι, Σύνταγμα – Ομόνοια – Μοναστηράκι, Εξάρχεια, Ιλίσια κλπ.)',
    2: '2ο Δημοτικό Διαμέρισμα (περιλ. Νέος Κόσμος, Παγκράτι κλπ.)',
    3: '3ο Δημοτικό Διαμέρισμα (περιλ. Βοτανικός, Ρουφ, Θησείο, Μεταξουργείο, Πετράλωνα κλπ.)',
    4: '4ο Δημοτικό Διαμέρισμα (περιλ. Κολωνός, Σεπόλια, Πλατεία Αττικής κλπ.)',
    5: '5ο Δημοτικό Διαμέρισμα (περιλ. Πατήσια, Αγ. Ελευθέριος κλπ.)',
    6: '6ο Δημοτικό Διαμέρισμα (περιλ. Πλατεία Κολιάτσου, Κυψέλη, Σταθμός Λαρίσης κλπ.)',
    7: '7ο Δημοτικό Διαμέρισμα (περιλ. Πολύγωνο, Γκύζη, Αμπελόκηποι, Γουδί κλπ.)',
    8: 'Αγία Βαρβάρα - Χαιδάρι',
    9: 'Άγιοι Ανάργυροι - Καματερό',
    10: 'Αεροδρόμιο',
    11: 'Αιγάλεω',
    12: 'Ανατολική Αττική (περιλ. Κορωπί, Λαύριο, Νέα Μάκρη, Ραφήνα κλπ.)',
    13: 'Βύρωνας',
    14: 'Γαλάτσι',
    15: 'Ζωγράφου',
    16: 'Δάφνη - Υμηττός',
    17: 'Δυτική Αττική (περιλ. Ελευσίνα, Φυλή, Ασπρόπυργος Μέγαρα κλπ.)',
    18: 'Ηλιούπολη - Αργυρούπολη - Αγ. Δημήτριος',
    19: 'Ιλιον - Πετρούπολη - Αχαρνές',
    20: 'Καισαριανή',
    21: 'Καλλιθέα',
    22: 'Μαρούσι - Κηφισιά - Νέα Ερυθραία - Πεντέλη',
    23: 'Μοσχάτο - Ταύρος',
    24: 'Νέα Ιωνία - Ηράκλειο - Μεταμόρφωση - Λυκόβρυση - Πεύκη',
    25: 'Νέα Σμύρνη',
    26: 'Νέα Φιλαδέλφια - Χαλκηδόνα',
    27: 'Νίκαια - Ρέντη',
    28: 'Π. Φάληρο - Άλιμος - Γλυφάδα - Βουλιαγμένη',
    29: 'Παπάγου - Χολαργός',
    30: 'Πειραιάς',
    31: 'Πέραμα - Δραπετσώνα - Κερατσίνι - Κορυδαλλός',
    32: 'Περιστέρι',
    33: 'Σαλαμίνα',
    34: 'Φιλοθέη - Ψυχικό',
    35: 'Χαλάνδρι - Αγ. Παρασκευή - Γερακας - Παλλήνη',
    36: 'Εκτός Αττικής',
}
