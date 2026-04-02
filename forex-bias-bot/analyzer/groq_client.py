import time
from typing import Optional, Callable
from groq import Groq, RateLimitError
from config.settings import settings
from analyzer.tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS


class GroqClient:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        self.max_retries = 3
        self.retry_delay = 5
        self.tools = TOOL_DEFINITIONS
        self.tool_functions = TOOL_FUNCTIONS

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=200,
                )
                return response.choices[0].message.content
            except RateLimitError:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise
            except Exception as e:
                raise RuntimeError(f"Groq API error: {e}")

    def generate_with_tools(self, user_message: str, system_prompt: str, max_iterations: int = 10) -> dict:
        """Generate response with tool calling support. Returns final signal dict."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        for iteration in range(max_iterations):
            for attempt in range(self.max_retries):
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=self.tools,
                        temperature=0.3,
                        max_tokens=500,
                    )
                    break
                except RateLimitError:
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (attempt + 1))
                    else:
                        raise
                except Exception as e:
                    raise RuntimeError(f"Groq API error: {e}")

            choice = response.choices[0]
            message = choice.message

            # Check if LLM wants to call a tool
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = eval(tool_call.function.arguments)  # Parse JSON arguments

                    print(f"[Tool Call {iteration + 1}] {tool_name}({tool_args})")

                    # If this is send_signal, capture and return the result directly
                    if tool_name == "send_signal":
                        result = {
                            "signal": tool_args.get("signal", "NEUTRAL"),
                            "confidence": tool_args.get("confidence", 50),
                            "reasoning": tool_args.get("reasoning", ""),
                        }
                        # Still execute to log/send to Discord
                        self.tool_functions[tool_name](**tool_args)
                        return result

                    elif tool_name in self.tool_functions:
                        tool_result = self.tool_functions[tool_name](**tool_args)

                        # Add tool call to conversation
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tool_call.id,
                                "type": "function",
                                "function": tool_call.function
                            }]
                        })

                        # Add tool result as a tool message
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(tool_result)
                        })
                    else:
                        print(f"Unknown tool: {tool_name}")

                    continue  # Continue to next iteration to process response

            # No tool calls - return final response
            content = message.content
            if content:
                return self.parse_signal(content)

        # Max iterations reached
        return {"signal": "NEUTRAL", "confidence": 50, "reasoning": "Max iterations reached"}

    def parse_signal(self, response: str) -> dict:
        result = {"signal": "NEUTRAL", "confidence": 50, "reasoning": ""}

        response_upper = response.upper()

        if "BUY" in response_upper and "SELL" not in response_upper:
            result["signal"] = "BUY"
        elif "SELL" in response_upper and "BUY" not in response_upper:
            result["signal"] = "SELL"
        else:
            result["signal"] = "NEUTRAL"

        for word in response_upper.split():
            if word.isdigit() and 0 <= int(word) <= 100:
                result["confidence"] = int(word)
                break
            if "%" in word:
                try:
                    num = int(word.replace("%", "").replace(",", ""))
                    if 0 <= num <= 100:
                        result["confidence"] = num
                        break
                except ValueError:
                    pass

        if "REASONING:" in response_upper:
            reasoning_part = response.split("REASONING:", 1)[1].split("\n")[0].strip()
            result["reasoning"] = reasoning_part
        elif "|" in response:
            parts = response.split("|")
            for part in parts:
                if "REASON" in part.upper():
                    result["reasoning"] = part.split(":", 1)[1].strip() if ":" in part else part.strip()

        return result


groq_client = GroqClient()
