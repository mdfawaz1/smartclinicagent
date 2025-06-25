import json
import requests
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("Tools")

class Tools:
    """
    Tools for hospital chatbot using various APIs.
    Contains tools for doctor specialty lookup and appointment management.
    """
    
    def __init__(self, 
                 specialty_api_endpoint: str = "http://eserver/api/his/AppointmentsAPI/InitAll",
                 specialty_api_token: Optional[str] = None,
                 debug_mode: bool = True):
        """
        Initialize the Tools.
        
        Args:
            specialty_api_endpoint: Endpoint for the doctor specialty API
            specialty_api_token: Bearer token for API authentication
            debug_mode: Whether to show detailed debugging information
        """
        self.specialty_api_endpoint = specialty_api_endpoint
        self.specialty_api_token = specialty_api_token or os.getenv("SPECIALTY_API_TOKEN")
        self.debug_mode = debug_mode
        
        # Default headers with token
        self.headers = {
            "accept": "*/*",
            "authorization": f"Bearer {self.specialty_api_token}"
        }
        
        logger.info("Tools initialized with debug_mode=%s", debug_mode)
    
    def get_doctor_specialties(self, parameters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Get doctor specialties from the API.

        Args:
            parameters: Parameters for the API call (e.g., {"query": "cardio"}).
               If None, returns all specialties.

        Returns:
            Doctor specialty information.
        """
        if parameters is None:
            parameters = {"query": "all available specialties"}

        try:
            logger.info(f"Making API request to {self.specialty_api_endpoint}")
            response = requests.get(
                self.specialty_api_endpoint,
                headers=self.headers
            )
            response.raise_for_status()

            # For demonstration/debug, log the raw response
            if self.debug_mode:
                logger.info(f"Raw API response: {json.dumps(response.json(), indent=2)[:500]}...")

            # Get all specialties from the response
            all_specialties = response.json().get("Codes", {}).get("SPECIALITY", [])
            logger.info(f"Retrieved {len(all_specialties)} specialties from API")

            # If a query parameter is provided, filter the results
            query = parameters.get("query", "").upper()

            # Check if this is a request for the full list
            full_list_terms = ["FULL", "ALL", "COMPLETE", "YES", "YEAH", "SURE", "LIST", "SHOW", "MORE"]
            is_full_list_request = any(term in query.split() for term in full_list_terms)

            # Check if this is a general query about available specialties
            general_query_terms = ["AVAILABLE", "LIST", "ALL", "WHAT", "WHICH", "HAVE", "OFFER"]
            is_general_query = any(term in query for term in general_query_terms)

            # For full list requests or general queries, return all specialties
            if is_full_list_request or is_general_query:
                logger.info("Returning all specialties (full list request or general query)")
                return {"specialties": all_specialties, "is_full_list": True}

            # For specific specialty queries
            if query:
                # Extract query terms for more flexible matching
                query_terms = query.split()

                # Filter out common words that aren't helpful for matching
                stop_words = ["WHAT", "WHICH", "ARE", "IS", "THE", "DO", "DOES", "YOU", "HAVE", "AVAILABLE", "THERE", "ANY", "FOR", "A", "AN", "IN", "AT", "BY", "WITH", "ABOUT", "PLEASE", "CAN", "COULD", "WOULD"]
                query_terms = [term for term in query_terms if term not in stop_words]

                logger.info(f"Filtering specialties by query terms: {query_terms}")
                filtered_specialties = []

                # Check each specialty against each query term
                for specialty in all_specialties:
                    desc = specialty.get("DESCRIPTION", "").upper()

                    # Match if any term is contained in the description
                    if any(term in desc for term in query_terms):
                        filtered_specialties.append(specialty)

                logger.info(f"Found {len(filtered_specialties)} matching specialties")
                return {"specialties": filtered_specialties}
            else:
                # For empty queries, return all specialties
                logger.info("Returning all specialties (no specific terms)")
                return {"specialties": all_specialties}

        except Exception as e:
            logger.error(f"Error calling specialty API: {str(e)}")
            return {"error": str(e)}
    
    # APPOINTMENT-RELATED TOOLS
    
    def activate_sso(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Activate SSO for a user.
        
        Args:
            parameters: Optional parameters (not used in this function)
            
        Returns:
            SSO activation result
        """
        try:
            url = "http://eserver/api/visitmgmt/Accounts/ActivateSSO?Id=$2a$06$209Th1Z/ZBraqhPa2PIQDeM/7T65Y6Y6MRS6YjefwVomvFAuMwYtG"
            res = requests.get(url, headers={"accept": "*/*"})
            return res.json()
        except Exception as e:
            logger.error(f"Error activating SSO: {str(e)}")
            return {"error": str(e)}
    
    def search_by_id_number(self, parameters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Search for a patient by ID number.
        
        Args:
            parameters: Parameters for the search (e.g., {"id_number": "DD15021998"}).
                       If None, returns parameter requirements.
            
        Returns:
            Search results or parameter requirements
        """
        if parameters is None or not parameters.get("id_number"):
            return ParameterCollector.get_parameter_requirements("search_by_id_number")
        
        if not ParameterCollector.validate_parameters("search_by_id_number", parameters):
            return ParameterCollector.get_parameter_requirements("search_by_id_number")
            
        try:
            id_number = parameters.get("id_number", "DD15021998")
            url = f"http://eserver/api/clinicaldocs/Codes/SearchText?CodeName=CHECKIDNO&text={id_number}"
            res = requests.get(url, headers=self.headers)
            return res.json()
        except Exception as e:
            logger.error(f"Error searching by ID number: {str(e)}")
            return {"error": str(e)}
    
    def get_today_appointments(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get today's appointments.
        
        Args:
            parameters: Optional parameters (not used in this function)
            
        Returns:
            Today's appointments
        """
        try:
            url = "http://eserver/api/clinicaldocs/VisitDocs/GetRecordset?VisitId=3598&QueryName=GET_TODAYAPPTS"
            res = requests.get(url, headers=self.headers)
            return res.json()
        except Exception as e:
            logger.error(f"Error getting today's appointments: {str(e)}")
            return {"error": str(e)}
    
    def get_ongoing_visits(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get ongoing visits.
        
        Args:
            parameters: Optional parameters (not used in this function)
            
        Returns:
            Ongoing visits
        """
        try:
            url = "http://eserver/api/clinicaldocs/VisitDocs/GetRecordset?VisitId=3598&QueryName=GET_ONGOINGVISITS"
            res = requests.get(url, headers=self.headers)
            return res.json()
        except Exception as e:
            logger.error(f"Error getting ongoing visits: {str(e)}")
            return {"error": str(e)}
    
    def init_appointments(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Initialize appointments API.
        
        Args:
            parameters: Optional parameters (not used in this function)
            
        Returns:
            Initialization data
        """
        try:
            url = "http://eserver/api/his/AppointmentsAPI/InitAll"
            res = requests.get(url, headers=self.headers)
            return res.json()
        except Exception as e:
            logger.error(f"Error initializing appointments: {str(e)}")
            return {"error": str(e)}
    
    def get_user_dataset(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get user dataset for appointments.
        
        Args:
            parameters: Parameters for the dataset query. If None, returns parameter requirements.
                - date_from: Start date (default: today)
                - date_to: End date (default: today)
                - resource_type: Resource type (default: 1)
                - specialty_id: Specialty ID (optional)
                - resource_id: Resource ID (optional)
                - clinic_id: Clinic ID (optional)
                - from_time: From time (optional)
                - to_time: To time (optional)
            
        Returns:
            User dataset or parameter requirements
        """
        if parameters is None:
            parameters = {}
            
        # Auto-fill missing required parameters with defaults
        today = datetime.now().strftime("%Y-%m-%d")
        parameters.setdefault("date_from", today)
        parameters.setdefault("date_to", today)
        parameters.setdefault("resource_type", "1")
        
        if not ParameterCollector.validate_parameters("get_user_dataset", parameters):
            return ParameterCollector.get_parameter_requirements("get_user_dataset")
            
        try:
            # Extract parameters with defaults
            date_from = parameters.get("date_from", today)
            date_to = parameters.get("date_to", today)
            resource_type = parameters.get("resource_type", "1")
            
            body = {
                "RESOURCETYPE": resource_type,
                "SPECIALITYID": parameters.get("specialty_id"),
                "RESOURCEID": parameters.get("resource_id"),
                "CLINICID": parameters.get("clinic_id"),
                "FROMDATE": date_from,
                "TODATE": date_to,
                "FROM_TIME": parameters.get("from_time"),
                "TO_TIME": parameters.get("to_time")
            }
            
            url = "http://eserver/api/his/AppointmentsAPI/GetUserDataset?QueryName=APPOINTMENTFINDRESC"
            headers = {**self.headers, "content-type": "application/json"}
            
            res = requests.post(url, headers=headers, json=body)
            return res.json()
        except Exception as e:
            logger.error(f"Error getting user dataset: {str(e)}")
            return {"error": str(e)}
    
    def get_session_slots(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get appointment session slots.
        
        Args:
            parameters: Parameters for the slots query. If None, returns parameter requirements.
                - resource_id: Resource ID (default: 2)
                - session_date: Session date (default: today)
                - session_id: Session ID (default: 363)
            
        Returns:
            Session slots or parameter requirements
        """
        if parameters is None:
            parameters = {}
        
        # For booking appointments, we should ask the user for preferences
        # Only auto-fill if this seems like a general query
        missing_params = []
        if not parameters.get("resource_id"):
            missing_params.append("resource_id")
        if not parameters.get("session_date"):
            missing_params.append("session_date") 
        if not parameters.get("session_id"):
            missing_params.append("session_id")
            
        # If any key parameters are missing, ask the user
        if missing_params:
            return ParameterCollector.get_parameter_requirements("get_session_slots")
        
        if not ParameterCollector.validate_parameters("get_session_slots", parameters):
            return ParameterCollector.get_parameter_requirements("get_session_slots")
            
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            resource_id = parameters.get("resource_id", "2")
            session_date = parameters.get("session_date", today)
            session_id = parameters.get("session_id", "363")
            
            url = f"http://eserver/api/his/AppointmentsAPI/GetSessionSlots?Id={resource_id}&SessionDate={session_date}T00%3A00%3A00.000Z&SessionId={session_id}"
            res = requests.get(url, headers=self.headers)
            return res.json()
        except Exception as e:
            logger.error(f"Error getting session slots: {str(e)}")
            return {"error": str(e)}
    
    def create_walkin(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a walk-in appointment.
        
        Args:
            parameters: Parameters for creating the walk-in. If None, returns parameter requirements.
                - resource_id: Resource ID (default: 2)
                - session_id: Session ID (default: 363)
                - session_date: Session date (default: today)
                - from_time: From time (default: 07:10:00)
                - patient_id: Patient ID (default: 3598)
            
        Returns:
            Walk-in creation result or parameter requirements
        """
        if parameters is None:
            parameters = {}
        
        # For creating appointments, we should ask for key details
        missing_params = []
        if not parameters.get("patient_id"):
            missing_params.append("patient_id")
        if not parameters.get("resource_id"):
            missing_params.append("resource_id")
        if not parameters.get("session_date"):
            missing_params.append("session_date")
            
        # If key parameters are missing, ask the user
        if missing_params:
            return ParameterCollector.get_parameter_requirements("create_walkin")
        
        # Auto-fill less critical parameters with defaults
        today = datetime.now().strftime("%Y-%m-%d")
        parameters.setdefault("resource_id", "2")
        parameters.setdefault("session_id", "363")
        parameters.setdefault("session_date", today)
        parameters.setdefault("from_time", "07%3A10%3A00")
        parameters.setdefault("patient_id", "3598")
        
        if not ParameterCollector.validate_parameters("create_walkin", parameters):
            return ParameterCollector.get_parameter_requirements("create_walkin")
            
        try:
            resource_id = parameters.get("resource_id", "2")
            session_id = parameters.get("session_id", "363")
            session_date = parameters.get("session_date", today)
            from_time = parameters.get("from_time", "07%3A10%3A00")
            patient_id = parameters.get("patient_id", "3598")
            
            url = f"http://eserver/api/his/AppointmentsAPI/CreateWalkin?ResourceId={resource_id}&SessionId={session_id}&SessionDate={session_date}&FromTime={from_time}&PatientId={patient_id}"
            res = requests.get(url, headers=self.headers)
            return res.json()
        except Exception as e:
            logger.error(f"Error creating walk-in: {str(e)}")
            return {"error": str(e)}
    
    def get_appointment_number(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get appointment number.
        
        Args:
            parameters: Optional parameters (not used in this function)
            
        Returns:
            Appointment number
        """
        try:
            url = "http://eserver/api/his/AppointmentsAPI/GetAppointmentNumber"
            res = requests.get(url, headers=self.headers)
            return res.json()
        except Exception as e:
            logger.error(f"Error getting appointment number: {str(e)}")
            return {"error": str(e)}
    
    def create_visit(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a visit from an appointment.
        
        Args:
            parameters: Parameters for creating the visit. If None, returns parameter requirements.
                - appointment_id: Appointment ID to create visit from
            
        Returns:
            Visit creation result or parameter requirements
        """
        if parameters is None or not parameters.get("appointment_id"):
            return ParameterCollector.get_parameter_requirements("create_visit")
        
        if not ParameterCollector.validate_parameters("create_visit", parameters):
            return ParameterCollector.get_parameter_requirements("create_visit")
            
        try:
            appointment_id = parameters.get("appointment_id", "1820")
            url = f"http://eserver/api/his/AppointmentsAPI/CreateVisit?AppointmentId={appointment_id}"
            res = requests.get(url, headers=self.headers)
            return res.json()
        except Exception as e:
            logger.error(f"Error creating visit: {str(e)}")
            return {"error": str(e)}
    
    def get_patient_journey(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get patient journey information.
        
        Args:
            parameters: Parameters for the patient journey. If None, returns parameter requirements.
                - visit_id: Visit ID to get journey for
            
        Returns:
            Patient journey information or parameter requirements
        """
        if parameters is None or not parameters.get("visit_id"):
            return ParameterCollector.get_parameter_requirements("get_patient_journey")
        
        if not ParameterCollector.validate_parameters("get_patient_journey", parameters):
            return ParameterCollector.get_parameter_requirements("get_patient_journey")
            
        try:
            visit_id = parameters.get("visit_id", "3502")
            url = f"http://eserver/api/clinicaldocs/VisitDocs/GetPatientJourney?VisitId={visit_id}"
            res = requests.get(url, headers=self.headers)
            return res.json()
        except Exception as e:
            logger.error(f"Error getting patient journey: {str(e)}")
            return {"error": str(e)}
    
    def get_appointment_followup(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get follow-up appointment information.
        
        Args:
            parameters: Parameters for the follow-up query. If None, returns parameter requirements.
                - patient_id: Patient ID
                - date_from: Start date
                - date_to: End date
            
        Returns:
            Follow-up appointment information or parameter requirements
        """
        if parameters is None:
            parameters = {}
            
        # Auto-fill missing parameters with defaults
        today = datetime.now().strftime("%Y-%m-%d")
        parameters.setdefault("patient_id", "3598")
        parameters.setdefault("date_from", today)
        parameters.setdefault("date_to", today)
        
        if not ParameterCollector.validate_parameters("get_appointment_followup", parameters):
            return ParameterCollector.get_parameter_requirements("get_appointment_followup")
            
        try:
            patient_id = parameters.get("patient_id", "3598")
            date_from = parameters.get("date_from")
            date_to = parameters.get("date_to")
            
            url = f"http://eserver/api/clinicaldocs/VisitDocs/GetRecordset?VisitId={patient_id}&QueryName=GET_FOLLOWUP&ParamDateFrom={date_from}&ParamDateTo={date_to}"
            res = requests.get(url, headers=self.headers)
            return res.json()
        except Exception as e:
            logger.error(f"Error getting appointment followup: {str(e)}")
            return {"error": str(e)}


class ParameterCollector:
    """
    Utility class for handling parameter requirements for API-based interactions.
    """

    @staticmethod
    def get_parameter_requirements(tool_name: str) -> Dict[str, Any]:
        """
        Get parameter requirements for a tool in API-friendly format.
        
        Args:
            tool_name: Name of the tool requiring parameters.
            
        Returns:
            Dictionary with parameter requirements and user-friendly message.
        """
        requirements = {
            "search_by_id_number": {
                "needs_parameters": True,
                "tool_name": tool_name,
                "required_parameters": ["id_number"],
                "parameter_descriptions": {
                    "id_number": "Patient ID number (e.g., 'DD15021998')"
                },
                "user_message": "I need a patient ID number to search for the patient. Please provide the patient ID number."
            },
            "get_user_dataset": {
                "needs_parameters": True,
                "tool_name": tool_name,
                "required_parameters": ["date_from", "date_to", "resource_type"],
                "optional_parameters": ["specialty_id", "resource_id", "clinic_id", "from_time", "to_time"],
                "parameter_descriptions": {
                    "date_from": "Start date (YYYY-MM-DD format)",
                    "date_to": "End date (YYYY-MM-DD format)",
                    "resource_type": "Resource type (1 for Doctor, 2 for Room)",
                    "specialty_id": "Specialty ID (optional)",
                    "resource_id": "Resource ID (optional)",
                    "clinic_id": "Clinic ID (optional)"
                },
                "user_message": "I can search for appointments with today's date and default settings. If you need specific dates or resources, please provide: date range (from/to dates), resource type (1=Doctor, 2=Room), and optionally specialty ID, resource ID, or clinic ID."
            },
            "get_session_slots": {
                "needs_parameters": True,
                "tool_name": tool_name,
                "required_parameters": ["resource_id", "session_date", "session_id"],
                "parameter_descriptions": {
                    "resource_id": "Doctor/Resource ID (e.g., 2 for Dr. Clement Tan)",
                    "session_date": "Session date (YYYY-MM-DD format)",
                    "session_id": "Session ID (e.g., 363 for PM session)"
                },
                "user_message": "To show available appointment slots, I need to know:\n• Which doctor? (Resource ID - e.g., 2 for Dr. Clement Tan)\n• What date? (YYYY-MM-DD format)\n• Which session? (Session ID - e.g., 363 for PM session)\n\nPlease provide these details so I can find the best available slots for you."
            },
            "create_walkin": {
                "needs_parameters": True,
                "tool_name": tool_name,
                "required_parameters": ["patient_id", "resource_id", "session_date"],
                "optional_parameters": ["session_id", "from_time"],
                "parameter_descriptions": {
                    "patient_id": "Patient ID (required)",
                    "resource_id": "Doctor/Resource ID (e.g., 2 for Dr. Clement Tan)",
                    "session_date": "Appointment date (YYYY-MM-DD format)",
                    "session_id": "Session ID (optional, defaults to 363)",
                    "from_time": "Preferred time (optional, defaults to 07:10:00)"
                },
                "user_message": "To create a walk-in appointment, I need:\n• Patient ID (who is the appointment for?)\n• Which doctor? (Resource ID - e.g., 2 for Dr. Clement Tan)\n• What date? (YYYY-MM-DD format)\n\nOptionally, you can specify session ID and preferred time. Please provide at least the required details."
            },
            "create_visit": {
                "needs_parameters": True,
                "tool_name": tool_name,
                "required_parameters": ["appointment_id"],
                "parameter_descriptions": {
                    "appointment_id": "Appointment ID to create visit from"
                },
                "user_message": "I need an appointment ID to create a visit. Please provide the appointment ID."
            },
            "get_patient_journey": {
                "needs_parameters": True,
                "tool_name": tool_name,
                "required_parameters": ["visit_id"],
                "parameter_descriptions": {
                    "visit_id": "Visit ID to get journey information for"
                },
                "user_message": "I need a visit ID to show the patient journey. Please provide the visit ID."
            },
            "get_appointment_followup": {
                "needs_parameters": True,
                "tool_name": tool_name,
                "required_parameters": ["patient_id", "date_from", "date_to"],
                "parameter_descriptions": {
                    "patient_id": "Patient ID",
                    "date_from": "Start date (YYYY-MM-DD format)",
                    "date_to": "End date (YYYY-MM-DD format)"
                },
                "user_message": "I can search for follow-up appointments with default patient ID and today's date. If you need specific details, please provide: patient ID and date range (from/to dates)."
            }
        }
        
        return requirements.get(tool_name, {
            "needs_parameters": True,
            "tool_name": tool_name,
            "user_message": f"I need additional information to complete the {tool_name.replace('_', ' ')} request. Please provide the required parameters."
        })

    @staticmethod
    def get_parameter_prompt(tool_name: str) -> str:
        """
        Get a user-friendly prompt for missing parameters.
        
        Args:
            tool_name: Name of the tool requiring parameters.
            
        Returns:
            String prompt to show to the user.
        """
        requirements = ParameterCollector.get_parameter_requirements(tool_name)
        return requirements.get("user_message", f"I need additional information to complete this {tool_name.replace('_', ' ')} request.")

    @staticmethod
    def validate_parameters(tool_name: str, parameters: Dict[str, Any]) -> bool:
        """
        Validate that required parameters are present and valid.

        Args:
            tool_name: Name of the tool.
            parameters: Parameters to validate.

        Returns:
            True if parameters are valid, False otherwise.
        """
        required_params = {
            "search_by_id_number": ["id_number"],
            "get_user_dataset": ["date_from", "date_to", "resource_type"],
            "get_session_slots": ["resource_id", "session_date", "session_id"],
            "create_walkin": ["resource_id", "session_id", "session_date", "from_time", "patient_id"],
            "create_visit": ["appointment_id"],
            "get_patient_journey": ["visit_id"],
            "get_appointment_followup": ["patient_id", "date_from", "date_to"]
        }
        
        if tool_name not in required_params:
            return True  # No validation needed
        
        for param in required_params[tool_name]:
            if param not in parameters or not parameters[param]:
                logger.warning(f"Missing required parameter: {param}")
                return False
        
        return True

    @staticmethod
    def format_date(date_str: str) -> str:
        """
        Format and validate date string.

        Args:
            date_str: Date string to format.

        Returns:
            Formatted date string or today's date if invalid.
        """
        try:
            # Try to parse the date to validate format
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}. Using today's date.")
            return datetime.now().strftime("%Y-%m-%d")
