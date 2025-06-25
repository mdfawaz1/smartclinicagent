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
               If None, prompt user for inputs.

        Returns:
            Doctor specialty information.
        """
        if parameters is None:
            parameters = self._collect_specialty_parameters()

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

    def _collect_specialty_parameters(self) -> Dict[str, str]:
        """
        Collect parameters for specialty API call from user if not provided.

        Returns:
            A dictionary of parameters.
        """
        # Use the parameter collection helper
        return ParameterCollector.collect_specialty_parameters()
    
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
                       If None, prompt user for inputs.
            
        Returns:
            Search results
        """
        if parameters is None:
            parameters = ParameterCollector.collect_appointment_parameters("search_by_id_number")
        
        if not ParameterCollector.validate_parameters("search_by_id_number", parameters):
            return {"error": "Missing required parameters"}
            
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
            parameters: Parameters for the dataset query. If None, prompt user for inputs.
                - date_from: Start date (default: today)
                - date_to: End date (default: today)
                - resource_type: Resource type (default: 1)
                - specialty_id: Specialty ID (optional)
                - resource_id: Resource ID (optional)
                - clinic_id: Clinic ID (optional)
                - from_time: From time (optional)
                - to_time: To time (optional)
            
        Returns:
            User dataset
        """
        if parameters is None:
            parameters = ParameterCollector.collect_appointment_parameters("get_user_dataset")
            
        if not ParameterCollector.validate_parameters("get_user_dataset", parameters):
            return {"error": "Missing required parameters"}
            
        try:
            # Extract parameters with defaults
            today = datetime.now().strftime("%Y-%m-%d")
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
            parameters: Parameters for the slots query. If None, prompt user for inputs.
                - resource_id: Resource ID (default: 2)
                - session_date: Session date (default: today)
                - session_id: Session ID (default: 363)
            
        Returns:
            Session slots
        """
        if parameters is None:
            parameters = ParameterCollector.collect_appointment_parameters("get_session_slots")
            
        if not ParameterCollector.validate_parameters("get_session_slots", parameters):
            return {"error": "Missing required parameters"}
            
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
            parameters: Parameters for creating the walk-in. If None, prompt user for inputs.
                - resource_id: Resource ID (default: 2)
                - session_id: Session ID (default: 363)
                - session_date: Session date (default: today)
                - from_time: From time (default: 07:10:00)
                - patient_id: Patient ID (default: 3598)
            
        Returns:
            Walk-in creation result
        """
        if parameters is None:
            parameters = ParameterCollector.collect_appointment_parameters("create_walkin")
            
        if not ParameterCollector.validate_parameters("create_walkin", parameters):
            return {"error": "Missing required parameters"}
            
        try:
            today = datetime.now().strftime("%Y-%m-%d")
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
            parameters: Parameters for creating the visit. If None, prompt user for inputs.
                - appointment_id: Appointment ID to create visit from
            
        Returns:
            Visit creation result
        """
        if parameters is None:
            parameters = ParameterCollector.collect_appointment_parameters("create_visit")
            
        if not ParameterCollector.validate_parameters("create_visit", parameters):
            return {"error": "Missing required parameters"}
            
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
            parameters: Parameters for the patient journey. If None, prompt user for inputs.
                - visit_id: Visit ID to get journey for
            
        Returns:
            Patient journey information
        """
        if parameters is None:
            parameters = ParameterCollector.collect_appointment_parameters("get_patient_journey")
            
        if not ParameterCollector.validate_parameters("get_patient_journey", parameters):
            return {"error": "Missing required parameters"}
            
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
            parameters: Parameters for the follow-up query. If None, prompt user for inputs.
                - patient_id: Patient ID
                - date_from: Start date
                - date_to: End date
            
        Returns:
            Follow-up appointment information
        """
        if parameters is None:
            parameters = ParameterCollector.collect_appointment_parameters("get_appointment_followup")
            
        if not ParameterCollector.validate_parameters("get_appointment_followup", parameters):
            return {"error": "Missing required parameters"}
            
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
    Utility class for collecting required parameters from users.
    """

    @staticmethod
    def collect_specialty_parameters() -> Dict[str, str]:
        """
        Collect parameters for specialty lookup.
        For web environments, returns default parameters that will trigger a general search.

        Returns:
            Dictionary with specialty query parameters.
        """
        # In web environment, return default that will show all specialties
        return {"query": "all available specialties"}
    
    @staticmethod
    def get_parameter_prompt(tool_name: str) -> str:
        """
        Get a user-friendly prompt for missing parameters.
        
        Args:
            tool_name: Name of the tool requiring parameters.
            
        Returns:
            String prompt to show to the user.
        """
        prompts = {
            "search_by_id_number": "I need a patient ID number to search. Please provide the patient ID (e.g., 'DD15021998').",
            "get_user_dataset": "To search for appointments, I need: date range (from/to dates), resource type (1=Doctor, 2=Room), and optionally specialty ID, resource ID, or clinic ID. Please provide these details.",
            "get_session_slots": "To find available appointment slots, I need: Doctor/Resource ID, session date (YYYY-MM-DD), and session ID. Please provide these details.",
            "create_walkin": "To create a walk-in appointment, I need: Doctor/Resource ID, session ID, appointment date, preferred time, and patient ID. Please provide these details.",
            "create_visit": "To create a visit, I need an appointment ID. Please provide the appointment ID.",
            "get_patient_journey": "To view patient journey, I need a visit ID. Please provide the visit ID.",
            "get_appointment_followup": "To search for follow-up appointments, I need: patient ID and date range (from/to dates). Please provide these details."
        }
        return prompts.get(tool_name, "I need additional information to complete this request. Please provide the required parameters.")

    @staticmethod
    def collect_appointment_parameters(tool_name: str) -> Dict[str, Any]:
        """
        Collect parameters for appointment-related tools.

        Args:
            tool_name: Name of the tool requiring parameters.

        Returns:
            Dictionary with collected parameters.
        """
        print(f"\n=== {tool_name.replace('_', ' ').title()} ===")
        
        if tool_name == "search_by_id_number":
            id_number = input("Enter patient ID number (e.g., 'DD15021998'): ").strip()
            return {"id_number": id_number or "DD15021998"}
        
        elif tool_name == "get_user_dataset":
            print("Please provide the following information for appointments search:")
            date_from = input("From date (YYYY-MM-DD, press Enter for today): ").strip()
            date_to = input("To date (YYYY-MM-DD, press Enter for today): ").strip()
            resource_type = input("Resource type (1=Doctor, 2=Room, press Enter for 1): ").strip()
            specialty_id = input("Specialty ID (optional, press Enter to skip): ").strip()
            resource_id = input("Resource ID (optional, press Enter to skip): ").strip()
            clinic_id = input("Clinic ID (optional, press Enter to skip): ").strip()
            
            today = datetime.now().strftime("%Y-%m-%d")
            return {
                "date_from": date_from or today,
                "date_to": date_to or today,
                "resource_type": resource_type or "1",
                "specialty_id": specialty_id or None,
                "resource_id": resource_id or None,
                "clinic_id": clinic_id or None
            }
        
        elif tool_name == "get_session_slots":
            print("Please provide information for available appointment slots:")
            resource_id = input("Doctor/Resource ID (press Enter for default '2'): ").strip()
            session_date = input("Session date (YYYY-MM-DD, press Enter for today): ").strip()
            session_id = input("Session ID (press Enter for default '363'): ").strip()
            
            today = datetime.now().strftime("%Y-%m-%d")
            return {
                "resource_id": resource_id or "2",
                "session_date": session_date or today,
                "session_id": session_id or "363"
            }
        
        elif tool_name == "create_walkin":
            print("Please provide information for walk-in appointment:")
            resource_id = input("Doctor/Resource ID (press Enter for default '2'): ").strip()
            session_id = input("Session ID (press Enter for default '363'): ").strip()
            session_date = input("Appointment date (YYYY-MM-DD, press Enter for today): ").strip()
            from_time = input("Preferred time (HH:MM:SS, press Enter for '07:10:00'): ").strip()
            patient_id = input("Patient ID (press Enter for default '3598'): ").strip()
            
            today = datetime.now().strftime("%Y-%m-%d")
            # URL encode the time
            time_formatted = from_time or "07:10:00"
            time_encoded = time_formatted.replace(":", "%3A")
            
            return {
                "resource_id": resource_id or "2",
                "session_id": session_id or "363",
                "session_date": session_date or today,
                "from_time": time_encoded,
                "patient_id": patient_id or "3598"
            }
        
        elif tool_name == "create_visit":
            appointment_id = input("Enter appointment ID to create visit from (press Enter for default '1820'): ").strip()
            return {"appointment_id": appointment_id or "1820"}
        
        elif tool_name == "get_patient_journey":
            visit_id = input("Enter visit ID to view patient journey (press Enter for default '3502'): ").strip()
            return {"visit_id": visit_id or "3502"}
        
        elif tool_name == "get_appointment_followup":
            print("Please provide information for follow-up appointments:")
            patient_id = input("Patient ID (press Enter for default '3598'): ").strip()
            date_from = input("From date (YYYY-MM-DD, press Enter for today): ").strip()
            date_to = input("To date (YYYY-MM-DD, press Enter for today): ").strip()
            
            today = datetime.now().strftime("%Y-%m-%d")
            return {
                "patient_id": patient_id or "3598",
                "date_from": date_from or today,
                "date_to": date_to or today
            }
        
        # Default case - return empty dict
        return {}

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
