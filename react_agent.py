import json
import requests
import os
import logging
import re
from typing import Dict, List, Any, Optional

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
        
        # Available tools
        self.tools = {
            "get_doctor_specialties": self._get_doctor_specialties
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
        
        # Force tool use for specialty-related queries
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
        
        # For non-specialty queries, use the LLM for reasoning but limit scope
        logger.info("Query is not directly about doctor specialties. Checking with LLM...")
        
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
                "reasoning": "Failed to process with LLM. Treating as out-of-scope query.",
                "use_tool": False,
                "out_of_scope": True,
                "direct_answer": None
            }
    
    def _is_specialty_query(self, query: str) -> bool:
        """
        Determine if a query is related to doctor specialties.
        
        Args:
            query: The user query to check
            
        Returns:
            Boolean indicating if the query is about specialties
        """
        query_lower = query.lower()
        
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
        
        # Check for specialty keywords
        if any(keyword in query_lower for keyword in self.specialty_keywords):
            return True
            
        # Check for specialty-related question patterns
        specialty_patterns = [
            r"(do|does|are|can|have).+(doctor|specialist|physician)",
            r"(what|which).+(specialist|specialty|department)",
            r"looking for.+(doctor|specialist)",
            r"(find|need).+(doctor|specialist)"
        ]
        
        for pattern in specialty_patterns:
            if re.search(pattern, query_lower):
                return True
                
        return False
    
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
            result = self.tools[action["action_type"]](action.get("parameters", {}))
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
            
            # HANDLE SPECIALTY QUERIES WITH TOOLS
            if reasoning_output.get("use_tool", False):
                # ACT: Execute the action
                action_result = self._act(reasoning_output["action"])
                
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
                    if action_result["success"] and "specialties" in action_result["result"]:
                        specialties = action_result["result"]["specialties"]
                        if specialties:
                            specialty_names = [s.get("DESCRIPTION", "Unknown") for s in specialties[:5]]
                            final_answer = f"I found these specialties: {', '.join(specialty_names)}"
                            if len(specialties) > 5:
                                final_answer += f" and {len(specialties) - 5} more."
                        else:
                            final_answer = "I couldn't find any matching specialties for your query."
                    else:
                        final_answer = "I'm sorry, I encountered an error while processing your request about doctor specialties."
            
            # HANDLE NON-SPECIALTY QUERIES WITH LIMITED SCOPE
            else:
                # For questions not about specialties, only answer if within scope
                logger.info("\n=== DIRECT ANSWER (NO TOOL USED) ===")
                
                # Get the direct answer from the reasoning step
                direct_answer = reasoning_output.get("direct_answer", None)
                
                # If no direct answer or unauthorized topic, provide scope limitation response
                if not direct_answer or reasoning_output.get("out_of_scope", False):
                    final_answer = "I'm currently focused on providing information about doctor specialties at our hospital. I don't have information about other topics yet. Is there something specific about our medical specialists I can help you with?"
                else:
                    final_answer = direct_answer
            
            logger.info("\n=== FINAL ANSWER ===")
            logger.info(final_answer)
            
            # Add agent response to conversation history
            self.conversation_history.append({"role": "assistant", "content": final_answer})
            
            return final_answer
            
        except Exception as e:
            # Global error handling to ensure we always return a string
            logger.error(f"Unexpected error in chat flow: {str(e)}")
            error_message = "I'm sorry, I encountered an unexpected error. Please try asking about our doctor specialties again."
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
        You are an intelligent hospital assistant that helps users with their queries about doctor specialties only.
        
        Your task is to analyze the user's query and decide whether to use a tool or answer directly.
        
        Currently, you have access to the following tools:
        
        1. get_doctor_specialties: Retrieves information about doctor specialties
        
        IMPORTANT: You should ONLY answer questions about doctor specialties in the hospital. For ANY other topic:
        1. You must set "out_of_scope" to true
        2. You should NOT provide an answer, as you don't have verified information on other topics
        3. Your response should direct the user back to asking about doctor specialties
        
        For each query, you should:
        1. Think about what the user is asking for
        2. Decide if it's about doctor specialties (if not, mark it out of scope)
        3. Format your response as JSON with the following structure:
        
        If you need to use a tool:
        {
            "reasoning": "your step-by-step reasoning",
            "use_tool": true,
            "action": {
                "action_type": "get_doctor_specialties",
                "parameters": {"query": "relevant search term"}
            }
        }
        
        If you can answer directly (ONLY for basic doctor specialty information):
        {
            "reasoning": "your step-by-step reasoning",
            "use_tool": false,
            "direct_answer": "your answer to the user's query about doctor specialties"
        }
        
        If the query is NOT about doctor specialties:
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
        for message in self.conversation_history[-6:]:
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
        You are an intelligent hospital assistant that helps users with their queries about doctor specialties.
        
        Based on the user's query, the reasoning, and the observation from using a tool,
        formulate a helpful, concise, and informative response about doctor specialties.
        
        IMPORTANT RULES:
        1. Only respond with information that is directly supported by the observation
        2. If the observation doesn't provide enough information to answer, say so clearly
        3. Never make up or hallucinate information about specialists or departments
        4. If specialty information is found, present it in a clear, helpful way
        5. If no relevant specialty is found, politely inform the user
        
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
                "direct_answer": "I'm having trouble processing your question. Could you please ask specifically about doctor specialties available at our hospital?"
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
            return "I'm sorry, I encountered an error while processing your request about doctor specialties."
    
    def _get_doctor_specialties(self, parameters: Dict[str, str]) -> Dict[str, Any]:
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
        
        headers = {
            "Authorization": f"Bearer {self.specialty_api_token}"
        }
        
        try:
            logger.info(f"Making API request to {self.specialty_api_endpoint}")
            response = requests.get(
                self.specialty_api_endpoint, 
                headers=headers
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