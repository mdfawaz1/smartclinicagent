import json
import requests
import os
import logging
import re
from typing import Dict, List, Any, Optional
from tools import Tools

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("ReActAgent")

class ReActAgent:
    """
    ReAct Agent for hospital chatbot using the Reason-Act-Observe paradigm.
    This agent interfaces with a local LLM and uses external tools like doctor specialty lookup.
    """
    
    def __init__(self, llm_endpoint: str = "http://localhost:1234/v1/chat/completions", 
                 specialty_api_endpoint: str = "http://eserver/api/his/AppointmentsAPI/InitAll",
                 specialty_api_token: Optional[str] = None,
                 debug_mode: bool = True):
        """
        Initialize the ReAct Agent.
        
        Args:
            llm_endpoint: Endpoint for the local LLM
            specialty_api_endpoint: Endpoint for the doctor specialty API
            specialty_api_token: Bearer token for API authentication
            debug_mode: Whether to show detailed debugging information
        """
        self.llm_endpoint = llm_endpoint
        self.specialty_api_endpoint = specialty_api_endpoint
        self.specialty_api_token = specialty_api_token or os.getenv("SPECIALTY_API_TOKEN")
        self.debug_mode = debug_mode
        
        # Initialize tools
        self.tools_manager = Tools(
            specialty_api_endpoint=specialty_api_endpoint,
            specialty_api_token=self.specialty_api_token,
            debug_mode=debug_mode
        )
        
        # Available tools mapping - mapping tool names to methods in Tools class
        self.tools = {
            "get_doctor_specialties": self.tools_manager.get_doctor_specialties,
            "activate_sso": self.tools_manager.activate_sso,
            "search_by_id_number": self.tools_manager.search_by_id_number,
            "get_today_appointments": self.tools_manager.get_today_appointments,
            "get_ongoing_visits": self.tools_manager.get_ongoing_visits,
            "init_appointments": self.tools_manager.init_appointments,
            "get_user_dataset": self.tools_manager.get_user_dataset,
            "get_session_slots": self.tools_manager.get_session_slots,
            "create_walkin": self.tools_manager.create_walkin,
            "get_appointment_number": self.tools_manager.get_appointment_number,
            "create_visit": self.tools_manager.create_visit,
            "get_patient_journey": self.tools_manager.get_patient_journey,
            "get_appointment_followup": self.tools_manager.get_appointment_followup
        }
        
        # Initialize conversation history
        self.conversation_history = []
        
        # Keywords related to doctor specialties for better detection
        self.specialty_keywords = [
            "doctor", "specialist", "specialty", "specialties", "speciality", 
            "specialities", "department", "medical", "physician", "practitioner",
            "cardio", "heart", "dental", "teeth", "dentist", "neuro", "brain", 
            "ortho", "bone", "pediatric", "children", "emergency", "surgery"
        ]
        
        # Keywords related to appointments for better detection
        self.appointment_keywords = [
            "appointment", "book", "schedule", "slot", "reserve", "visit", 
            "consultation", "meet", "session", "timing", "available", 
            "follow-up", "followup", "checkup", "walkin", "walk-in"
        ]
        
        logger.info("ReAct Agent initialized with debug_mode=%s", debug_mode)
        
    def _reason(self, user_query: str) -> Dict[str, Any]:
        """
        Reason about the next step based on the user query and conversation history.
        This method prompts the LLM to decide what to do next.
        
        Args:
            user_query: The user's input query
            
        Returns:
            Dict containing the reasoning and next action
        """
        logger.info("\n=== REASONING ===")
        
        # First check if this is a general greeting or simple question
        if self._is_greeting(user_query):
            logger.info("Detected greeting or simple question, providing direct answer")
            
            return {
                "reasoning": "The user is providing a greeting or asking a simple question. I can answer directly without using a tool.",
                "use_tool": False,
                "direct_answer": self._get_greeting_response(user_query)
            }
        
        # Then check for appointment-related queries (higher priority)
        if self._is_appointment_query(user_query):
            logger.info("Detected appointment-related question, selecting appropriate appointment tool")
            
            # Select the appropriate tool based on the query 
            tool_action = self._select_appointment_tool(user_query)
            
            return {
                "reasoning": f"The user is asking about appointments. I should use the {tool_action['action_type']} tool.",
                "use_tool": True,
                "action": tool_action
            }
        
        # Then check for specialty-related queries
        if self._is_specialty_query(user_query):
            logger.info("Detected specialty-related question, enforcing API call for ReAct flow")
            
            # Extract potential specialty from query
            specialty_query = user_query
            
            return {
                "reasoning": "The user is asking about doctor specialties. I should use the get_doctor_specialties tool to retrieve accurate information from our API.",
                "use_tool": True,
                "action": {
                    "action_type": "get_doctor_specialties",
                    "parameters": {"query": specialty_query}
                }
            }
        
        # For queries that don't match any patterns, use the LLM
        logger.info("Query doesn't match specific patterns. Checking with LLM...")
        
        try:
            # Construct a prompt specifically designed to prevent hallucination
            prompt = self._construct_reasoning_prompt(user_query)
            
            logger.info("Calling LLM for reasoning...")
            response = self._call_llm(prompt)
            
            # Parse the LLM response to extract reasoning and action
            reasoning_output = self._parse_reasoning_response(response)
            
            logger.info(f"Reasoning: {reasoning_output.get('reasoning', 'No reasoning provided')}")
            return reasoning_output
        except Exception as e:
            logger.error(f"Error in reasoning step: {str(e)}")
            # Provide a fallback reasoning response when LLM call fails
            return {
                "reasoning": "Failed to process with LLM. Providing a general response.",
                "use_tool": False,
                "direct_answer": "I'm here to help with questions about doctor specialties and appointments at our hospital. How can I assist you today?"
            }
    
    def _is_greeting(self, query: str) -> bool:
        """
        Determine if a query is a simple greeting or general question.
        
        Args:
            query: The user query to check
            
        Returns:
            Boolean indicating if the query is a greeting
        """
        query_lower = query.lower()
        
        greeting_patterns = [
            r"^(hi|hello|hey|greetings|good morning|good afternoon|good evening)[\s\W]*$",
            r"^how are you(\?)?$",
            r"^what'?s up(\?)?$",
            r"(nice to meet you|pleased to meet you)(\.)$"
        ]
        
        for pattern in greeting_patterns:
            if re.search(pattern, query_lower):
                return True
                
        return False
    
    def _get_greeting_response(self, query: str) -> str:
        """
        Generate a response for greetings.
        
        Args:
            query: The user's greeting
            
        Returns:
            A greeting response
        """
        query_lower = query.lower()
        
        if re.search(r"how are you", query_lower):
            return "I'm doing well, thank you for asking! I'm here to help with questions about doctor specialties and appointments at our hospital. How can I assist you today?"
            
        return "Hello! I'm the SmartClinic assistant. I can help you with information about doctor specialties and appointments at our hospital. How can I assist you today?"
    
    def _is_specialty_query(self, query: str) -> bool:
        """
        Determine if a query is related to doctor specialties.
        
        Args:
            query: The user query to check
            
        Returns:
            Boolean indicating if the query is about specialties
        """
        query_lower = query.lower()
        
        # Avoid false positives by checking for appointment terms first
        if any(word in query_lower for word in ["book", "schedule", "appointment", "slot", "visit", "time"]):
            return False
        
        # Check for follow-up queries about listing specialties
        full_list_patterns = [
            r"(yes|yeah|sure|ok|okay|full|complete|all).+(list|specialties|speciality|specialists)",
            r"(show|see|give).+(all|full|complete|more).+(list|specialties)",
            r"(list|show).+(all|everything|every|more)",
            r"what.+(all|else|other).+(available|have)"
        ]
        
        for pattern in full_list_patterns:
            if re.search(pattern, query_lower):
                return True
        
        # Check for specialty keywords but make sure they're not just part of a general question
        specialty_keyword_match = False
        for keyword in self.specialty_keywords:
            if keyword in query_lower:
                specialty_keyword_match = True
                break
                
        if specialty_keyword_match:
            # Check if it's a question about specialties, not just containing the word
            specialty_patterns = [
                r"(do|does|are|can|have).+(doctor|specialist|physician)",
                r"(what|which).+(specialist|specialty|department)",
                r"looking for.+(doctor|specialist)",
                r"(find|need).+(doctor|specialist)",
                r"(tell|inform).+(about|your).+(specialist|specialty|department)",
                r"(what|which|any|is).+(doctor|specialist|department).+(available|have|for|treat)"
            ]
            
            for pattern in specialty_patterns:
                if re.search(pattern, query_lower):
                    return True
                    
            # If it's not an explicit question about specialties, be more conservative
            if not any(word in query_lower for word in ["what", "which", "where", "how", "when", "do", "does", "are", "can", "have", "tell", "inform"]):
                return False
                
        return specialty_keyword_match
    
    def _is_appointment_query(self, query: str) -> bool:
        """
        Determine if a query is related to appointments.
        
        Args:
            query: The user query to check
            
        Returns:
            Boolean indicating if the query is about appointments
        """
        query_lower = query.lower()
        
        # Direct appointment keywords that strongly indicate appointment intent
        strong_appointment_indicators = [
            "book appointment", "schedule appointment", "make appointment", 
            "get appointment", "create appointment", "new appointment",
            "appointment booking", "appointment schedule", "appointment availability",
            "book a visit", "schedule a visit", "book a slot"
        ]
        
        for indicator in strong_appointment_indicators:
            if indicator in query_lower:
                return True
        
        # Check for appointment-related question patterns
        appointment_patterns = [
            r"(book|schedule|make|get|create).+(appointment|visit|consultation)",
            r"(available|free|open).+(slot|time|appointment)",
            r"(when|how).+(see|meet|visit).+(doctor|specialist)",
            r"(my|check).+(appointment|booking|reservation)",
            r"walk.?in",
            r"follow.?up",
            r"(today|tomorrow).+(appointment|visit)",
            r"(appointment|booking).+(system|process|available)"
        ]
        
        for pattern in appointment_patterns:
            if re.search(pattern, query_lower):
                return True
                
        # More general queries that mention both appointment-related terms
        if any(word in query_lower for word in ["appointment", "booking", "schedule", "slot"]):
            if any(word in query_lower for word in ["doctor", "hospital", "clinic", "medical", "visit"]):
                return True
                
        return False
    
    def _select_appointment_tool(self, query: str) -> Dict[str, Any]:
        """
        Select the appropriate appointment tool based on the query.
        
        Args:
            query: The user query
            
        Returns:
            Dictionary containing the action type and parameters
        """
        query_lower = query.lower()
        
        # Check for specific appointment actions
        if any(term in query_lower for term in ["today", "current", "ongoing", "active"]):
            if "appointment" in query_lower:
                return {
                    "action_type": "get_today_appointments",
                    "parameters": {}
                }
            elif "visit" in query_lower:
                return {
                    "action_type": "get_ongoing_visits",
                    "parameters": {}
                }
        
        # Check for booking-related queries
        if any(term in query_lower for term in ["book", "schedule", "make", "create", "get", "new"]):
            if any(term in query_lower for term in ["walk in", "walk-in", "walkin"]):
                return {
                    "action_type": "create_walkin",
                    "parameters": {
                        "resource_id": "2",
                        "session_id": "363",
                        "session_date": "2025-06-25",
                        "from_time": "07%3A10%3A00",
                        "patient_id": "3598"
                    }
                }
            else:
                # For general booking, we need to get slots first
                return {
                    "action_type": "get_session_slots",
                    "parameters": {
                        "resource_id": "2",
                        "session_date": "2025-06-25",
                        "session_id": "363"
                    }
                }
                
        if any(term in query_lower for term in ["follow up", "follow-up", "followup"]):
            return {
                "action_type": "get_appointment_followup",
                "parameters": {
                    "patient_id": "3598",
                    "date_from": "2025-06-25",
                    "date_to": "2025-06-25"
                }
            }
            
        if any(term in query_lower for term in ["journey", "status", "progress"]):
            return {
                "action_type": "get_patient_journey",
                "parameters": {
                    "visit_id": "3502"
                }
            }
            
        if any(term in query_lower for term in ["available", "slot", "time"]):
            return {
                "action_type": "get_session_slots",
                "parameters": {
                    "resource_id": "2",
                    "session_date": "2025-06-25",
                    "session_id": "363"
                }
            }
            
        # Default to initialization if no specific query is matched
        return {
            "action_type": "init_appointments",
            "parameters": {}
        }
    
    def _act(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the action determined by the reasoning step.
        
        Args:
            action: Dictionary containing action type and parameters
            
        Returns:
            Result of the action
        """
        logger.info("\n=== ACTION ===")
        logger.info(f"Executing action: {action['action_type']}")
        logger.info(f"Parameters: {json.dumps(action.get('parameters', {}), indent=2)}")
        
        # Check if the action type is valid
        if action["action_type"] not in self.tools:
            logger.error(f"Unknown action type: {action['action_type']}")
            return {
                "success": False,
                "error": f"Unknown action type: {action['action_type']}",
                "result": None
            }
        
        # Execute the corresponding tool function
        try:
            logger.info("Calling API...")
            
            # Handle parameter collection for tools that need it
            parameters = action.get("parameters", {})
            tool_name = action["action_type"]
            
            # Call the tool with the parameters
            result = self.tools[action["action_type"]](parameters)
            
            # Check if the result indicates missing parameters
            if isinstance(result, dict) and result.get("needs_parameters", False):
                return {
                    "success": False,
                    "needs_parameters": True,
                    "parameter_prompt": result.get("user_message", "Additional information required"),
                    "tool_name": tool_name,
                    "parameter_requirements": result,
                    "result": None
                }
            
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            logger.error(f"Error executing action: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "result": None
            }
    
    def _observe(self, action_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the output of the executed action.
        
        Args:
            action_result: Result from the action step
            
        Returns:
            Processed observation
        """
        logger.info("\n=== OBSERVATION ===")
        
        if action_result["success"]:
            observation = action_result["result"]
            logger.info(f"Observation: {json.dumps(observation, indent=2)}")
        else:
            observation = f"Error: {action_result['error']}"
            logger.info(f"Observation: {observation}")
        
        return {"observation": observation}
    
    def chat(self, user_query: str) -> str:
        """
        Main entry point for chat interaction.
        Implements the full ReAct loop: Reason -> Act -> Observe -> Final answer
        
        Args:
            user_query: User's input query
            
        Returns:
            Agent's response to the user (always a string)
        """
        logger.info(f"\n\nUser Query: {user_query}")
        
        # Add user query to conversation history
        self.conversation_history.append({"role": "user", "content": user_query})
        
        try:
            # REASON: Determine what to do based on the user query
            reasoning_output = self._reason(user_query)
            
            # HANDLE TOOL-USING QUERIES
            if reasoning_output.get("use_tool", False):
                # ACT: Execute the action
                action_result = self._act(reasoning_output["action"])
                
                # Check if the action needs parameters
                if not action_result["success"] and action_result.get("needs_parameters", False):
                    logger.info("\n=== PARAMETER REQUIREMENTS ===")
                    logger.info("Tool requires parameters from user")
                    final_answer = action_result.get("parameter_prompt", "I need additional information to complete this request.")
                    
                    # Add agent response to conversation history
                    self.conversation_history.append({"role": "assistant", "content": final_answer})
                    return final_answer
                
                # OBSERVE: Process the result of the action
                observation = self._observe(action_result)
                
                # FINAL REASONING: Generate final answer based on the observation
                final_prompt = self._construct_final_answer_prompt(
                    user_query, 
                    reasoning_output, 
                    action_result, 
                    observation
                )
                
                logger.info("\n=== FINAL REASONING ===")
                logger.info("Generating final answer based on observation...")
                
                try:
                    final_response = self._call_llm(final_prompt)
                    final_answer = self._extract_final_answer(final_response)
                except Exception as e:
                    logger.error(f"Error in final reasoning: {str(e)}")
                    # Fallback if LLM fails during final reasoning
                    if action_result["success"]:
                        tool_type = reasoning_output["action"]["action_type"]
                        
                        if tool_type == "get_doctor_specialties" and "specialties" in action_result["result"]:
                            specialties = action_result["result"]["specialties"]
                            if specialties:
                                specialty_names = [s.get("DESCRIPTION", "Unknown") for s in specialties[:5]]
                                final_answer = f"I found these specialties: {', '.join(specialty_names)}"
                                if len(specialties) > 5:
                                    final_answer += f" and {len(specialties) - 5} more."
                            else:
                                final_answer = "I couldn't find any matching specialties for your query."
                        # Handle appointment-related tools
                        elif "create_walkin" in tool_type:
                            final_answer = "I've scheduled a walk-in appointment for you. Your appointment has been confirmed."
                        elif "get_today_appointments" in tool_type:
                            final_answer = "I've retrieved today's appointments. You can view the details in the system."
                        elif "get_ongoing_visits" in tool_type:
                            final_answer = "I've checked the ongoing visits in the hospital. The information has been retrieved."
                        elif "get_session_slots" in tool_type:
                            final_answer = "I've found available appointment slots. You can select one for your appointment."
                        elif "get_appointment_followup" in tool_type:
                            final_answer = "I've checked your follow-up appointments. The information is now available."
                        elif "get_patient_journey" in tool_type:
                            final_answer = "I've retrieved your patient journey information. You can see your progress."
                        elif "create_visit" in tool_type:
                            final_answer = "I've created a visit record for your appointment. You're all set."
                        elif "search_by_id_number" in tool_type:
                            final_answer = "I've found your patient record using your ID number. Your information has been retrieved."
                        elif "activate_sso" in tool_type:
                            final_answer = "I've activated your SSO account. You can now log in with your credentials."
                        else:
                            # Generic response for other tools
                            final_answer = f"I processed your request about {tool_type.replace('_', ' ')}. The operation was successful."
                    else:
                        final_answer = "I'm sorry, I encountered an error while processing your request."
            
            # HANDLE DIRECT ANSWER QUERIES
            elif "direct_answer" in reasoning_output and reasoning_output["direct_answer"]:
                logger.info("\n=== DIRECT ANSWER ===")
                final_answer = reasoning_output["direct_answer"]
                logger.info(final_answer)
            
            # HANDLE OUT-OF-SCOPE QUERIES
            elif reasoning_output.get("out_of_scope", False):
                logger.info("\n=== OUT OF SCOPE ===")
                final_answer = "I'm currently focused on providing information about doctor specialties and appointments at our hospital. I don't have information about other topics yet. How can I help you with our medical specialists or scheduling appointments?"
                logger.info(final_answer)
            
            # FALLBACK FOR ANY OTHER CASE
            else:
                logger.info("\n=== FALLBACK RESPONSE ===")
                final_answer = "I'm here to help with questions about doctor specialties and appointments at our hospital. How can I assist you today?"
                logger.info(final_answer)
            
            # Add agent response to conversation history
            self.conversation_history.append({"role": "assistant", "content": final_answer})
            
            return final_answer
            
        except Exception as e:
            # Global error handling to ensure we always return a string
            logger.error(f"Unexpected error in chat flow: {str(e)}")
            error_message = "I'm sorry, I encountered an unexpected error. Please try asking about our doctor specialties or appointments again."
            self.conversation_history.append({"role": "assistant", "content": error_message})
            return error_message
    
    def _construct_reasoning_prompt(self, user_query: str) -> List[Dict[str, str]]:
        """
        Constructs the prompt for the reasoning step.
        
        Args:
            user_query: User's input query
            
        Returns:
            Formatted prompt for the LLM
        """
        system_message = """
        You are an intelligent hospital assistant that helps users with their queries about doctor specialties and appointments only.
        
        Your task is to analyze the user's query and decide whether to use a tool or answer directly.
        
        Currently, you have access to the following tools:
        
        SPECIALTY TOOLS:
        1. get_doctor_specialties: Retrieves information about doctor specialties
        
        APPOINTMENT TOOLS:
        2. activate_sso: Activates Single Sign-On for a user
        3. search_by_id_number: Searches for a patient by ID number
        4. get_today_appointments: Retrieves today's appointments
        5. get_ongoing_visits: Retrieves ongoing patient visits
        6. init_appointments: Initializes the appointments system
        7. get_user_dataset: Retrieves user dataset for appointments
        8. get_session_slots: Retrieves appointment session slots
        9. create_walkin: Creates a walk-in appointment
        10. get_appointment_number: Retrieves appointment numbers
        11. create_visit: Creates a patient visit
        12. get_patient_journey: Retrieves patient journey information
        13. get_appointment_followup: Retrieves follow-up appointment information
        
        IMPORTANT: You should ONLY answer questions about doctor specialties and appointments in the hospital. For ANY other topic:
        1. You must set "out_of_scope" to true
        2. You should NOT provide an answer, as you don't have verified information on other topics
        3. Your response should direct the user back to asking about doctor specialties or appointments
        
        EXAMPLES OF SPECIALTY QUERIES:
        - "What specialties do you have?"
        - "Do you have cardiologists?"
        - "Tell me about your orthopedic department"
        
        EXAMPLES OF APPOINTMENT QUERIES:
        - "I want to book an appointment"
        - "Show me today's appointments"
        - "What appointment slots are available?"
        - "How do I schedule a follow-up?"
        
        EXAMPLES OF OUT-OF-SCOPE QUERIES:
        - "What medications should I take for headaches?"
        - "How much does surgery cost?"
        - "What's the weather today?"
        
        For each query, you should:
        1. Think about what the user is asking for
        2. Decide if it's about doctor specialties or appointments (if not, mark it out of scope)
        3. Format your response as JSON with the following structure:
        
        If you need to use a tool:
        {
            "reasoning": "your step-by-step reasoning",
            "use_tool": true,
            "action": {
                "action_type": "[one of the tool names]",
                "parameters": {"param1": "value1", "param2": "value2"}
            }
        }
        
        If you can answer directly (ONLY for basic specialty/appointment information or greetings):
        {
            "reasoning": "your step-by-step reasoning",
            "use_tool": false,
            "direct_answer": "your answer to the user's query about doctor specialties or appointments"
        }
        
        If the query is NOT about doctor specialties or appointments:
        {
            "reasoning": "your step-by-step reasoning",
            "use_tool": false,
            "out_of_scope": true,
            "direct_answer": null
        }
        """
        
        messages = [
            {"role": "system", "content": system_message},
        ]
        
        # Add conversation history (limited to last few exchanges for context)
        for message in self.conversation_history[-4:]:
            messages.append(message)
            
        # Add the current query
        messages.append({"role": "user", "content": f"User query: {user_query}\n\nRespond with the JSON format described in the instructions."})
        
        return messages
    
    def _construct_final_answer_prompt(self, user_query: str, reasoning: Dict[str, Any], 
                                      action_result: Dict[str, Any], observation: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Constructs the prompt for generating the final answer.
        
        Args:
            user_query: Original user query
            reasoning: Output from the reasoning step
            action_result: Result from the action step
            observation: Processed observation
            
        Returns:
            Formatted prompt for the LLM
        """
        system_message = """
        You are an intelligent hospital assistant that helps users with their queries about doctor specialties and appointments.
        
        Based on the user's query, the reasoning, and the observation from using a tool,
        formulate a helpful, concise, and informative response.
        
        IMPORTANT RULES:
        1. Only respond with information that is directly supported by the observation
        2. If the observation doesn't provide enough information to answer, say so clearly
        3. Never make up or hallucinate information about specialists, departments, or appointments
        4. If relevant information is found, present it in a clear, helpful way
        5. If no relevant information is found, politely inform the user
        
        Provide only the final answer without mentioning the reasoning process or the fact that you used a tool.
        """
        
        prompt_content = f"""
        User query: {user_query}
        
        Reasoning: {reasoning.get('reasoning', 'No reasoning provided')}
        
        Tool used: {reasoning.get('action', {}).get('action_type', 'No tool used')}
        Tool parameters: {json.dumps(reasoning.get('action', {}).get('parameters', {}), indent=2)}
        
        Observation: {json.dumps(observation.get('observation', 'No observation available'), indent=2)}
        
        Based on this information, provide a helpful answer to the user's original query.
        Remember to ONLY use information from the observation and do not make up or hallucinate any details.
        """
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt_content}
        ]
        
        return messages
    
    def _call_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Call the local LLM with the given prompt.
        
        Args:
            messages: List of message dictionaries for the LLM
            
        Returns:
            LLM response
        """
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "local-model", # This can be adjusted based on the LLM's requirements
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 800
        }
        
        try:
            response = requests.post(
                self.llm_endpoint,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            raise Exception(f"LLM call failed: {str(e)}")
    
    def _parse_reasoning_response(self, llm_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the LLM's response to extract reasoning and action information.
        
        Args:
            llm_response: Raw response from the LLM
            
        Returns:
            Parsed reasoning output
        """
        try:
            # Extract the content from the LLM response
            content = llm_response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            
            # Find JSON in the content (in case the LLM added extra text)
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            # Parse the JSON response
            parsed_response = json.loads(content)
            
            # Ensure required fields are present
            if "reasoning" not in parsed_response:
                parsed_response["reasoning"] = "No explicit reasoning provided by LLM"
                
            return parsed_response
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return {
                "reasoning": "Failed to parse LLM response",
                "use_tool": False,
                "out_of_scope": True,
                "direct_answer": "I'm having trouble processing your question. Could you please ask specifically about doctor specialties or appointments available at our hospital?"
            }
    
    def _extract_final_answer(self, llm_response: Dict[str, Any]) -> str:
        """
        Extract the final answer from the LLM's response.
        
        Args:
            llm_response: Raw response from the LLM
            
        Returns:
            Extracted final answer as a string
        """
        try:
            return llm_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"Error extracting final answer: {str(e)}")
            return "I'm sorry, I encountered an error while processing your request."
    
    def _tool_requires_parameters(self, tool_name: str) -> bool:
        """
        Check if a tool requires user input parameters.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if the tool requires parameters, False otherwise
        """
        tools_requiring_parameters = {
            "search_by_id_number", "get_user_dataset", "get_session_slots", 
            "create_walkin", "create_visit", "get_patient_journey", 
            "get_appointment_followup"
        }
        return tool_name in tools_requiring_parameters
    
    def _has_required_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> bool:
        """
        Check if all required parameters are present for a tool.
        
        Args:
            tool_name: Name of the tool
            parameters: Parameters provided
            
        Returns:
            True if all required parameters are present, False otherwise
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
            return True  # No parameters required
        
        for param in required_params[tool_name]:
            if param not in parameters or not parameters[param]:
                return False
        
        return True
