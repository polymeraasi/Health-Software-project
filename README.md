# Health-Software-project
Authors: Jenna Mehto & Vilma Lehto (GUI), Janina Montonen & Pinja Koivisto (back-end)
This project was made during the course Health Software Development Project, in Spring 2024. It utilizes HL7 FHIR -database for retrieving patient data.

Description: The application conforms to an existing risk calculation site called FINRISKI.
The calculator’s algorithms are based on a research article, where the risk percentage is determined
for both stroke and heart attack as well as their combined risk.
The vital sign and other known information are fetched from the HL7 FHIR database,
that includes for example blood pressure, age and gender of the patient.
The rest of the needed information such as diabetes and smoking habits are filled in manually
via questionnaire. The calculated risks are visualized as bar charts and percentages.
