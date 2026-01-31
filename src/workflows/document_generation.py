from typing import Dict, Any, Optional
from src.agents.document_generation.templates import TemplateRegistry, DocumentTemplate
from src.agents.document_generation.generator import DocumentGenerator
from src.models.activity_law import ActivityLawState

class DocumentGenerationWorkflow:
    """
    Workflow to generate legal documents based on ActivityLawState.
    """
    
    def __init__(self):
        self.generator = DocumentGenerator()

    def run(self, 
            state: Optional[ActivityLawState] = None, 
            template_id: str = "bail_application", 
            user_inputs: Dict[str, Any] = {}, 
            output_dir: str = "output/documents") -> str:
        """
        Executes the document generation workflow.
        
        Args:
            state: The output state from ActivityToLawWorkflow (optional).
            template_id: ID of the template to use.
            user_inputs: Dictionary of user provided values for placeholders.
            output_dir: Directory to save the generated document.
            
        Returns:
            Path to the generated document.
        """
        
        # 1. Get Template
        template = TemplateRegistry.get(template_id)
        if not template:
            raise ValueError(f"Template with ID '{template_id}' not found.")
            
        # 2. Prepare Data
        # Merge data sources: Defaults < State Extraction < User Inputs
        data = template.default_values.copy()
        
        if state:
            extracted_data = self._extract_data_from_state(state)
            data.update(extracted_data)
            
        data.update(user_inputs)
        
        # 3. Validate Data (Optional check for missing keys)
        missing_keys = [key for key in template.required_placeholders if key not in data]
        if missing_keys:
            # In a real agent, we might prompt the user here. 
            # For now, we log/warn or raise if strict. 
            # Let's just warn and fill with placeholders to avoid crashing.
            print(f"Warning: Missing values for {missing_keys}")
            for key in missing_keys:
                data[key] = f"[{key}]"

        # 4. Generate Document
        filename = f"{template_id}_{data.get('APPLICANT_NAME', 'unknown')}.docx".replace(" ", "_")
        output_path = f"{output_dir}/{filename}"
        
        return self.generator.generate(template, data, output_path)

    def _extract_data_from_state(self, state: ActivityLawState) -> Dict[str, Any]:
        """
        Maps ActivityLawState to flat dictionary for template filling.
        Logic depends on how rich the state is.
        """
        data = {}
        
        # Example mapping from state to template keys
        # Assuming state has some structure like risk_assessment or rule_matching results
        
        if state.statute_matching and state.statute_matching.candidate_statutes:
            # Join top statutes as "OFFENCES"
            provisions = [s.provision for s in state.statute_matching.candidate_statutes]
            data["OFFENCES"] = ", ".join(provisions)

        # Logic to extract other fields if they exist in state
        # e.g., if we had a proper 'FactExtraction' pass that got names/dates
        if state.fact_structuring:
            # This is hypothetical as I see 'fact_structuring' in ActivityToLawWorkflow
            # I'd need to peek at what fact_structuring actually produces.
            # For now, let's assume it might have 'entities' or similar.
            pass
            
        return data
