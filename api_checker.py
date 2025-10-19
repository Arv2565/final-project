import google.generativeai as genai

genai.configure(api_key="AIzaSyD9vBmPV4itxoCLxgPfFCJ2oHMYswrffWc")

# List all available models
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(model.name)