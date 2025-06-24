import json
import requests
import os
import logging
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
        
        # Construct the prompt for the LLM
        prompt = self._construct_reasoning_prompt(user_query)
        
        # Check if the query is explicitly about specialties and force tool use
        if any(keyword in user_query.lower() for keyword in ["specialty", "specialties", "speciality", "specialities", "doctors", "department"]):
            logger.info("Detected specialty-related question, enforcing API call")
            specialty_query = user_query.split("specialty")[1].strip() if "specialty" in user_query.lower() else ""
            return {
                "reasoning": "The user is asking about available specialties. I should use the get_doctor_specialties tool to retrieve this information.",
                "use_tool": True,
                "action": {
                    "action_type": "get_doctor_specialties",
                    "parameters": {"query": specialty_query}
                }
            }
        
        # Call the LLM
        logger.info("Calling LLM for reasoning...")
        response = self._call_llm(prompt)
        
        # Parse the LLM response to extract reasoning and action
        reasoning_output = self._parse_reasoning_response(response)
        
        logger.info(f"Reasoning: {reasoning_output['reasoning']}")
        return reasoning_output
    
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
            Agent's response to the user
        """
        logger.info(f"\n\nUser Query: {user_query}")
        
        # Add user query to conversation history
        self.conversation_history.append({"role": "user", "content": user_query})
        
        # REASON: Determine what to do based on the user query
        reasoning_output = self._reason(user_query)
        
        # If the LLM determines we need to use a tool
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
            final_response = self._call_llm(final_prompt)
            final_answer = self._extract_final_answer(final_response)
        else:
            # Direct answer without using tools
            logger.info("\n=== DIRECT ANSWER (NO TOOL USED) ===")
            final_answer = reasoning_output.get("direct_answer", "I don't have enough information to answer that.")
        
        logger.info("\n=== FINAL ANSWER ===")
        logger.info(final_answer)
        
        # Add agent response to conversation history
        self.conversation_history.append({"role": "assistant", "content": final_answer})
        
        return final_answer
    
    def _construct_reasoning_prompt(self, user_query: str) -> List[Dict[str, str]]:
        """
        Constructs the prompt for the reasoning step.
        
        Args:
            user_query: User's input query
            
        Returns:
            Formatted prompt for the LLM
        """
        system_message = """
        You are an intelligent hospital assistant that helps users with their queries.
        Your task is to analyze the user's query and decide whether to use a tool or answer directly.
        Currently, you have access to the following tools:
        
        1. get_doctor_specialties: Retrieves information about doctor specialties
        
        For each query, you should:
        1. Think about what the user is asking for
        2. Decide if you need to use a tool or can answer directly
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
        
        If you can answer directly:
        {
            "reasoning": "your step-by-step reasoning",
            "use_tool": false,
            "direct_answer": "your answer to the user's query"
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
        You are an intelligent hospital assistant that helps users with their queries.
        Based on the user's query, the reasoning, and the observation from using a tool,
        formulate a helpful, concise, and informative response to the user's original query.
        
        Provide only the final answer without mentioning the reasoning process or the fact that you used a tool.
        """
        
        prompt_content = f"""
        User query: {user_query}
        
        Reasoning: {reasoning.get('reasoning', 'No reasoning provided')}
        
        Tool used: {reasoning.get('action', {}).get('action_type', 'No tool used')}
        Tool parameters: {json.dumps(reasoning.get('action', {}).get('parameters', {}), indent=2)}
        
        Observation: {json.dumps(observation.get('observation', 'No observation available'), indent=2)}
        
        Based on this information, provide a helpful answer to the user's original query.
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
            print(f"Error calling LLM: {str(e)}")
            return {"error": str(e)}
    
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
            return parsed_response
        except Exception as e:
            print(f"Error parsing LLM response: {str(e)}")
            return {
                "reasoning": "Failed to parse LLM response",
                "use_tool": False,
                "direct_answer": "I'm having trouble understanding how to help with your query. Could you please rephrase your question?"
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
            print(f"Error extracting final answer: {str(e)}")
            return "I'm sorry, I encountered an error while processing your request."
    
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
            if query:
                logger.info(f"Filtering specialties by query: {query}")
                filtered_specialties = [
                    specialty for specialty in all_specialties
                    if query in specialty.get("DESCRIPTION", "").upper()
                ]
                logger.info(f"Found {len(filtered_specialties)} matching specialties")
                return {"specialties": filtered_specialties}
            else:
                return {"specialties": all_specialties}
                
        except Exception as e:
            logger.error(f"Error calling specialty API: {str(e)}")
            return {"error": str(e)} 