# json to represent the classes below
suppliers = {
    "DPSFULL": {
        "DPSFULL": {
            "3IN1": "CRUDS",
            "COVID": "CRUDS",
            "FLU": "CRUDS",
            "HPV": "CRUDS",
            "MENACWY": "CRUDS",
            "MMR": "CRUDS",
            "RSV": "CRUDS",
        }
    },
    "DPSREDUCED": {
        "DPSREDUCED": {
            "3IN1": "CRUDS",
            "COVID": "CRUDS",
            "FLU": "CRUDS",
            "HPV": "CRUDS",
            "MENACWY": "CRUDS",
            "MMR": "CRUDS",
            "RSV": "CRUDS",
        }
    },
    "MAVIS": {
        "V0V8L": {
            "FLU": "CRUDS",
            "HPV": "CUD",
        }
    },
    "SONAR": {"8HK48": {"FLU": "CD"}},
    "EVA": {"8HA94": {"COVID": "CUD"}},
    "RAVS": {
        "X26": {"MMR": "CRUDS", "RSV": "CRUDS"},
        "X8E5B": {"MMR": "CRUDS", "RSV": "CRUDS"},
    },
    "EMIS": {
        "YGM41": {
            "3IN1": "CRUDS",
            "COVID": "CRUDS",
            "HPV": "CRUDS",
            "MENACWY": "CRUDS",
            "MMR": "CRUDS",
            "RSV": "CRUDS",
        },
        "YGJ": {
            "3IN1": "CRUDS",
            "COVID": "CRUDS",
            "HPV": "CRUDS",
            "MENACWY": "CRUDS",
            "MMR": "CRUDS",
            "RSV": "CRUDS",
        },
    },
    "TPP": {
        "YGA": {
            "3IN1": "CRUDS",
            "HPV": "CRUDS",
            "MENACWY": "CRUDS",
            "MMR": "CRUDS",
            "RSV": "CRUDS",
        }
    },
    "MEDICUS": {
        "YGMYW": {
            "3IN1": "CRUDS",
            "HPV": "CRUDS",
            "MENACWY": "CRUDS",
            "MMR": "CRUDS",
            "RSV": "CRUDS",
        }
    },
}


class OdsVax:
    def __init__(self, ods_code: str, vax: str):
        self.ods_code = ods_code
        self.vax = vax


class TestPair:
    """
    "ods_vax": TestPair.E8HA94_COVID_CUD,
    "ods_vax": TestPair.DPSFULL_COVID_CRUDS,
    "ods_vax": TestPair.X26_MMR_CRUDS,
    "ods_vax": TestPair.YGA_MENACWY_CRUDS,
    """

    X26_MMR_CRUDS = OdsVax("X26", "MMR")
    # X26_RSV_CRUDS = OdsVax("X26", "RSV")
    # X8E5B_MMR_CRUDS = OdsVax("X8E5B", "MMR")
    # X8E5B_RSV_CRUDS = OdsVax("X8E5B", "RSV")
    # YGM41_3IN1_CRUDS = OdsVax("YGM41", "3IN1")
    # YGM41_COVID_CRUDS = OdsVax("YGM41", "COVID")
    # YGM41_HPV_CRUDS = OdsVax("YGM41", "HPV")
    # YGM41_MENACWY_CRUDS = OdsVax("YGM41", "MENACWY")
    # YGM41_MMR_CRUDS = OdsVax("YGM41", "MMR")
    # YGM41_RSV_CRUDS = OdsVax("YGM41", "RSV")
    # YGJ_3IN1_CRUDS = OdsVax("YGJ", "3IN1")
    # YGJ_COVID_CRUDS = OdsVax("YGJ", "COVID")
    # YGJ_HPV_CRUDS = OdsVax("YGJ", "HPV")
    # YGJ_MENACWY_CRUDS = OdsVax("YGJ", "MENACWY")
    # YGJ_MMR_CRUDS = OdsVax("YGJ", "MMR")
    # YGJ_RSV_CRUDS = OdsVax("YGJ", "RSV")
    # DPSFULL_3IN1_CRUDS = OdsVax("DPSFULL", "3IN1")
    DPSFULL_COVID_CRUDS = OdsVax("DPSFULL", "COVID")
    # DPSFULL_FLU_CRUDS = OdsVax("DPSFULL", "FLU")
    # DPSFULL_HPV_CRUDS = OdsVax("DPSFULL", "HPV")
    # DPSFULL_MENACWY_CRUDS = OdsVax("DPSFULL", "MENACWY")
    # DPSFULL_MMR_CRUDS = OdsVax("DPSFULL", "MMR")
    # DPSFULL_RSV_CRUDS = OdsVax("DPSFULL", "RSV")
    # DPSREDUCED_3IN1_CRUDS = OdsVax("DPSREDUCED", "3IN1")
    # DPSREDUCED_COVID_CRUDS = OdsVax("DPSREDUCED", "COVID")
    # DPSREDUCED_FLU_CRUDS = OdsVax("DPSREDUCED", "FLU")
    # DPSREDUCED_HPV_CRUDS = OdsVax("DPSREDUCED", "HPV")
    # DPSREDUCED_MENACWY_CRUDS = OdsVax("DPSREDUCED", "MENACWY")
    # DPSREDUCED_MMR_CRUDS = OdsVax("DPSREDUCED", "MMR")
    # DPSREDUCED_RSV_CRUDS = OdsVax("DPSREDUCED", "RSV")
    # V0V8L_3IN1_CRUDS = OdsVax("V0V8L", "3IN1")
    # V0V8L_FLU_CRUDS = OdsVax("V0V8L", "FLU")
    # V0V8L_HPV_CRUDS = OdsVax("V0V8L", "HPV")
    # V0V8L_MENACWY_CRUDS = OdsVax("V0V8L", "MENACWY")
    # V0V8L_MMR_CRUDS = OdsVax("V0V8L", "MMR")
    # YGA_3IN1_CRUDS = OdsVax("YGA", "3IN1")
    # YGA_HPV_CRUDS = OdsVax("YGA", "HPV")
    YGA_MENACWY_CRUDS = OdsVax("YGA", "MENACWY")
    # YGA_MMR_CRUDS = OdsVax("YGA", "MMR")
    # YGA_RSV_CRUDS = OdsVax("YGA", "RSV")
    # YGMYW_3IN1_CRUDS = OdsVax("YGMYW", "3IN1")
    # YGMYW_HPV_CRUDS = OdsVax("YGMYW", "HPV")
    # YGMYW_MENACWY_CRUDS = OdsVax("YGMYW", "MENACWY")
    # YGMYW_MMR_CRUDS = OdsVax("YGMYW", "MMR")
    # YGMYW_RSV_CRUDS = OdsVax("YGMYW", "RSV")
    # E8HK48_FLU_CD = OdsVax("8HK48", "FLU")
    E8HA94_COVID_CUD = OdsVax("8HA94", "COVID")
