def anonymize_text(user_question):
    # Define a pattern for MRN (adjust this regex pattern to match your specific MRN format)
    mrn_pattern = Pattern(
        name="mrn_pattern",
        regex=r"\b[0-9]{7,10}\b",
        score=0.7
    )

    # Create a PatternRecognizer for MRN
    mrn_recognizer = PatternRecognizer(
        supported_entity="MEDICAL_RECORD_NUMBER",
        patterns=[mrn_pattern]
    )
    # Create a custom recognizer registry
    registry = RecognizerRegistry()

    # Create a custom SpacyRecognizer with specific entities
    custom_spacy = SpacyRecognizer(supported_entities=["PERSON", "ORG", "LOC"])

    # Add only the recognizers you want
    registry.add_recognizer(mrn_recognizer)
    registry.add_recognizer(custom_spacy)
    registry.add_recognizer(EmailRecognizer())
    registry.add_recognizer(PhoneRecognizer())
    registry.add_recognizer(UsLicenseRecognizer())
    registry.add_recognizer(UsSsnRecognizer())
    # Add other recognizers as needed, but exclude DateTimeRecognizer

    # Create an AnalyzerEngine with the custom registry
    analyzer = AnalyzerEngine(registry=registry)

    # Define an allow list
    allow_list = allowed_list

    # Analyze text
    results = analyzer.analyze(
        text=user_question, 
        language='en',
        allow_list=allow_list,
        context=emergency_dept_context,
        score_threshold=0.7)

    anonymizer = AnonymizerEngine()
    
    # Anonymize the text based on the analysis results
    anonymized_text = anonymizer.anonymize(text=user_question, analyzer_results=results)
    
    return anonymized_text.text
