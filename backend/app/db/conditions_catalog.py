"""Authoritative condition definitions for seeding and migrations.

Canonical names follow common clinical nomenclature; synonyms support dashboard search
and ingestion query expansion. Keep slugs stable once shipped (URLs and API contracts).
"""

from __future__ import annotations

from typing import TypedDict


class ConditionSeed(TypedDict):
    slug: str
    canonical_name: str
    description: str
    synonyms: list[str]
    rare_disease_flag: bool


CONDITIONS: list[ConditionSeed] = [
    {
        "slug": "nf1",
        "canonical_name": "Neurofibromatosis type 1",
        "description": (
            "Neurofibromatosis type 1 (NF1) is an autosomal dominant disorder caused by pathogenic "
            "variants in NF1. It is characterized by café-au-lait macules, neurofibromas, axillary or "
            "inguinal freckling, Lisch nodules, and an elevated risk of certain neoplasms. Care is "
            "multidisciplinary and individualized."
        ),
        "synonyms": [
            "NF1",
            "NF type 1",
            "Neurofibromatosis 1",
            "Neurofibromatosis type I",
            "von Recklinghausen disease",
            "von Recklinghausen neurofibromatosis",
            "peripheral neurofibromatosis",
            "neurofibromatosis one",
        ],
        "rare_disease_flag": True,
    },
    {
        "slug": "autism-spectrum",
        "canonical_name": "Autism spectrum disorder",
        "description": (
            "Autism spectrum disorder (ASD) is a neurodevelopmental condition characterized by "
            "differences in social communication and interaction, restricted or repetitive "
            "patterns of behavior, interests, or activities, with onset in the developmental period. "
            "Presentation is heterogeneous; supports and services should be individualized."
        ),
        "synonyms": [
            "ASD",
            "Autism",
            "autistic disorder",
            "autism spectrum",
            "pervasive developmental disorder",
            "PDD",
            "PDD-NOS",
            "PDD NOS",
            "Asperger syndrome",
            "Asperger's syndrome",
            "Aspergers",
            "childhood autism",
            "infantile autism",
            "Kanner autism",
            "high-functioning autism",
            "HFA",
            "atypical autism",
            "DSM-5 autism",
        ],
        "rare_disease_flag": False,
    },
    {
        "slug": "alzheimers-disease",
        "canonical_name": "Alzheimer's disease",
        "description": (
            "Alzheimer's disease is the most common cause of dementia in older adults. It is a "
            "progressive neurodegenerative disorder marked by cognitive decline, memory impairment, "
            "and functional impact. Diagnosis and management require clinical assessment and often "
            "multidisciplinary care."
        ),
        "synonyms": [
            "Alzheimer disease",
            "Alzheimers",
            "Alzheimer's",
            "Alzheimer dementia",
            "AD",
            "Alzheimer-type dementia",
            "senile dementia of Alzheimer type",
            "SDAT",
            "DAT",
            "dementia Alzheimer",
        ],
        "rare_disease_flag": False,
    },
    {
        "slug": "parkinsons-disease",
        "canonical_name": "Parkinson's disease",
        "description": (
            "Parkinson's disease is a progressive neurodegenerative movement disorder associated "
            "with dopaminergic cell loss. Core features include bradykinesia with rigidity or rest "
            "tremor, and postural instability in later stages. Treatment is individualized and may "
            "include medications, rehabilitation, and advanced therapies."
        ),
        "synonyms": [
            "Parkinson disease",
            "Parkinson's",
            "Parkinsons",
            "PD",
            "idiopathic Parkinson disease",
            "primary parkinsonism",
            "paralysis agitans",
            "hypokinetic rigid syndrome",
        ],
        "rare_disease_flag": False,
    },
    {
        "slug": "diabetes-mellitus",
        "canonical_name": "Diabetes mellitus",
        "description": (
            "Diabetes mellitus comprises a group of metabolic disorders characterized by hyperglycemia "
            "due to defects in insulin secretion, insulin action, or both. Major forms include type 1, "
            "type 2, and other specific etiologies. Long-term care focuses on glycemic targets, "
            "complication risk reduction, and patient-centered education."
        ),
        "synonyms": [
            "Diabetes",
            "DM",
            "diabetes mellitus",
            "type 1 diabetes",
            "T1D",
            "T1DM",
            "type 2 diabetes",
            "T2D",
            "T2DM",
            "IDDM",
            "insulin-dependent diabetes",
            "NIDDM",
            "non-insulin-dependent diabetes",
            "adult-onset diabetes",
            "juvenile diabetes",
            "MODY",
            "maturity-onset diabetes of the young",
            "LADA",
            "latent autoimmune diabetes in adults",
            "gestational diabetes",
            "GDM",
            "hyperglycemia",
        ],
        "rare_disease_flag": False,
    },
    {
        "slug": "breast-cancer",
        "canonical_name": "Breast cancer",
        "description": (
            "Breast cancer is a malignant neoplasm arising from breast tissue. Subtypes and stages "
            "guide prognosis and therapy, including surgery, radiation, systemic therapy, and "
            "endocrine or targeted approaches when indicated. Care pathways depend on biomarkers, "
            "stage, and patient preferences."
        ),
        "synonyms": [
            "mammary carcinoma",
            "breast carcinoma",
            "invasive ductal carcinoma",
            "IDC",
            "ductal carcinoma",
            "invasive lobular carcinoma",
            "ILC",
            "lobular carcinoma",
            "DCIS",
            "ductal carcinoma in situ",
            "lobular carcinoma in situ",
            "LCIS",
            "TNBC",
            "triple-negative breast cancer",
            "HER2-positive breast cancer",
            "HR-positive breast cancer",
            "ER-positive",
            "PR-positive",
            "metastatic breast cancer",
            "MBC",
            "male breast cancer",
        ],
        "rare_disease_flag": False,
    },
    {
        "slug": "als",
        "canonical_name": "Amyotrophic lateral sclerosis",
        "description": (
            "Amyotrophic lateral sclerosis (ALS) is a progressive neurodegenerative disorder of "
            "upper and lower motor neurons. It causes weakness, atrophy, and spasticity, with variable "
            "pace of progression. Management is multidisciplinary and focuses on function, nutrition, "
            "respiratory support, and communication."
        ),
        "synonyms": [
            "ALS",
            "Lou Gehrig disease",
            "Lou Gehrig's disease",
            "motor neuron disease",
            "MND",
            "Charcot disease",
            "Charcot ALS",
            "classical ALS",
            "sporadic ALS",
            "familial ALS",
            "FALS",
            "progressive bulbar palsy",
            "PBP",
            "primary lateral sclerosis",
            "PLS",
        ],
        "rare_disease_flag": True,
    },
    {
        "slug": "oculodentodigital-dysplasia",
        "canonical_name": "Oculodentodigital dysplasia",
        "description": (
            "Oculodentodigital dysplasia (ODDD) is a rare disorder primarily caused by pathogenic "
            "variants in GJA1, affecting gap junction function. Features can include microphthalmia "
            "or other ocular anomalies, dental abnormalities (e.g., small or missing teeth), and "
            "syndactyly or other digital findings. Neurologic involvement occurs in some individuals. "
            "Care is multidisciplinary and individualized."
        ),
        "synonyms": [
            "ODDD",
            "oddd",
            "oculodentodigital dysplasia",
            "oculo-dento-digital dysplasia",
            "oculodentodigital syndrome",
            "ODD syndrome",
            "GJA1-related disorder",
            "GAP junction disease oculodentodigital",
        ],
        "rare_disease_flag": True,
    },
    {
        "slug": "neuromyelitis-optica-spectrum",
        "canonical_name": "Neuromyelitis optica spectrum disorder",
        "description": (
            "Neuromyelitis optica spectrum disorder (NMOSD) is an autoimmune inflammatory disorder "
            "of the central nervous system that typically targets the optic nerves and spinal cord, "
            "often associated with aquaporin-4 (AQP4) or, in some cases, myelin oligodendrocyte "
            "glycoprotein (MOG) antibodies. It is distinct from multiple sclerosis and requires "
            "specialized diagnosis and long-term management to reduce relapses and disability."
        ),
        "synonyms": [
            "NMOSD",
            "neuromyelitis optica spectrum",
            "neuromyelitis optica",
            "NMO",
            "Devic disease",
            "Devic's disease",
            "AQP4-IgG NMOSD",
            "aquaporin-4 NMOSD",
            "AQP4 antibody positive NMO",
            "NMO spectrum disorder",
        ],
        "rare_disease_flag": True,
    },
]
