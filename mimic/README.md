# MIMIC 

This branch contains exploratory data analysis (EDA) and machine learning pre-processing code for the Medical Information Mart for Intensive Care (MIMIC) dataset, version 1.4.  It does not contain the actual MIMIC dataset which can be downloaded [here](https://physionet.org/content/mimiciii/1.4/).  Note that new users of this data set will have to complete an online ethics training module before being able to download the data.


## Database Structure

All MIMIC tables have a `ROW_ID` field that uniquely identify each row.  In the following, these are not designated as primary keys since the row ID of one table is never used as a foreign key in another table in order to facilitate linking two tables together.



### Defining and Tracking Patient Stays

The database records how a cohort of 46,520 people interact with the hospital system.  Each person is identified by a unique `SUBJECT_ID`.  As described [here](https://physionet.org/content/mimiciii/1.4/), all dates associated with each person are offset by a random amount.  This means that age must be calculated for each person relative to their admission date and admission dates cannot be compared since admissions on the same day for different individuals would be offset by a different amount.

An admission record is created each time a person accesses hospital services.  A single admission can stretch over many days, depending on the service.  One person could potentially have multiple admissions.  Each admission is given a unique `HADM_ID` key.

A subset of admissions involve an ICU stay.  Each ICU stay is given a unique `ICUSTAY_ID`.  Information is also recorded on ICU and cardiac care *callouts*.  A patient is "called out" when they are ready to exit a critical care ward.

While in hospital, transfers between former (previous) and new (current) units are recorded along with admission/discharge dates for the previous units.


| Table | Primary Key | Foreign Key(s) | Notes |
|---|---|---|---|
| [`PATIENTS`](./eda/PATIENTS.ipynb) | `SUBJECT_ID` | None | Birth, death and gender. |
| [`ADMISSIONS`](./eda/ADMISSIONS.ipynb) | `HADM_ID` | `SUBJECT_ID` | Admission/discharge time/location, diagnosis and demographics. |
| [`ICUSTAYS`](./eda/ICUSTAYS.ipynb) | `ICUSTAY_ID` | `SUBJECT_ID`, `HADM_ID` | Ward and admission/discharge times. |
| [`CALLOUT`](./eda/CALLOUT.ipynb) | None | `SUBJECT_ID`, `HADM_ID` | Ward, service, outcome and timing/dates. |
| [`TRANSFERS`](./eda/TRANSFERS.ipynb) | None | `SUBJECT_ID`, `HADM_ID`, `ICUSTAY_ID` | Previous/current unit and previous unit in/out dates. |


### Timestamped Events

A big part of understanding a person's experience in hospital is determining what happens to them and when it happens.  All of the procedures recorded in the tables below are timestamped.  Many of these events are defined in dictionary tables with `D_ITEMS` being a large dictionary that several of the tables described below can link to for more information.  `CAREGIVERS` is another dictionary that defines the job function of the people providing care.

Chart events are the procedures ordered for a person while staying in hospital (ICU or otherwise).  The `DATETIMEEVENTS` table is very similar to `CHARTEVENTS` but has a greater (but not exclusive) focus on ICU patients.  Output events record patient fluid output events (ie. urine production) and is supposed to be for ICU patients only but has some null `ICUSTAY_ID` values.  Lab and microbiology events are lab procedures ordered for a person while in hospital.  In some cases, these events are not associated with a hospital admission so they are most likely done on an outpatient basis.  This is one of the few places in MIMIC that captures outpatient events.  Prescription events include not only the drug and dosing but also the start and end dates of the prescription.  

| Table | Primary Key | Foreign Key(s) | Notes |
|---|---|---|---|
| [`CHARTEVENTS`](./eda/CHARTEVENTS.ipynb) | None | `SUBJECT_ID`, `HADM_ID`, `ICUSTAY_ID`, `ITEMID` | Charted procedures. |
| [`DATETIMEEVENTS`](./eda/DATETIMEEVENTS.ipynb) | None | `SUBJECT_ID`, `HADM_ID`, `ICUSTAY_ID`, `ITEMID`, `cgid` | Charted procedures. |
| [`OUTPUTEVENTS`](./eda/OUTPUTEVENTS.ipynb) | None | `SUBJECT_ID`, `HADM_ID`, `ICUSTAY_ID`, `ITEMID`, `cgid` | Fluid output events. |
| [`D_LABITEMS`](./eda/D_LABITEMS.ipynb) | `itemid` | None | Dictionary of lab procedures. |
| [`LABEVENTS`](./eda/LABEVENTS.ipynb) | None | `itemid`, `SUBJECT_ID`, `HADM_ID` | Lab procedures with results and units. |
| [`MICROBIOLOGYEVENTS`](./eda/MICROBIOLOGYEVENTS.ipynb) | None | `spec_itemid`, `SUBJECT_ID`, `HADM_ID` | Lab procedures with results and units. |
| [`PRESCRIPTIONS`](./eda/PRESCRIPTIONS.ipynb) | None | `SUBJECT_ID`, `HADM_ID`, `ICUSTAY_ID` | Prescriptions and dosing. |
| [`CAREGIVERS`](./eda/CAREGIVERS.ipynb) | `cgid` | None | Caregiver roles. |

Special additional information is recorded for patients in the ICU using two different systems: Philips CareVue and iMDSoft Metavision.  The events recorded in these two systems is defined in more detail in `D_ITEMS`.

| Table | Primary Key | Foreign Key(s) | Notes |
|---|---|---|---|
| [`INPUTEVENTS_CV`](./eda/INPUTEVENTS_CV.ipynb) | None | `SUBJECT_ID`, `HADM_ID`, `ICUSTAY_ID`, `itemid`, `cgid` | ICU procedures. |
| [`INPUTEVENTS_MV`](./eda/INPUTEVENTS_MV.ipynb) | None | `SUBJECT_ID`, `HADM_ID`, `ICUSTAY_ID`, `itemid`, `cgid` | ICU procedures. |

MIMIC also includes de-identified clinician notes which is potentially useful for testing natural language processing (NLP) techniques.

| Table | Primary Key | Foreign Key(s) | Notes |
|---|---|---|---|
| [`NOTEEVENTS`](./eda/NOTEEVENTS.ipynb) | None | `SUBJECT_ID`, `HADM_ID` | Clinician notes. |



### Diagnoses and Procedures
International Classification of Diseases (ICD) codes are used to indicate a patient diagnosis or a procedure administered to a patient.  MIMIC uses the [9th revision](https://www.cdc.gov/nchs/icd/icd9cm.htm) of the ICD system.  These are linked to admissions and are not timestamped.

| Table | Foreign Key(s) | Notes |
|---|---|---|
| [`D_ICD_DIAGNOSES`](./eda/D_ICD_DIAGNOSES.ipynb) | `icd9_code` | Dictionary of ICD9 diagnoses. |
| [`DIAGNOSES_ICD`](./eda/DIAGNOSES_ICD.ipynb) | `SUBJECT_ID`, `HADM_ID` | ICD9 diagnoses linked to patient and admission. |
| [`D_ICD_PROCEDURES`](./eda/D_ICD_PROCEDURES.ipynb) | `icd9_code` | Dictionary of ICD9 procedures. |
| [`PROCEDURES_ICD`](./eda/PROCEDURES_ICD.ipynb) | `SUBJECT_ID`, `HADM_ID` | ICD9 procedures linked to patient and admission. |

Current Procedural Terminology (CPT) codes describe [a range of medical procedures](https://www.cms.gov/medicare/fraud-and-abuse/physicianselfreferral/list_of_codes).  These describe medical interventions as opposed to diagnoses.  A series of CPT records are associated with each admission, each with a CPT code in `cpt_cd`.  This code can be compared to the code ranges provided in the `D_CPT` table to determine intervention category.  Note that these records are not timestamped and are simply linked to each admission `HADM_ID` value.

| Table | Foreign Key(s) | Notes |
|---|---|---|
| [`D_CPT`](./eda/D_CPT.ipynb) | Code subsection range. | CPT dictionary of categories based on CPT code ranges. |
| [`CPTEVENTS`](./eda/CPTEVENTS.ipynb) | `SUBJECT_ID`, `HADM_ID` | CPT codes linked to each patient and admission. |

[Diagnostic Related Group (DRG)](https://en.wikipedia.org/wiki/Diagnosis-related_group) codes were designed to group hospital procedures based on cost.  They are divided into the Health Care Financing Administration (HCFA), Medicare (MS) and All Payers Registry (APR) categories.  They are also linked to each admission.

| Table | Foreign Key(s) | Notes |
|---|---|---|
| [`DRGCODES`](./eda/DRGCODES.ipynb) | `SUBJECT_ID`, `HADM_ID` | DRG codes and descriptions linked to each patient and admission. |




