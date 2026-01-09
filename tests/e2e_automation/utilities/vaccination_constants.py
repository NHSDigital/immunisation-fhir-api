from src.objectModels.api_data_objects import *

VACCINE_CODE_MAP = {
    "COVID": [
        {
            "system": "http://snomed.info/sct",
            "code": "43111411000001101",
            "display": "Comirnaty JN.1 COVID-19 mRNA Vaccine 30micrograms/0.3ml dose dispersion for injection multidose vials (Pfizer Ltd)",
            "stringValue": "Comirnaty JN.1 COVID-19 mRNA Vaccine 30micrograms/0.3ml dose dispersion for injection multidose vials",
            "idValue": "4311141100001101",
            "manufacturer": "Pfizer Ltd"
        },
        {
            "system": "http://snomed.info/sct",
            "code": "43113211000001101",
            "display": "Comirnaty JN.1 Children 6 months - 4 years COVID-19 mRNA Vaccine 3micrograms/0.3ml dose concentrate for dispersion for injection multidose vials (Pfizer Ltd)",
            "stringValue": "Comirnaty JN.1 Children 6 months - 4 years COVID-19 mRNA Vaccine 3micrograms/0.3ml dose concentrate for dispersion for injection multidose vials",
            "idValue": "4311321100001101",
            "manufacturer": "Pfizer Ltd"
        },
        {
            "system": "http://snomed.info/sct",
            "code": "43112711000001100",
            "display": "Comirnaty JN.1 Children 5-11 years COVID-19 mRNA Vaccine 10micrograms/0.3ml dose dispersion for injection single dose vials (Pfizer Ltd)",
            "stringValue": "Comirnaty JN.1 Children 5-11 years COVID-19 mRNA Vaccine 10micrograms/0.3ml dose dispersion for injection single dose vials",
            "idValue": "431127110001100",
            "manufacturer": "Pfizer Ltd"
        },
        {
            "system": "http://snomed.info/sct",
            "code": "42985911000001104",
            "display": "Spikevax JN.1 COVID-19 mRNA Vaccine 0.1mg/ml dispersion for injection multidose vials (Moderna, Inc)",
            "stringValue": "Spikevax JN.1 COVID-19 mRNA Vaccine 0.1mg/ml dispersion for injection multidose vials",
            "idValue": "4298591100001104",
            "manufacturer": "Moderna, Inc"
        }
    ],
    "FLU": [
        {
            "system": "http://snomed.info/sct",
            "code": "34680411000001107",
            "display": "Quadrivalent influenza vaccine (split virion, inactivated) suspension for injection 0.5ml pre-filled syringes (Sanofi Pasteur)",
            "stringValue": "Quadrivalent influenza vaccine (split virion, inactivated) suspension for injection 0.5ml pre-filled syringes",
            "idValue": "3468041100001107",
            "manufacturer": "Sanofi Pasteur"
        }
    ],
    "RSV": [
        {
            "system": "http://snomed.info/sct",
            "code": "42223111000001107",
            "display": "Arexvy vaccine powder and suspension for suspension for injection 0.5ml vials (GlaxoSmithKline UK Ltd)",
            "stringValue": "Arexvy vaccine powder and suspension for suspension for injection 0.5ml vials",
            "idValue": "4222311100001107",
            "manufacturer": "GlaxoSmithKline UK Ltd"
        },
        {
            "system": "http://snomed.info/sct",
            "code": "42605811000001109",
            "display": "Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd)",
            "stringValue": "Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials",
            "idValue": "4260581100001109",
            "manufacturer": "Pfizer Ltd"
        }
    ],
    "HPV": [
        {
            "system": "http://snomed.info/sct",
            "code": "12238911000001100",
            "display": "Cervarix vaccine suspension for injection 0.5ml pre-filled syringes (GlaxoSmithKline) (product)",
            "stringValue": "Gardasil 9 suspension for injection 0.5ml pre-filled syringes",
            "idValue": "12238911000001100",  
            "manufacturer": "GlaxoSmithKline"    
        },
        {
            "system": "http://snomed.info/sct",
            "code": "33493111000001108",
            "display": "Gardasil 9 vaccine suspension for injection 0.5ml pre-filled syringes (Merck Sharp & Dohme (UK) Ltd) (product)",
            "stringValue": "Gardasil 9 suspension for injection 0.5ml pre-filled syringes",
            "idValue": "33493111000001108",  
            "manufacturer": "Merck Sharp & Dohme (UK) Ltd"    
        },
        {
            "system": "http://snomed.info/sct",
            "code": "10880211000001104",
            "display": "Gardasil vaccine suspension for injection 0.5ml pre-filled syringes (Merck Sharp & Dohme (UK) Ltd) (product)",
            "stringValue": "Gardasil 9 suspension for injection 0.5ml pre-filled syringes",
            "idValue": "10880211000001104",  
            "manufacturer": "Merck Sharp & Dohme (UK) Ltd"    
        }
    ] ,
    "MENACWY":[
        {
            "system": "http://snomed.info/sct",
            "code": "39779611000001104",    
            "display": "MenQuadfi vaccine solution for injection 0.5ml vials (Sanofi) (product)",
            "stringValue": "MenQuadfi vaccine solution for injection 0.5ml vials",
            "idValue": "3977961100001104",
            "manufacturer": "Sanofi"
        },
        {
            "system": "http://snomed.info/sct",
            "code": "20517811000001104",    
            "display": "Nimenrix vaccine powder and solvent for solution for injection 0.5ml pre-filled syringes (GlaxoSmithKline UK Ltd) (product)",
            "stringValue": "Nimenrix vaccine powder and solvent for solution for injection 0.5ml pre-filled syringes",
            "idValue": "20517811000001104",
            "manufacturer": "GlaxoSmithKline UK Ltd"
        }
        ,
        {
            "system": "http://snomed.info/sct",
            "code": "17188711000001105",    
            "display": "Menveo vaccine powder and solvent for solution for injection 0.5ml vials (Novartis Vaccines and Diagnostics Ltd) (product)",
            "stringValue": "Menveo vaccine powder and solvent for solution for injection 0.5ml vials",
            "idValue": "17188711000001105",
            "manufacturer": "Novartis Vaccines and Diagnostics Ltd"
        }
    ],
    "3IN1":[
        {   
            "system": "http://snomed.info/sct",
            "code": "7374511000001107",
            "display": "Revaxis vaccine suspension for injection 0.5ml pre-filled syringes (Sanofi) 1 pre-filled disposable injection (product)",
            "stringValue": "Revaxis vaccine suspension for injection 0.5ml pre-filled syringes ",
            "idValue": "7374511000001107",
            "manufacturer": "Sanofi"
        },
    ],
    "MMR":[
        {   
            "system": "http://snomed.info/sct",
            "code": "13968211000001108",
            "display": "M-M-RVAXPRO vaccine powder and solvent for suspension for injection 0.5ml pre-filled syringes (Merck Sharp & Dohme (UK) Ltd)",
            "stringValue": "M-M-RVAXPRO vaccine powder and solvent for suspension for injection 0.5ml pre-filled syringes",
            "idValue": "13968211000001108",
            "manufacturer": "Merck Sharp & Dohme (UK) Ltd"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "34925111000001104",
            "display": "Priorix vaccine powder and solvent for solution for injection 0.5ml pre-filled syringes (GlaxoSmithKline UK Ltd)",
            "stringValue": "Priorix vaccine powder and solvent for solution for injection 0.5ml pre-filled syringes",
            "idValue": "34925111000001104",
            "manufacturer": "GlaxoSmithKline UK Ltd"
        }
    ],
    "MMRV":[
        {   
            "system": "http://snomed.info/sct",
            "code": "45525711000001102",
            "display": "Priorix Tetra vaccine powder and solvent for solution for injection 0.5ml pre-filled syringes (GlaxoSmithKline UK Ltd)",
            "stringValue": "Priorix Tetra vaccine powder and solvent for solution for injection 0.5ml pre-filled syringes",
            "idValue": "45525711000001102",
            "manufacturer": "GlaxoSmithKline UK Ltd"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "45480711000001107",
            "display": "ProQuad vaccine powder and solvent for suspension for injection 0.5ml pre-filled syringes (Merck Sharp & Dohme (UK) Ltd)",
            "stringValue": "ProQuad vaccine powder and solvent for suspension for injection 0.5ml pre-filled syringes",
            "idValue": "45480711000001107",
            "manufacturer": "Merck Sharp & Dohme (UK) Ltd"
        }
    ],
    "PERTUSSIS":[
        {   
            "system": "http://snomed.info/sct",
            "code": "42707511000001109",
            "display": "Adacel vaccine suspension for injection 0.5ml pre-filled syringes (Sanofi)",
            "stringValue": "Adacel vaccine suspension for injection 0.5ml pre-filled syringes",
            "idValue": "42707511000001109",
            "manufacturer": "Sanofi"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "26267211000001100",
            "display": "Boostrix-IPV suspension for injection 0.5ml pre-filled syringes (GlaxoSmithKline UK Ltd) (product)",
            "stringValue": "Boostrix-IPV suspension for injection 0.5ml pre-filled syringes ",
            "idValue": "26267211000001100",
            "manufacturer": "GlaxoSmithKline UK Ltd"
        },
    ],
    "SHINGLES":[
        {   
            "system": "http://snomed.info/sct",
            "code": "39655511000001105",
            "display": "Shingrix (Herpes Zoster) adjuvanted recombinant vaccine powder and suspension for suspension for injection 0.5ml vials (GlaxoSmithKline UK Ltd)",
            "stringValue": "Shingrix (Herpes Zoster) adjuvanted recombinant vaccine powder and suspension for suspension for injection 0.5ml vials",
            "idValue": "39655511000001105",
            "manufacturer": "GlaxoSmithKline UK Ltd"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "38737511000001105",
            "display": "Shingles (Herpes Zoster) adjuvanted recombinant vaccine powder and solvent for suspension for injection 0.5ml vials",
            "stringValue": "Shingles adjuvanted recombinant vaccine powder and solvent for suspension for injection 0.5ml vials",
            "idValue": "38737511000001105",
            "manufacturer": "GlaxoSmithKline UK Ltd"
        }
    ],
    "PNEUMOCOCCAL":[
        {   
            "system": "http://snomed.info/sct",
            "code": "16649411000001104",
            "display": "Prevenar 13 vaccine suspension for injection 0.5ml pre-filled syringes (Pfizer Ltd)",
            "stringValue": "Prevenar 13 vaccine suspension for injection 0.5ml pre-filled syringes",
            "idValue": "16649411000001104",
            "manufacturer": "Pfizer Ltd"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "40600011000001101",
            "display": "Prevenar 20 vaccine suspension for injection 0.5ml pre-filled syringes (Pfizer Ltd)",
            "stringValue": "Prevenar 20 vaccine suspension for injection 0.5ml pre-filled syringes",
            "idValue": "40600011000001101",
            "manufacturer": "Pfizer Ltd"
        }
    ],
    "BCG":[
        {   
            "system": "http://snomed.info/sct",
            "code": "37240111000001101",
            "display": "BCG Vaccine AJV powder for suspension for injection 1ml vials (AJ Vaccines)",
            "stringValue": "BCG Vaccine AJV powder for suspension for injection 1ml vials",
            "idValue": "37240111000001101",
            "manufacturer": "AJ Vaccines"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "9316511000001100",
            "display": "BCG vaccine powder and solvent for suspension for injection vials 10 vial (Pfizer Ltd)",
            "stringValue": "BCG vaccine powder and solvent for suspension for injection vials 10 vial",
            "idValue": "9316511000001100",
            "manufacturer": "Pfizer Ltd"
        }
    ],
    "HEPB":[
        {   
            "system": "http://snomed.info/sct",
            "code": "10752011000001102",
            "display": "HBVAXPRO 10micrograms/1ml vaccine suspension for injection pre-filled syringes (Merck Sharp & Dohme (UK) Ltd)",
            "stringValue": "HBVAXPRO 10micrograms/1ml vaccine suspension for injection pre-filled syringes",
            "idValue": "107520110001102",
            "manufacturer": "Merck Sharp & Dohme (UK) Ltd"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "871822003",
            "display": "Vaccine product containing only Hepatitis B virus antigen (Pfizer Ltd)",
            "stringValue": "Vaccine product containing only Hepatitis B virus antigen",
            "idValue": "871822003",
            "manufacturer": "Pfizer Ltd"
        }
    ],
    "HIB":[
        {   
            "system": "http://snomed.info/sct",
            "code": "9903711000001109",
            "display": "Menitorix powder and solvent for solution for injection 0.5ml vials (GlaxoSmithKline)",
            "stringValue": "Haemophilus type b / Meningococcal C conjugate vaccine powder and solvent for solution for injection 0.5ml vials 1 vial",
            "idValue": "99037110001109",
            "manufacturer": "GlaxoSmithKline UK Ltd"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "9903611000001100",
            "display": "Haemophilus type b / Meningococcal C conjugate vaccine powder and solvent for solution for injection 0.5ml vials 1 vial",
            "stringValue": "Menitorix powder and solvent for solution for injection 0.5ml vials (GlaxoSmithKline)",
            "idValue": "99036110001100",
            "manufacturer": "Sanofi"
        }
    ],
    "MENB":[    
        {   
            "system": "http://snomed.info/sct",
            "code": "23584211000001109",
            "display": "Bexsero vaccine suspension for injection 0.5ml pre-filled syringes (GlaxoSmithKline UK Ltd)",
            "stringValue": "Bexsero vaccine powder and solvent for solution for injection 0.5ml vials",
            "idValue": "235842110001109",
            "manufacturer": "GlaxoSmithKline UK Ltd"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "37430711000001103",
            "display": "Bexsero vaccine suspension for injection 0.5ml pre-filled syringes (CST Pharma Ltd) 1 pre-filled disposable injection",
            "stringValue": "Bexsero vaccine suspension for injection 0.5ml pre-filled syringes (GlaxoSmithKline UK Ltd)",
            "idValue": "374307110001103",
            "manufacturer": "Pfizer Ltd"
        }
    ],
    "ROTAVIRUS":[
        {   
            "system": "http://snomed.info/sct",
            "code": "34609911000001106",
            "display": "Rotarix vaccine live oral suspension 1.5ml tube (GlaxoSmithKline UK Ltd)",
            "stringValue": "Rotarix oral vaccine suspension for oral administration 1.5ml pre-filled syringes",
            "idValue": "34609911000001106",
            "manufacturer": "GlaxoSmithKline UK Ltd"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "17996111000001109",
            "display": "Rotavirus vaccine live oral suspension 1.5ml pre-filled syringes",
            "stringValue": "Rotarix vaccine live oral suspension 1.5ml tube (GlaxoSmithKline UK Ltd)",
            "idValue": "17996111000001109",
            "manufacturer": "Merck Sharp & Dohme (UK) Ltd"
        }
    ],
    "4IN1":[
        {   
            "system": "http://snomed.info/sct",
            "code": "26267211000001100",
            "display": "Boostrix-IPV suspension for injection 0.5ml pre-filled syringes (GlaxoSmithKline UK Ltd)",
            "stringValue": "Vaccine product containing only acellular Bordetella pertussis and Clostridium tetani and Corynebacterium diphtheriae and inactivated whole Human poliovirus antigens",
            "idValue": "1303503001",
            "manufacturer": "GlaxoSmithKline UK Ltd"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "871893003",
            "display": "Vaccine product containing only acellular Bordetella pertussis and Clostridium tetani and Corynebacterium diphtheriae and inactivated whole Human poliovirus antigens",
            "stringValue": "Boostrix-IPV suspension for injection 0.5ml pre-filled syringes (GlaxoSmithKline UK Ltd)",
            "idValue": "1303503001",
            "manufacturer": "Pfizer Ltd"
        }
    ],
    "6IN1":[
        {   
            "system": "http://snomed.info/sct",
            "code": "34765811000001105",
            "display": "Infanrix Hexa vaccine powder and suspension for suspension for injection 0.5ml pre-filled syringes (GlaxoSmithKline UK Ltd) ",
            "stringValue": "Vaccine product containing only Clostridium tetani and Corynebacterium diphtheriae and inactivated Human poliovirus and acellular Bordetella pertussis and Haemophilus influenzae type b and Hepatitis B virus antigens",
            "idValue": "347658110001105",
            "manufacturer": "GlaxoSmithKline UK Ltd"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "1162634005",
            "display": "Pediatric vaccine product containing only acellular Bordetella pertussis, Clostridium tetani and Corynebacterium diphtheriae toxoids, Haemophilus influenzae type b conjugated, Hepatitis B virus and inactivated Human poliovirus antigens",
            "stringValue": "Infanrix Hexa vaccine powder and suspension for suspension for injection 0.5ml pre-filled syringes (GlaxoSmithKline UK Ltd)",
            "idValue": "347658110001105",
            "manufacturer": "GlaxoSmithKline UK Ltd"
        }
    ]
}
VACCINATION_PROCEDURE_MAP = {
    "COVID": [
        {
            "system": "http://snomed.info/sct",
            "code": "1362591000000103",
            "display": "Immunisation course to maintain protection against SARS-CoV-2 (severe acute respiratory syndrome coronavirus 2)",
            "stringValue": "Immunisation course to maintain protection against severe acute respiratory syndrome coronavirus 2 (regime/therapy)",
            "idValue": "1362591000000103"
        },
        {
            "system": "http://snomed.info/sct",
            "code": "1362591000000103",
            "display": "Immunisation course to maintain protection against severe acute respiratory syndrome coronavirus 2 (regime/therapy)",
            "stringValue": "Immunisation course to maintain protection against severe acute respiratory syndrome coronavirus 2",
            "idValue": "1362591000000103"
        }
    ],
    "FLU": [
        {
            "system": "http://snomed.info/sct",
            "code": "884861000000100",
            "display": "Seasonal influenza vaccination (procedure)",
            "stringValue": "Administration of first intranasal seasonal influenza vaccination (procedure)",
            "idValue": "884861000000100"
        },
        {
            "system": "http://snomed.info/sct",
            "code": "884861000000100",
            "display": "Administration of first intranasal seasonal influenza vaccination (procedure)",
            "stringValue": "Seasonal influenza vaccination",
            "idValue": "884861000000100"
        }
    ],
    "RSV": [
        {
            "system": "http://snomed.info/sct",
            "code": "1303503001",
            "display": "Administration of RSV (respiratory syncytial virus) vaccine",
            "stringValue": "Administration of respiratory syncytial virus vaccine",
            "idValue": "1303503001"
        },
        {
            "system": "http://snomed.info/sct",
            "code": "1303503001",
            "display": "Administration of respiratory syncytial virus vaccine",
            "stringValue": "Administration of vaccine product containing only Human orthopneumovirus antigen",
            "idValue": "1303503001"
        }
    ],
    "HPV": [
        {
            "system": "http://snomed.info/sct",
            "code": "761841000",
            "display": "Administration of vaccine product containing only Human papillomavirus antigen (procedure)",
            "stringValue": "Administration of vaccine product containing only Human papillomavirus antigen",
            "idValue": "761841000"
        },
        {
            "system": "http://snomed.info/sct",
            "code": "761841000",
            "display": "Administration of vaccine product containing only Human papillomavirus antigen (procedure)",
            "stringValue": "Administration of vaccine product containing only Human papillomavirus antigen",
            "idValue": "761841000"
        }
    ],
    "MENACWY": [ 
        {
            "system": "http://snomed.info/sct",
            "code": "871874000",
            "display": "Administration of vaccine product containing only Neisseria meningitidis serogroup A, C, W135 and Y antigens (procedure)",
            "stringValue": "Administration of vaccine product containing only Neisseria meningitidis serogroup ",
            "idValue": "871874000"
        },
        {
            "system": "http://snomed.info/sct",
            "code": "871874000",
            "display": "Administration of vaccine product containing only Neisseria meningitidis serogroup A, C, W135 and Y antigens (procedure)",
            "stringValue": "Administration of vaccine product containing only Neisseria meningitidis serogroup ",
            "idValue": "871874000"
        }
    ],
    "MMR": [
        {
            "system": "http://snomed.info/sct",
            "code": "170433008",
            "display": "Administration of second dose of vaccine product containing only Measles morbillivirus and Mumps orthorubulavirus and Rubella virus antigens",
            "stringValue": "Administration of vaccine product containing only Measles virus and Mumps virus and Rubella virus antigens",
            "idValue": "866186002"
        },
         {
            "system": "http://snomed.info/sct",
            "code": "38598009",
            "display": "Administration of vaccine product containing only Measles morbillivirus and Mumps orthorubulavirus and Rubella virus antigens",
            "stringValue": "Administration of vaccine product containing only Measles virus and Mumps virus and Rubella virus antigens",
            "idValue": "8666002"
        }
    ],
    "MMRV": [
        {
            "system": "http://snomed.info/sct",
            "code": "432636005",
            "display": "Administration of vaccine product containing only Human alphaherpesvirus 3 and Measles morbillivirus and Mumps orthorubulavirus and Rubella virus antigens",
            "stringValue": "vaccine product containing only Human alphaherpesvirus 3 and Measles morbillivirus and Mumps orthorubulavirus and Rubella virus antigens",
            "idValue": "866182"
        },
        {
            "system": "http://snomed.info/sct",
            "code": "433733003",
            "display": "Administration of vaccine product containing only Human alphaherpesvirus 3 and Measles morbillivirus and Mumps orthorubulavirus and Rubella virus antigens",
            "stringValue": "Administration of vaccine product containing only Human alphaherpesvirus 3 and Measles morbillivirus and Mumps orthorubulavirus and Rubella virus antigens",
            "idValue": "86602"
        }
    ],
    "SHINGLES": [
        {   
            "system": "http://snomed.info/sct",
            "code": "722215002",
            "display": "Administration of vaccine product containing only Human alphaherpesvirus 3 antigen for shingles (procedure)",
            "stringValue": "Administration of vaccine product containing only Human alphaherpesvirus 3 antigen for shingles",
            "idValue": "4326365"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "1326111000000107",
            "display": "Administration of second dose of vaccine product containing only Human alphaherpesvirus 3 antigen for shingles (procedure)",
            "stringValue": "Administration of second dose of vaccine product containing only Human alphaherpesvirus 3 antigen for shingles",
            "idValue": "432636512"
        }        
    ],
    "3IN1": [
        {
            "system": "http://snomed.info/sct",
            "code": "414619005",
            "display": "Administration of vaccine product containing only Clostridium tetani and low dose Corynebacterium diphtheriae and inactivated Human poliovirus antigens",
            "stringValue": "Administration of vaccine product containing only Clostridium tetani and Corynebacterium diphtheriae and inactivated Human poliovirus antigens",
            "idValue": "866182"
        },
        {
            "system": "http://snomed.info/sct",
            "code": "866227002",
            "display": "Administration of booster dose of vaccine product containing only Clostridium tetani and Corynebacterium diphtheriae and Human poliovirus antigens",
            "stringValue": "Administration of vaccine product containing only Clostridium tetani and low dose Corynebacterium diphtheriae and inactivated Human poliovirus antigens",
            "idValue": "8662002"
        }
    ],
    "PERTUSSIS": [
        {   
            "system": "http://snomed.info/sct",
            "code": "956951000000104",
            "display": "Pertussis vaccination in pregnancy (procedure)",
            "stringValue": "Pertussis vaccination in pregnancy",
            "idValue": "1000000104"
        },
    ],
    "PNEUMOCOCCAL": [
        {   
            "system": "http://snomed.info/sct",
            "code": "722215002",
            "display": "Administration of vaccine product containing only Human alphaherpesvirus 3 antigen for shingles (procedure)",
            "stringValue": "Administration of vaccine product containing only Human alphaherpesvirus 3 antigen for shingles",
            "idValue": "4326365"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "247631000000101",
            "display": "First pneumococcal conjugated vaccination",
            "stringValue": "First pneumococcal conjugated",
            "idValue": "4326365"
        }
    ],
    "BCG": [
        {   
            "system": "http://snomed.info/sct",
            "code": "42284007",
            "display": "Administration of vaccine product containing only live attenuated Mycobacterium bovis antigen",
            "stringValue": "Requires Bacillus Calmette-Guerin vaccination",
            "idValue": "4326365"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "429069001",
            "display": "Requires Bacillus Calmette-Guerin vaccination",
            "stringValue": "Administration of vaccine product containing only live attenuated Mycobacterium bovis antigen",
            "idValue": "4326365"
        }
    ],
    "HEPB": [
        {   
            "system": "http://snomed.info/sct",
            "code": "170370000",
            "display": "Administration of first dose of vaccine product containing only Hepatitis B virus antigen",
            "stringValue": "Administration of booster dose of vaccine product containing only Hepatitis B virus antigen",
            "idValue": "4326365"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "170373003",
            "display": "Administration of booster dose of vaccine product containing only Hepatitis B virus antigen",
            "stringValue": "Administration of first dose of vaccine product containing only Hepatitis B virus antigen",
            "idValue": "4326365"
        }
    ],
    "HIB": [
        {   
            "system": "http://snomed.info/sct",
            "code": "428975001",
            "display": "Haemophilus influenzae type B Meningitis C (HibMenC) vaccination codes",
            "stringValue": "Haemophilus influenzae type B Meningitis C (HibMenC) vaccination codes",
            "idValue": "4326365"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "712833000",
            "display": "Haemophilus influenzae type B Meningitis C (HibMenC) vaccination codes",
            "stringValue": "Haemophilus influenzae type B Meningitis C (HibMenC) vaccination codes",
            "idValue": "4326365"
        }
    ],
    "MENB": [
        {   
            "system": "http://snomed.info/sct",
            "code": "720539004",
            "display": "Administration of first dose of vaccine product containing only Neisseria meningitidis serogroup B antigen",
            "stringValue": "Recombinant meningococcal group B and outer membrane vesicle vaccination",
            "idValue": "235842110001109",
            "manufacturer": "GlaxoSmithKline UK Ltd"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "516301000000101",
            "display": "Recombinant meningococcal group B and outer membrane vesicle vaccination",
            "stringValue": "Administration of first dose of vaccine product containing only Neisseria meningitidis serogroup B antigen",
            "idValue": "516301000101",
            "manufacturer": "CST Pharma Ltd"
        }
    ],
    "ROTAVIRUS": [
        {   
            "system": "http://snomed.info/sct",
            "code": "868631000000102",
            "display": "First rotavirus vaccination",
            "stringValue": "Administration of vaccine product containing only Rotavirus antigen",
            "idValue": "4326365"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "415354003",
            "display": "Administration of vaccine product containing only Rotavirus antigen",
            "stringValue": "First rotavirus vaccination",
            "idValue": "4326365"
        }
    ],
    "4IN1": [
        {   
            "system": "http://snomed.info/sct",
            "code": "868273007",
            "display": "Administration of vaccine product containing only Bordetella pertussis and Clostridium tetani and Corynebacterium diphtheriae and Human poliovirus antigens",
            "stringValue": "Administration of vaccine product containing only acellular Bordetella pertussis and Clostridium tetani and Corynebacterium diphtheriae and inactivated whole Human poliovirus antigens",
            "idValue": "1303503001"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "247821000000102",
            "display": "Booster diphtheria, tetanus, acellular pertussis and inactivated polio vaccination",
            "stringValue": "Administration of vaccine product containing only acellular Bordetella pertussis and Clostridium tetani and Corynebacterium diphtheriae and inactivated whole Human poliovirus antigens",
            "idValue": "1303503001"
        }
    ],
    "6IN1": [
         {   
            "system": "http://snomed.info/sct",
            "code": "1082441000000108",
            "display": "First diphtheria, tetanus and acellular pertussis, inactivated polio, Haemophilus influenzae type b and hepatitis B vaccination",
            "stringValue": "Administration of vaccine product containing only acellular Bordetella pertussis and Clostridium tetani and Corynebacterium diphtheriae and inactivated whole Human poliovirus antigens",
            "idValue": "1303503001"
        },
        {   
            "system": "http://snomed.info/sct",
            "code": "1162640003",
            "display": "Administration of vaccine product containing only acellular Bordetella pertussis and Clostridium tetani and Corynebacterium diphtheriae and Haemophilus influenzae type b and Hepatitis B virus and inactivated Human poliovirus antigens",
            "stringValue": "Administration of vaccine product containing only acellular Bordetella pertussis and Clostridium tetani and Corynebacterium diphtheriae and inactivated whole Human poliovirus antigens",
            "idValue": "1303503001"
        }
    ]
            
}

SITE_MAP = [
    {
        "system": "http://snomed.info/sct",
        "code": "368208006",
        "display": "Left upper arm structure",
        "idValue": "36820006",
        "stringValue": "Left upper arm structure (body structure)"
    },
    {
        "system": "http://snomed.info/sct",
        "code": "368209003",
        "display": "Right upper arm structure",
        "idValue": "36820903",
        "stringValue": "Right upper arm structure (body structure)"
    }
]


ROUTE_MAP = [
    {
        "system": "http://snomed.info/sct",
        "code": "78421000",
        "display": "Intramuscular",
        "idValue": "7842100",
        "stringValue": "Intramuscular route (qualifier value)"
    },
    {
        "system": "http://snomed.info/sct",
        "code": "34206005",
        "display": "Subcutaneous route (qualifier value)",
        "idValue": "3420605",
        "stringValue": "Subcutaneous route (qualifier value)"
    }
]


DOSE_QUANTITY_MAP = [
    {
    "value": 0.3,
    "unit": "Inhalation - unit of product usage",
    "system": "http://snomed.info/sct",
    "code": "2622896019"
    }
]

REASON_CODE_MAP = [
    {
        "system": "http://snomed.info/sct",
        "code": "443684005",
        "display": "Disease outbreak (event)"
    },
    {
        "system": "http://snomed.info/sct",
        "code": "310578008",
        "display": "Routine immunization schedule"
    }
]

PROTOCOL_DISEASE_MAP = {
    "COVID": [
        {
            "system": "http://snomed.info/sct",
            "code": "840539006",
            "display": "Disease caused by severe acute respiratory syndrome coronavirus 2"
        }
    ],
    "FLU": [
        {
            "system": "http://snomed.info/sct",
            "code": "6142004",
            "display": "Influenza"
        }
    ],
    "RSV": [
        {
            "system": "http://snomed.info/sct",
            "code": "55735004",
            "display": "Respiratory syncytial virus infection"
        }
    ],
    "HPV": [
        {
            "system": "http://snomed.info/sct",
            "code": "240532009",
            "display": "Human papilloma virus infection"
        }
    ],
    "MMR": [
        {
            "system": "http://snomed.info/sct",
            "code": "14189004",
            "display": "Measles"
        },
        {
            "system": "http://snomed.info/sct",
            "code": "36989005",
            "display": "Mumps"
        },
        {
            "system": "http://snomed.info/sct",
            "code": "36653000",
            "display": "Rubella"
        }        
    ],
    "MMRV": [
      {
            "system": "http://snomed.info/sct",
            "code": "14189004",
            "display": "Measles"
      },
      {
           "system": "http://snomed.info/sct",
            "code": "36989005",
            "display": "Mumps"
      },
      {
            "system": "http://snomed.info/sct",
            "code": "36653000",
            "display": "Rubella"
      },
      {
            "system": "http://snomed.info/sct",
            "code": "38907003",
            "display": "Varicella"
      }
    ],
    "PERTUSSIS": [
      {
            "system": "http://snomed.info/sct",
            "code": "27836007",
            "display": "Pertussis"
      }
    ],
     "SHINGLES": [
      {
            "system": "http://snomed.info/sct",
            "code": "4740000",
            "display": "Herpes zoster"
      }
    ],  
    "PNEUMOCOCCAL": [
      {
        "system": "http://snomed.info/sct",
        "code": "16814004",
        "display": "Pneumococcal infectious disease"
      }
    ],
    "3IN1": [
      {
        "system": "http://snomed.info/sct",
        "code": "398102009",
        "display": "Acute poliomyelitis"
      },
      {
        "system": "http://snomed.info/sct",
        "code": "397430003",
        "display": "Diphtheria caused by Corynebacterium diphtheriae"
      },
      {
        "system": "http://snomed.info/sct",
        "code": "76902006",
        "display": "Tetanus"
      }
    ],
    "MENACWY": [
      {
        "system": "http://snomed.info/sct",
        "code": "23511006",
        "display": "Meningococcal infectious disease"
      }
    ],
    "4IN1": [
      {
        "system": "http://snomed.info/sct",
        "code": "398102009",
        "display": "Acute poliomyelitis"
      },
      {
        "system": "http://snomed.info/sct",
        "code": "397430003",
        "display": "Diphtheria caused by Corynebacterium diphtheriae"
      },
      {
        "system": "http://snomed.info/sct",
        "code": "27836007",
        "display": "Pertussis"
      },
      {
        "system": "http://snomed.info/sct",
        "code": "76902006",
        "display": "Tetanus"
      }      
    ],
    "6IN1": [
      {
        "system": "http://snomed.info/sct",
        "code": "398102009",
        "display": "Acute poliomyelitis"
      },
      {
        "system": "http://snomed.info/sct",
        "code": "397430003",
        "display": "Diphtheria caused by Corynebacterium diphtheriae"
      },
      {
        "system": "http://snomed.info/sct",
        "code": "709410003",
        "display": "Haemophilus influenzae type b infection"
      },
      {
        "system": "http://snomed.info/sct",
        "code": "27836007",
        "display": "Pertussis"
      },
      {
        "system": "http://snomed.info/sct",
        "code": "76902006",
        "display": "Tetanus"
      },
      {
        "system": "http://snomed.info/sct",
        "code": "66071002",
        "display": "Type B viral hepatitis"
      }      
    ],
    "BCG": [
      {
        "system": "http://snomed.info/sct",
        "code": "56717001",
        "display": "Tuberculosis"
      }
    ],
    "HEPB": [
      {
        "system": "http://snomed.info/sct",
        "code": "66071002",
        "display": "Type B viral hepatitis"
      }
    ],
    "HIB": [
      {
        "system": "http://snomed.info/sct",
        "code": "709410003",
        "display": "Haemophilus influenzae type b infection"
      }
    ],
    "MENB": [
      {
        "system": "http://snomed.info/sct",
        "code": "1354584007",
        "display": "Meningococcal infectious disease caused by Neisseria meningitidis serogroup B"
      }
    ],
    "ROTAVIRUS": [
      {
        "system": "http://snomed.info/sct",
        "code": "186150001",
        "display": "Enteritis caused by rotavirus"
      }
    ]
    
  }