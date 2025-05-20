
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
    