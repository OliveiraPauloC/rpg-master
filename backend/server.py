from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, InternalServerError
import os
from dotenv import load_dotenv
import time
import random

load_dotenv()

# --- CARREGA AS CHAVES ---
CHAVES = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3")
]
CHAVES = [k for k in CHAVES if k] # Remove vazias para não dar erro

generation_config = {
    "temperature": 1.0,
    "max_output_tokens": 1000, 
}

MODELOS_PARA_TENTAR = [
    'gemini-flash-latest',       
    'gemini-2.0-flash-lite',     
    'gemini-2.0-flash',          
    'gemini-pro-latest'          
]

historico_por_ip = {} 

# --- PROMPT REFINADO (CAMPANHA LONGA E RITMADA) ---
ESTRUTURA_NARRATIVA = """
DIRETRIZES DE MESTRE DE RPG (SISTEMA D20 SIMPLIFICADO):

OBJETIVO: Mestrar uma campanha de 4 ATOS (10-15 interações cada).
FOCO: Ação, risco e consequências.

REGRAS DE OURO (MECÂNICA DE JOGO):
1. PEÇA ROLAGENS: Sempre que o jogador tentar algo arriscado (lutar, mentir, escalar, perceber), PEÇA UM TESTE.
   - Ex: "Faça um teste de Força (CD 12) para abrir a porta."
   - Ex: "Role um d20 para furtividade."
2. INTERPRETE OS DADOS: Se o jogador rolar o dado (ex: "Rolei 15"), narre o sucesso ou falha baseado nisso.
3. INIMIGOS AGRESSIVOS: Não deixe o jogador passear. Coloque inimigos que atacam imediatamente se não houver furtividade.
4. LOOT: Dê itens úteis após vitórias (poções, armas melhores).

ESTRUTURA INTERNA (ATOS):
- ATO 1: Introdução rápida e PRIMEIRO COMBATE OBRIGATÓRIO até a 5ª mensagem.
- ATO 2: Exploração perigosa e testes de perícia.
- ATO 3: Combate difícil (Boss).
- ATO 4: Conclusão.

FORMATO DA RESPOSTA:
- Máximo 2 parágrafos.
- Termine perguntando a ação OU pedindo uma rolagem de dado.
"""

PROMPT_MESTRE_BASE = f"""
{ESTRUTURA_NARRATIVA}
PERSONALIDADE: Narrativo, Sombrio, Imersivo (Dark Fantasy/Sci-Fi).
TÉCNICA:
- Use **Negrito** para itens, nomes importantes e inimigos.
- Use *Itálico* para sons, cheiros e sensações.
"""

TEMAS = {
    "medieval": f"{PROMPT_MESTRE_BASE} CENÁRIO: Alta Fantasia Épica (Estilo Dungeons & Dragons e Senhor dos Anéis). Um mundo vasto de magia antiga, raças diversas (humanos, elfos, anões), reinos grandiosos e heróis lendários enfrentando o mal absoluto.",
    "cyberpunk": f"{PROMPT_MESTRE_BASE} CENÁRIO: Cyberpunk Distópico. Alta tecnologia, baixa vida, corporações cruéis.",
    "terror": f"{PROMPT_MESTRE_BASE} CENÁRIO: Terror Lovecraftiano. Mistério investigativo, sanidade frágil, horror cósmico.",
    "espacial": f"{PROMPT_MESTRE_BASE} CENÁRIO: Horror Espacial (Estilo Dead Space/Alien). Claustrofobia, naves abandonadas, silêncio."
}

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

def gerar_resposta_blindada(prompt_usuario, historico):
    # Adiciona a mensagem do usuário na memória temporária antes de enviar
    historico.append({"role": "user", "parts": [prompt_usuario]})

    for nome_modelo in MODELOS_PARA_TENTAR:
        try:
            # Sorteia uma chave se houver lista, senão tenta pegar a única que tiver
            chave_escolhida = random.choice(CHAVES) if CHAVES else os.getenv("GEMINI_API_KEY")
            
            if not chave_escolhida: raise Exception("Nenhuma chave de API encontrada!")

            genai.configure(api_key=chave_escolhida)
            
            print(f"--> Jogando no {nome_modelo}...") 
            model = genai.GenerativeModel(nome_modelo, generation_config=generation_config)
            
            response = model.generate_content(historico)
            texto_resposta = response.text
            
            # --- TRAVA DE SEGURANÇA EXTRA ---
            # Se a IA tentar escrever um roteiro (Ato 1, Ato 2...), cortamos o texto.
            if "ATO 2" in texto_resposta or "ATO 3" in texto_resposta:
                 print("⚠️ A IA tentou avançar demais. Cortando resposta.")
                 # Tenta pegar só o primeiro parágrafo se ela surtar
                 texto_resposta = texto_resposta.split("ATO 2")[0]

            # Se deu certo, salva a resposta na memória e retorna
            historico.append({"role": "model", "parts": [texto_resposta]})
            return texto_resposta, 200
            
        except Exception as e:
            print(f"❌ Erro no {nome_modelo}: {e}")
            time.sleep(0.5) 
            continue

    return "⚠️ **O Mestre precisa de um descanso.**<br>Muitos jogadores ao mesmo tempo. Aguarde 10 segundos e tente de novo.", 429

@app.route('/api/chat', methods=['POST'])
def chat():
    user_ip = request.remote_addr 
    if user_ip not in historico_por_ip: historico_por_ip[user_ip] = []
    
    dados = request.json
    # O sufixo reforça a regra a cada turno
    msg_usuario = f"{dados.get('message')} [Mestre: Responda apenas a consequência IMEDIATA dessa ação. Não avance a trama. Máximo 2 parágrafos. Espere minha próxima ação.]"
    
    texto, status = gerar_resposta_blindada(msg_usuario, historico_por_ip[user_ip])
    return jsonify({"reply": texto}), status

@app.route('/api/reset', methods=['POST'])
def reset_game():
    user_ip = request.remote_addr
    historico_por_ip[user_ip] = [] 
    
    tema = request.json.get('theme', 'medieval')
    prompt_completo = TEMAS.get(tema, TEMAS['medieval'])
    
    # Prompt inicial focado APENAS NA INTRODUÇÃO
    comando_inicial = f"""
    SISTEMA: {prompt_completo}
    INÍCIO DO JOGO (ATO 1 - CENA 1):
    Descreva onde o personagem está agora. Descreva o ambiente, o cheiro e um mistério inicial ou perigo imediato à frente.
    NÃO resolva nada. NÃO mova o personagem.
    Termine perguntando: "O que você faz?"
    """
    
    texto, status = gerar_resposta_blindada(comando_inicial, historico_por_ip[user_ip])
    return jsonify({"reply": texto}), status

@app.route('/api/continue', methods=['POST'])
def continue_game():
    user_ip = request.remote_addr
    hist = historico_por_ip.get(user_ip, [])
    
    resumo, status = gerar_resposta_blindada("Resuma os eventos até agora em 1 parágrafo curto.", hist)
    if status != 200: return jsonify({"reply": resumo}), status
    
    historico_por_ip[user_ip] = [] 
    prompt_novo = f"{PROMPT_MESTRE_BASE} \n MUDANÇA DE CAPÍTULO. Histórico anterior: {resumo} \n AÇÃO: Inicie uma nova ameaça ou reviravolta na trama agora. Seja breve."
    
    texto, status = gerar_resposta_blindada(prompt_novo, historico_por_ip[user_ip])
    return jsonify({"reply": texto}), status

if __name__ == '__main__':
    app.run(debug=True, port=5000)