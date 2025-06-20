from constants import Disease, Vaccine
VACCINE_DISEASE_MAPPING = {
    Vaccine.COVID_19: [Disease.COVID_19],
    Vaccine.FLU: [Disease.FLU],
    Vaccine.MMR: [Disease.MEASLES, Disease.MUMPS, Disease.RUBELLA],
    Vaccine.RSV: [Disease.RSV],
}
