
from stdnum.verhoeff import validate

def is_valid_simple_snomed(simple_snomed: str) -> bool:
    """
    This utility is designed for reuse and should be packaged as part of a 
    shared validation module or service.
    """
    min_snomed_length = 6
    max_snomed_length = 18
    try: 
        return (
            simple_snomed is not None
            and simple_snomed.isdigit()
            and min_snomed_length <= len(simple_snomed) <= max_snomed_length
            and validate(simple_snomed)
            and (simple_snomed[-3:-1] in ("00", "10"))
        )
    except:
        return False
    
# ---------------------------------------------------------------------------------------------------------
# main conversion lookup


class LookUpData:
    # data settings
    allData = {
        "368208006": "Left upper arm structure",
        "279549004": "Nasal cavity structure",
        "74262004": "Oral cavity structure",
        "368209003": "Right upper arm structure",
        "723979003": "Structure of left buttock",
        "61396006": "Structure of left thigh",
        "723980000": "Structure of right buttock",
        "11207009": "Structure of right thigh",
        "420254004": "Body cavity",
        "54471007": "Buccal",
        "372449004": "Dental",
        "372450004": "Endocervical",
        "372451000": "Endosinusial",
        "372452007": "Endotracheopulmonary",
        "404820008": "Epidural",
        "18246711000001107": "Epilesional",
        "372453002": "Extraamniotic",
        "372454008": "Gastroenteral",
        "127490009": "Gastrostomy route",
        "372457001": "Gingival",
        "9191401000001100": "Haemodiafiltration",
        "18682911000001103": "Haemodialysis",
        "10334211000001103": "Haemofiltration",
        "718329006": "Infiltration",
        "18679011000001101": "Inhalation",
        "34777511000001106": "Intestinal use",
        "372458006": "Intraamniotic",
        "58100008": "Intraarterial",
        "12130007": "Intraarticular",
        "372459003": "Intrabursal",
        "418821007": "Intracameral use",
        "372460008": "Intracardiac",
        "372461007": "Intracavernous",
        "420719007": "Intracerebroventricular",
        "19537211000001108": "Intracervical route",
        "372463005": "Intracoronary",
        "372464004": "Intradermal",
        "372465003": "Intradiscal",
        "448077001": "Intraepidermal",
        "38233211000001106": "Intraglandular",
        "372466002": "Intralesional",
        "372467006": "Intralymphatic",
        "78421000": "Intramuscular",
        "255559005": "Intramuscular",
        "372468001": "Intraocular",
        "417255000": "Intraosseous",
        "38239002": "Intraperitoneal",
        "372469009": "Intrapleural",
        "372470005": "Intrasternal",
        "418586008": "Intratendinous route",
        "72607000": "Intrathecal",
        "447122006": "Intratumoral",
        "62226000": "Intrauterine",
        "47625008": "Intravenous",
        "420287000": "Intraventricular cardiac",
        "372471009": "Intravesical",
        "418401004": "Intravitreal",
        "21856811000001103": "Iontophoresis",
        "127491008": "Jejunostomy route",
        "9907001000001103": "Line lock",
        "46713006": "Nasal",
        "127492001": "Nasogastric route",
        "418730005": "Nasojejunal route",
        "54485002": "Ophthalmic route",
        "26643006": "Oral",
        "372473007": "Oromucosal",
        "10547007": "Otic",
        "225691000001105": "PEG tube route",
        "9191501000001101": "Percutaneous",
        "372474001": "Periarticular",
        "39338211000001108": "Peribulbar ocular",
        "3323001000001107": "Pericardial route",
        "372475000": "Perineural",
        "11478901000001102": "Periosseous",
        "419762003": "Peritendinous route",
        "39337511000001107": "Peritumoral",
        "37161004": "Rectal",
        "11564311000001109": "Regional perfusion",
        "418321004": "Retrobulbar route",
        "3594011000001102": "Route of administration not applicable",
        "372476004": "Subconjunctival",
        "34206005": "Subcutaneous",
        "37839007": "Sublingual",
        "419874009": "Submucosal",
        "11564211000001101": "Submucosal rectal",
        "33770711000001104": "Subretinal",
        "6064005": "Topical",
        "45890007": "Transdermal",
        "11479001000001107": "Translingual",
        "404815008": "Transmucosal",
        "90028008": "Urethral",
        "16857009": "Vaginal",
    }

    # Look up the term for the code
    def findLookUp(self, fieldValue):
        try:
            lookUpValue = self.allData[fieldValue]
        except:
            lookUpValue = ""
        return lookUpValue

