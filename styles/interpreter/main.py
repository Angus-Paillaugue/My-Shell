import re
import os
from typing import Dict

class StylesInterpreter:
    def __init__(self, input_dir: str, variables: Dict[str, str]) -> None:
        self._variables = variables
        self._input_dir = input_dir
        self._stylesheet = ""
        self.process_directory()

    def evaluate_expression(self, expression: str) -> str:
        """Evaluates an expression with variables, arithmetic, and units."""
        # Replace variables in the expression with their numeric values and units
        def replace_variable(match):
            key = match.group(1)
            if key not in self._variables:
                raise KeyError(f"Variable '{key}' is not defined.")
            value = self._variables[key]
            value = str(value)  # Ensure the value is treated as a string
            # Extract numeric value and unit (e.g., "12.5px" -> 12.5, "px")
            numeric_match = re.match(r"(\d+(\.\d+)?)([a-zA-Z%]*)", value)
            if numeric_match:
                numeric_value, _, unit = numeric_match.groups()
                self._current_unit = unit or "px"  # Default to "px" if no unit is present
                return numeric_value  # Return only the numeric part for arithmetic
            else:
                # If the variable is non-numeric, return it as a quoted string for eval
                return f"'{value}'"

        # Initialize the unit for this expression
        self._current_unit = ""

        # Replace variables in the expression
        expression = re.sub(r"([A-Z_][A-Z0-9_]*)", replace_variable, expression)

        # Evaluate the arithmetic expression
        try:
            result = eval(expression)  # Use eval to calculate the result
        except ZeroDivisionError:
            raise ZeroDivisionError("Attempted to divide by zero.")
        except Exception as e:
            raise ValueError(f"Invalid expression: {expression}") from e

        # Append the unit back to the result if it's numeric
        if self._current_unit:
            return f"{float(result):.2f}{self._current_unit}"  # Format result to 2 decimal places
        return str(result)  # Return the result as a string for non-numeric values

    def process_string(self, content: str) -> str:
        """Processes a string and replaces {{expressions}} with their evaluated values."""
        return re.sub(r"\{\{(.+?)\}\}", lambda match: self.evaluate_expression(match.group(1)), content)

    def set_variables(self, variables: Dict[str, str]) -> None:
        """Sets the variables for the interpreter."""
        self._variables = variables

    def process_directory(self) -> None:
        """Processes all .css files in the input directory."""
        processed_content = ""
        for root, _, files in os.walk(self._input_dir):
            for file in files:
                if file.endswith(".mcss"):
                    full_path = os.path.join(root, file)
                    with open(full_path, "r") as f:
                        content = f.read()
                    processed_content += self.process_string(content)
        self._stylesheet = processed_content

    def get_stylesheet(self) -> str:
        """Returns the processed stylesheet."""
        return self._stylesheet
