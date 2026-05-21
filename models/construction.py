from dataclasses import dataclass


@dataclass(slots=True)
class Construction:
    code: str
    country: str
    variant: object
    element_type: object
    first_year: object
    last_year: object
    name: object
    name_national: object
    description: object
    description_national: object
    u_value: object
    d_insulation: object
    g_value: object
