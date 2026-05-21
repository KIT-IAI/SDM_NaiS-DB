from dataclasses import dataclass, field


@dataclass(slots=True)
class Building:
    code: str
    country: str
    building_type: object
    data_type: object
    description: object
    year_class: object
    first_year: object
    last_year: object
    year_class_ext: object
    last_year_ext: object
    roof_1: object
    roof_2: object
    wall_1: object
    wall_2: object
    wall_3: object
    floor_1: object
    floor_2: object
    window_1: object
    window_2: object
    door_1: object
    ref_area: float
    root_2: object = field(init=False)

    def __post_init__(self) -> None:
        # Preserve the original attribute name typo for compatibility.
        self.root_2 = self.roof_2
