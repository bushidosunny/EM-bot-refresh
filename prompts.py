
create_med_note ="""Write an actual emergency medicine medical note for this patient based on the information we discussed, include good medical decision making under 'Assessment' and 'Differnetial Diagnosis'.
                fill in any missing "Physical Examination" information with most likley information. Do not put in laboratory results or imaging results unless they were provided. Any missing information needed, place triple asteriks (***) in the location. structure the note based on the structure provided by triple backticks.

                ```
                Chief Complaint:
                History of Present Illness:
                Past Medical History:
                Past Social History:
                Medications:
                Allergies:
                Review of Systems:
                Physical Examination:
                Laboratory Results:
                Imaging:
                Assessment:
                Differential Diagnoses:
                Plan:
                Disposition:
                ```"""

pt_education = """You are an emergency medicine specialist tasked with providing patient education materials. Based on the clinical details provided, generate an easy-to-understand patient education note in the specified language. follow the template separated by triple backticks:
    ```
    Diagnoses: List the key medical conditions discussed with the patient, educate them on the diagnosis to help understand their disease.


    Treatment Plan: Explain the treatments or interventions recommended 

    Discharge Instructions: Outline any instructions for care after discharge

    Topics Covered: Summarize the major concepts you reviewed with the patient, such as:
    - Diagnosis details and pathophysiology
    - Medication instructions (dosage, route, side effects)
    - Warning signs/symptoms to watch for  
    - Activity modifications or precautions
    - Follow-up care instructions

    Plan Outline: 
    - Describe any plans for reinforcing or following up on the education provided
    - Note if family members or interpreters were involved 
    - Indicate any barriers addressed (e.g. health literacy, language)

    Structure the patient education note using the following template format:

    Diagnoses:
    [List diagnoses discussed]

    Treatment Plan:  
    [Explain treatments/interventions]

    Discharge Instructions:
    [Outline post-discharge care instructions]

    Topics Covered:
    [Summarize key concepts reviewed]

    Plan Outline:
    [Note reinforcement plans, barriers addressed, interpreters used]
    ```
    Please provide the education note only in the specified patient language. If any critical information is missing to comprehensively create the note, please let me know.
    """ 

optimize_legal_note = f"Check the following medical note separated by triple backticks.  1. Evaluate on its ability to be legally defensible. 2. Suggest what else can be done for the patient before disposition. Separate the importance of the improvement from critical to mild. 3. Rewrite the note with the avialable information. Explain any changes. Be complete and accurate. < >Utizilze the following guidlines: Document all relevant aspects of the patient encounter thoroughly, including chief complaint, history of present illness, review of systems, physical exam findings, diagnostic test results, assessment/differential diagnosis, and treatment plan. Leaving out important details can be problematic legally. Write legibly and clearly. Illegible or ambiguous notes open the door for misinterpretation. Use standard medical terminology and accepted abbreviations. If using an EMR, avoid copy/paste errors. Record in real-time. Chart contemporaneously while details are fresh in your mind rather than waiting until the end of your shift. Late entries raise suspicions. Date, time and sign every entry. This establishes a clear timeline of events. Sign with your full name and credentials.Explain your medical decision making. Articulate your thought process and rationale for diagnosis and treatment decisions. This demonstrates you met the standard of care. Avoid speculation or subjective comments. Stick to objective facts and medical information. Editorializing can be used against you. Make addendums if needed. If you later remember an important detail, it's okay to go back and add it with the current date/time. Never alter original notes. Ensure informed consent is documented. Record that risks, benefits and alternatives were discussed and the patient agreed to the plan. Keep personal notes separate.< >"

disposition_analysis =  f"Analyze the patient's current condition. Assess for safe discharge or if the patient should be admitted. Provide reasons for or against. If it is not clear provide things to consider. Be concise with structured short bullet points"

procedure_checklist = f"Create a procedure checklist of the procedure that should be done immidately before any other procedure for this patient. 1. title the name of the procedure. 2. provide reasoning why this procedure should be done before other possible procedures. 3. Provide Clear procedural instructions. 4. Possible patient complications to look out for. 5. highlight education points for the patient. Use the following format ```1. Procedure name. 2. Reasoning. 3. Supplies   4. Precedure Instructions  5. Possible Complications 6. Patient Education of the Procedure"

summarize_note = """Carefully review the provided clinical note, paying special attention to the patient's chief complaint, relevant history, key findings from the physical exam and diagnostic tests, the primary diagnosis, and the current treatment plan.
    Concisely summarize the most important information needed to quickly understand the patient's situation. Answer in bullet points, use as little bullet points necessary to understand the situation enough, each bullet point does not have to be a complete sentance, like 'follow up with GI' or 'outpatient MRI'  are perfect bullet point examples , 
    including:
    -The main reason they sought care (chief complaint)
    -Key aspects of their relevant medical history
    -Critical findings from the exam and tests
    -The primary diagnosis or differential
    -The major components of the current treatment plan
    After the summary, analyze the available information and treatment plan. Identify any potential gaps in the workup, additional tests or referrals to consider, aspects of the plan that may need adjustment, and any other opportunities to optimize the patient's care.
    Provide your recommendations in a clear, actionable manner. Explain your rationale, citing specific information from the note as needed.
    Ensure your summary and analysis are accurate, logical and grounded in the provided information. Maintain a professional tone and avoid speculation beyond what can be reasonably concluded from the clinical details provided."""    
