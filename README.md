# Chatbot da Plataforma de Startups

Chatbot com LLM (Google Gemini) + base de conhecimento em JSON + interface web.

## Arquivos
- chatbot.py: servidor, lógica do chatbot e interface
- base_conhecimento.json: perguntas e respostas usadas como base

## Requisitos
- Python 3 

## Como rodar
1. Abra o terminal na pasta do projeto.
2. (Opcional, para usar o LLM) Defina a chave do Gemini:
   - Mac/Linux: export GEMINI_API_KEY=sua_chave
   - Windows (PowerShell): $env:GEMINI_API_KEY="sua_chave"
   A chave gratuita é criada em aistudio.google.com/app/apikey
3. Execute: python3 chatbot.py
4. Acesse o endereço que aparecer no terminal (http://localhost:5055).

Sem chave, o chatbot funciona em modo offline (busca por palavras-chave).

## Como funciona
1. O usuário digita uma pergunta na interface.
2. O programa lê o JSON e envia a base junto com a pergunta ao LLM.
3. O LLM interpreta a pergunta e responde apenas com base no JSON.
4. Se a informação não existir, o bot avisa que não sabe.

