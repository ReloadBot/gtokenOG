from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from google_auth_oauthlib.flow import InstalledAppFlow
import os
import requests
import json
import urllib.parse

app = Flask(__name__)
app.secret_key = "sua_chave_secreta"

# Escopo de acesso para a API do Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive']

def extract_client_id(credentials_file_path):
    try:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file_path, SCOPES)
        return flow.client_config['client_id']
    except Exception as e:
        raise RuntimeError(f"Erro ao extrair client_id: {str(e)}")

def generate_authorization_url(client_id):
    try:
        # Inclui o token CSRF na URL de autorização
        redirect_uri = "http://localhost:5000"
        authorize_url = f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fdrive&access_type=offline"
        return authorize_url
    except Exception as e:
        raise RuntimeError(f"Erro ao gerar URL de autorização: {str(e)}")

def save_credentials_file(uploaded_file):
    try:
        credentials_file_path = 'uploaded_credentials.json'
        uploaded_file.save(credentials_file_path)
        return credentials_file_path
    except Exception as e:
        raise RuntimeError(f"Erro ao salvar o arquivo de credenciais: {str(e)}")

# Rota principal
@app.route('/')
def index():
    return render_template('index.html')

# Rota para gerar a URL de autorização
@app.route('/generate_token', methods=['POST'])
def generate_token():
    try:
        # Obtenha o arquivo enviado
        uploaded_file = request.files['file']

        if uploaded_file:
            # Salve o arquivo no servidor
            credentials_file_path = 'uploaded_credentials.json'
            uploaded_file.save(credentials_file_path)

            # Extrai o client_id e o client_secret do arquivo
            with open(credentials_file_path) as f:
                credentials_data = json.load(f)
                client_id = credentials_data.get('installed', {}).get('client_id', '')
                client_secret = credentials_data.get('installed', {}).get('client_secret', '')

            # Gere a URL de autorização com base nas credenciais do arquivo
            authorize_url = generate_authorization_url(client_id)

            return render_template('index.html', authorize_url=authorize_url, client_id=client_id, client_secret=client_secret)

        else:
            flash("Nenhum arquivo de credenciais enviado.", "error")

    except Exception as e:
        flash(f"Erro ao processar as credenciais: {str(e)}", "error")

    return redirect(url_for('index'))

# Rota para completar a autenticação usando a URL gerada pelo Google
@app.route('/complete_auth', methods=['GET'])
def complete_auth():
    try:
        # Obtenha o código de autorização da URL
        auth_code = request.args.get("code")

        # Obtenha o arquivo enviado
        uploaded_file = request.files['file']

        if auth_code and uploaded_file:
            # Salve o arquivo no servidor
            credentials_file_path = 'uploaded_credentials.json'
            uploaded_file.save(credentials_file_path)

            # Extrai o client_id e o client_secret do arquivo
            with open(credentials_file_path) as f:
                credentials_data = json.load(f)
                client_id = credentials_data.get('installed', {}).get('client_id', '')
                client_secret = credentials_data.get('installed', {}).get('client_secret', '')

            # Use os dados para obter o token do Google Drive
            url = "https://oauth2.googleapis.com/token"
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": auth_code,
                "grant_type": "authorization_code",
                "redirect_uri": url_for('complete_auth', _external=True)
            }

            response = requests.post(url, headers=headers, data=data)
            result_json = response.json()

            if "error" in result_json:
                return jsonify({"error": "Geração falhou!"}), 400

            gdrive_token = {
                "access_token": result_json.get("access_token"),
                "refresh_token": result_json.get("refresh_token")
            }

            return jsonify(gdrive_token), 200
        else:
            flash("Parâmetros inválidos para completar a autenticação.", "error")

    except Exception as e:
        flash(f"Erro ao completar a autenticação: {str(e)}", "error")

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)