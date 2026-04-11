import inspect
import pydantic_ai
import pydantic_ai.providers.ollama as prov
import pydantic_ai.models as models

print("pydantic_ai version:", pydantic_ai.__version__)

print("\nOllamaProvider signature:")
print(inspect.signature(prov.OllamaProvider))

print("\nAvailable provider attributes:")
print(dir(prov.OllamaProvider))

print("\nAvailable models:")
print(dir(models))