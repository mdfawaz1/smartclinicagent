import json
import requests
import os
import logging
from typing import Dict, Any, Optional

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
    
    def get_doctor_specialties(self, parameters: Dict[str, str]) -> Dict[str, Any]:
        """
        Get doctor specialties from the API.
        
        Args:
            parameters: Parameters for the API call (e.g., {"query": "cardio"})
            
        Returns:
            Doctor specialty information
        """
        # Check if we have the API token
        if not self.specialty_api_token:
            logger.error("Specialty API token not provided")
            raise ValueError("Specialty API token not provided")
        
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
    
    def activate_sso(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
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
    
    def search_by_id_number(self, parameters: Dict[str, str]) -> Dict[str, Any]:
        """
        Search for a patient by ID number.
        
        Args:
            parameters: Parameters for the search (e.g., {"id_number": "DD15021998"})
            
        Returns:
            Search results
        """
        try:
            id_number = parameters.get("id_number", "DD15021998")  # Default to example ID if not provided
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
    
    def get_user_dataset(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get user dataset for appointments.
        
        Args:
            parameters: Parameters for the dataset query
                - date_from: Start date (default: 2025-06-25)
                - date_to: End date (default: 2025-06-25)
                - resource_type: Resource type (default: 1)
                - specialty_id: Specialty ID (optional)
                - resource_id: Resource ID (optional)
                - clinic_id: Clinic ID (optional)
                - from_time: From time (optional)
                - to_time: To time (optional)
            
        Returns:
            User dataset
        """
        try:
            # Extract parameters with defaults
            date_from = parameters.get("date_from", "2025-06-25")
            date_to = parameters.get("date_to", "2025-06-25")
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
    
    def get_session_slots(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get appointment session slots.
        
        Args:
            parameters: Parameters for the slots query
                - resource_id: Resource ID (default: 2)
                - session_date: Session date (default: 2025-06-25)
                - session_id: Session ID (default: 363)
            
        Returns:
            Session slots
        """
        try:
            resource_id = parameters.get("resource_id", "2")
            session_date = parameters.get("session_date", "2025-06-25")
            session_id = parameters.get("session_id", "363")
            
            url = f"http://eserver/api/his/AppointmentsAPI/GetSessionSlots?Id={resource_id}&SessionDate={session_date}T00%3A00%3A00.000Z&SessionId={session_id}"
            res = requests.get(url, headers=self.headers)
            return res.json()
        except Exception as e:
            logger.error(f"Error getting session slots: {str(e)}")
            return {"error": str(e)}
    
    def create_walkin(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a walk-in appointment.
        
        Args:
            parameters: Parameters for creating the walk-in
                - resource_id: Resource ID (default: 2)
                - session_id: Session ID (default: 363)
                - session_date: Session date (default: 2025-06-25)
                - from_time: From time (default: 07:10:00)
                - patient_id: Patient ID (default: 3598)
            
        Returns:
            Walk-in creation result
        """
        try:
            resource_id = parameters.get("resource_id", "2")
            session_id = parameters.get("session_id", "363")
            session_date = parameters.get("session_date", "2025-06-25")
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
            Appointment number information
        """
        try:
            url = "http://eserver/api/clinicaldocs/VisitDocs/GetRecordset?VisitId=1820&QueryName=GET_APPTNO"
            res = requests.get(url, headers=self.headers)
            return res.json()
        except Exception as e:
            logger.error(f"Error getting appointment number: {str(e)}")
            return {"error": str(e)}
    
    def create_visit(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a visit from an appointment.
        
        Args:
            parameters: Parameters for creating the visit
                - appointment_id: Appointment ID (default: 1820)
            
        Returns:
            Visit creation result
        """
        try:
            appointment_id = parameters.get("appointment_id", "1820")
            url = f"http://eserver/api/his/AppointmentsAPI/CreateVisit?AppointmentId={appointment_id}"
            res = requests.get(url, headers=self.headers)
            return res.json()
        except Exception as e:
            logger.error(f"Error creating visit: {str(e)}")
            return {"error": str(e)}
    
    def get_patient_journey(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get patient journey information.
        
        Args:
            parameters: Parameters for the patient journey query
                - visit_id: Visit ID (default: 3502)
            
        Returns:
            Patient journey information
        """
        try:
            visit_id = parameters.get("visit_id", "3502")
            url = f"http://eserver/api/clinicaldocs/VisitDocs/GetRecordset?VisitId={visit_id}&QueryName=GET_PATIENT_JOURNEY"
            res = requests.get(url, headers=self.headers)
            return res.json()
        except Exception as e:
            logger.error(f"Error getting patient journey: {str(e)}")
            return {"error": str(e)}
    
    def get_appointment_followup(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get appointment follow-up information.
        
        Args:
            parameters: Parameters for the follow-up query
                - patient_id: Patient ID (default: 3598)
                - date_from: Start date (default: 2025-06-25)
                - date_to: End date (default: 2025-06-25)
                - from_time: From time (optional)
                - to_time: To time (optional)
            
        Returns:
            Appointment follow-up information
        """
        try:
            patient_id = parameters.get("patient_id", "3598")
            date_from = parameters.get("date_from", "2025-06-25")
            date_to = parameters.get("date_to", "2025-06-25")
            
            body = {
                "PATIENTID": patient_id,
                "FROMDATE": date_from,
                "TODATE": date_to,
                "FROM_TIME": parameters.get("from_time"),
                "TO_TIME": parameters.get("to_time")
            }
            
            url = "http://eserver/api/his/AppointmentsAPI/GetUserDataset?QueryName=APPOINTMENTFOLLOWUP"
            headers = {**self.headers, "content-type": "application/json"}
            
            res = requests.post(url, headers=headers, json=body)
            return res.json()
        except Exception as e:
            logger.error(f"Error getting appointment follow-up: {str(e)}")
            return {"error": str(e)} 