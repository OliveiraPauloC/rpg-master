import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env') # Garante que pega do arquivo certo

chave = os.getenv("GEMINI_API_KEY")
print(f"Chave carregada: {chave[:5]}... (Verifique se é a nova!)")

genai.configure(api_key=chave)

print("\n--- MODELOS DISPONÍVEIS ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            
    print("\n--- TESTE DE CONEXÃO COM 1.5 FLASH ---")
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Diga 'Olá Mestre'")
    print(f"RESPOSTA DA IA: {response.text}")
    print(">>> SUCESSO! O modelo funciona.")
    
except Exception as e:
    print(f"\n>>> ERRO: {e}")