# -*- coding: utf-8 -*-
"""
Schools & Departments — Patras University
The dict insertion order is preserved in Python 3.7+ 
(so the order in the dropdowns is predictable).
"""

from typing import Dict, List

# Schools 
SCHOOLS: List[str] = [
    "ΘΕΤΙΚΩΝ ΕΠΙΣΤΗΜΩΝ",
    "ΠΟΛΥΤΕΧΝΙΚΗ",
    "ΕΠΙΣΤΗΜΩΝ ΥΓΕΙΑΣ",
    "ΑΝΘΡΩΠΙΣΤΙΚΩΝ & ΚΟΙΝΩΝΙΚΩΝ ΕΠΙΣΤΗΜΩΝ",
    "ΟΙΚΟΝΟΜΙΚΩΝ ΕΠΙΣΤΗΜΩΝ & ΔΙΟΙΚΗΣΗΣ",
    "ΓΕΩΠΟΝΙΚΩΝ ΕΠΙΣΤΗΜΩΝ",
    "ΕΠΙΣΤΗΜΩΝ ΑΠΟΚΑΤΑΣΤΑΣΗΣ ΥΓΕΙΑΣ",
]

# Mapping: School -> [Departments]
DEPARTMENTS_BY_SCHOOL: Dict[str, List[str]] = {
    "ΘΕΤΙΚΩΝ ΕΠΙΣΤΗΜΩΝ": [
        "ΒΙΟΛΟΓΙΑΣ",
        "ΜΑΘΗΜΑΤΙΚΩΝ",
        "ΓΕΩΛΟΓΙΑΣ",
        "ΦΥΣΙΚΗΣ",
        "ΕΠΙΣΤΗΜΗΣ ΤΩΝ ΥΛΙΚΩΝ",
        "ΧΗΜΕΙΑΣ",
    ],
    "ΠΟΛΥΤΕΧΝΙΚΗ": [
        "ΑΡΧΙΤΕΚΤΟΝΩΝ ΜΗΧΑΝΙΚΩΝ",
        "ΜΗΧΑΝΟΛΟΓΩΝ & ΑΕΡΟΝΑΥΠΗΓΩΝ ΜΗΧΑΝΙΚΩΝ",
        "ΗΛΕΚΤΡΟΛΟΓΩΝ ΜΗΧΑΝΙΚΩΝ & ΤΕΧΝΟΛΟΓΙΑΣ ΥΠΟΛΟΓΙΣΤΩΝ",
        "ΠΟΛΙΤΙΚΩΝ ΜΗΧΑΝΙΚΩΝ",
        "ΜΗΧΑΝΙΚΩΝ ΗΛΕΚΤΡΟΝΙΚΩΝ ΥΠΟΛΟΓΙΣΤΩΝ & ΠΛΗΡΟΦΟΡΙΚΗΣ",
        "ΧΗΜΙΚΩΝ ΜΗΧΑΝΙΚΩΝ",
    ],
    "ΕΠΙΣΤΗΜΩΝ ΥΓΕΙΑΣ": [
        "ΙΑΤΡΙΚΗΣ",
        "ΦΑΡΜΑΚΕΥΤΙΚΗΣ",
    ],
    "ΑΝΘΡΩΠΙΣΤΙΚΩΝ & ΚΟΙΝΩΝΙΚΩΝ ΕΠΙΣΤΗΜΩΝ": [
        "ΕΠΙΣΤΗΜΩΝ ΤΗΣ ΕΚΠΑΙΔΕΥΣΗΣ & ΚΟΙΝΩΝΙΚΗΣ ΕΡΓΑΣΙΑΣ",
        "ΙΣΤΟΡΙΑΣ - ΑΡΧΑΙΟΛΟΓΙΑΣ",
        "ΕΠΙΣΤΗΜΩΝ ΤΗΣ ΕΚΠΑΙΔΕΥΣΗΣ & ΑΓΩΓΗΣ ΣΤΗΝ ΠΡΟΣΧΟΛΙΚΗ ΗΛΙΚΙΑ",
        "ΦΙΛΟΛΟΓΙΑΣ",
        "ΘΕΑΤΡΙΚΩΝ ΣΠΟΥΔΩΝ",
        "ΦΙΛΟΣΟΦΙΑΣ",
    ],
    "ΟΙΚΟΝΟΜΙΚΩΝ ΕΠΙΣΤΗΜΩΝ & ΔΙΟΙΚΗΣΗΣ": [
        "ΔΙΟΙΚΗΣΗΣ ΕΠΙΧΕΙΡΗΣΕΩΝ",
        "ΔΙΟΙΚΗΤΙΚΗΣ ΕΠΙΣΤΗΜΗΣ & ΤΕΧΝΟΛΟΓΙΑΣ",
        "ΔΙΟΙΚΗΣΗΣ ΤΟΥΡΙΣΜΟΥ",
        "ΟΙΚΟΝΟΜΙΚΩΝ ΕΠΙΣΤΗΜΩΝ",
    ],
    "ΓΕΩΠΟΝΙΚΩΝ ΕΠΙΣΤΗΜΩΝ": [
        "ΓΕΩΠΟΝΙΑΣ",
        "ΑΛΙΕΙΑΣ & ΥΔΑΤΟΚΑΛΛΙΕΡΓΕΙΩΝ",
        "ΕΠΙΣΤΗΜΗΣ & ΤΕΧΝΟΛΟΓΙΑΣ ΤΡΟΦΙΜΩΝ",
        "ΑΕΙΦΟΡΙΚΗΣ ΓΕΩΡΓΙΑΣ",
    ],
    "ΕΠΙΣΤΗΜΩΝ ΑΠΟΚΑΤΑΣΤΑΣΗΣ ΥΓΕΙΑΣ": [
        "ΛΟΓΟΘΕΡΑΠΕΙΑΣ",
        "ΝΟΣΗΛΕΥΤΙΚΗΣ",
        "ΦΥΣΙΚΟΘΕΡΑΠΕΙΑΣ",
    ],
}

# Derived structures (helpful for UI)

# List of all departments (flat), ordered by school
ALL_DEPARTMENTS: List[str] = [dp for sch in SCHOOLS for dp in DEPARTMENTS_BY_SCHOOL[sch]]

# Reverse mapping: Department -> School (useful if you start from a department and want to pre-select a school)
SCHOOL_BY_DEPARTMENT: Dict[str, str] = {
    dp: sch for sch, dps in DEPARTMENTS_BY_SCHOOL.items() for dp in dps
}

# small helper functions
def get_schools() -> List[str]:
    """Returns the list of schools in the order they appear."""
    return SCHOOLS

def get_departments(school: str) -> List[str]:
    """Returns the departments of a school (or an empty list if an unknown school is given)."""
    return DEPARTMENTS_BY_SCHOOL.get(school, [])

def get_school_of_department(department: str) -> str:
    """Returns the school of a department (or an empty string if not found)."""
    return SCHOOL_BY_DEPARTMENT.get(department, "")
