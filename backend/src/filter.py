"""Functions for filtering a FHIR Immunization Resource"""

class Filter:
    """Functions for filtering a FHIR Immunization Resource"""

    @staticmethod
    def read(imms: dict):
        """Apply filtering for READ request"""
        imms.pop("identifier")
        return imms
