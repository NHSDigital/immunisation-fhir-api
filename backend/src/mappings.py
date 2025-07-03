"""Dictionary of vaccine procedure snomed codes and their mapping to vaccine type"""

from dataclasses import dataclass, field


@dataclass
class VaccineTypes:
    """Vaccine types"""

    covid_19: str = "COVID19"
    flu: str = "FLU"
    hpv: str = "HPV"
    mmr: str = "MMR"
    rsv: str = "RSV"

    all: list[str] = field(
        default_factory=lambda: [VaccineTypes.covid_19, VaccineTypes.flu, VaccineTypes.hpv, VaccineTypes.mmr,VaccineTypes.rsv]
    )

@dataclass
class DiseaseDisplayTerms:
    """Disease display terms which correspond to disease codes"""

    covid_19: str = "Disease caused by severe acute respiratory syndrome coronavirus 2"
    flu: str = "Influenza"
    hpv: str = "Human papillomavirus infection"
    measles: str = "Measles"
    mumps: str = "Mumps"
    rubella: str = "Rubella"
    rsv: str = "Respiratory syncytial virus infection (disorder)"

@dataclass
class DiseaseCodes:
    """Disease Codes"""

    # Disease codes can be found at https://hl7.org/fhir/uv/ips/ValueSet-target-diseases-uv-ips.html
    covid_19: str = "840539006"
    flu: str = "6142004"
    hpv: str = "240532009"
    measles: str = "14189004"
    mumps: str = "36989005"
    rubella: str = "36653000"
    rsv: str = "55735004"


vaccine_type_mappings = [
    ([DiseaseCodes.covid_19], VaccineTypes.covid_19),
    ([DiseaseCodes.flu], VaccineTypes.flu),
    ([DiseaseCodes.hpv], VaccineTypes.hpv),
    # IMPORTANT: FOR VACCINE_TYPES WHICH TARGET MULTIPLE DISEASES ENSURE THAT DISEASE CODES ARE SORTED ALPHABETICALLY
    # This allows order-insensitive comparison with other lists, by alphabetically sorting the list for comparison
    (sorted([DiseaseCodes.measles, DiseaseCodes.mumps, DiseaseCodes.rubella]), VaccineTypes.mmr),
    ([DiseaseCodes.rsv], VaccineTypes.rsv),
]


valid_disease_code_combinations = [x[0] for x in vaccine_type_mappings]
