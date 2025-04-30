import streamlit as st
import requests
from datetime import datetime, timedelta
import locale
from collections import defaultdict
import pytz
import os
import re
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração da página
st.set_page_config(
    page_title="Relatório DemandaNet",
    page_icon="📊",
    layout="wide"
)

# Obter configurações do arquivo .env
GITHUB_USER = os.getenv("GITHUB_USER", "dshzr")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Estilo CSS personalizado
st.markdown("""
<style>
    .reportview-container {
        background-color: #f5f5f5;
    }
    .main {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
    }
    .stMarkdown p {
        margin-bottom: 0.5rem;
    }
    .date-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 20px;
        border-left: 5px solid #4e73df;
    }
    .date-header {
        font-size: 1.25rem;
        font-weight: bold;
        margin-bottom: 16px;
        color: #333;
    }
    .commit-item {
        padding: 8px 0;
        border-bottom: 1px solid #eee;
    }
    .commit-item:last-child {
        border-bottom: none;
    }
    .stMultiSelect [data-testid=stMultiSelect] {
        max-height: 12rem;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def obter_repositorios(usuario, token):
    """Obter lista de repositórios do usuário via API do GitHub, incluindo privados."""
    # Para obter repositórios privados, usamos o endpoint de usuário autenticado
    # Se o token não estiver disponível, usamos apenas os públicos
    if token:
        # URL para obter todos os repositórios (incluindo privados) que o usuário tem acesso
        url = "https://api.github.com/user/repos"
        headers = {"Authorization": f"token {token}"}  # Formato correto para tokens
        params = {"per_page": 100, "sort": "updated", "affiliation": "owner,organization_member"}
    else:
        # Fallback para repositórios públicos se não houver token
        url = f"https://api.github.com/users/{usuario}/repos"
        headers = {}
        params = {"per_page": 100}
    
    try:
        # Fazer a solicitação
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        repos = res.json()
        
        # Log para depuração
        st.session_state["repos_count"] = len(repos)
        
        # Extrair nomes dos repositórios e adicionar informação se é privado ou não
        return [(repo["name"], repo.get("private", False)) for repo in repos]
    except Exception as e:
        st.error(f"Erro ao buscar repositórios: {str(e)}")
        return []

def obter_commits(usuario, repo, token, data_inicio, data_fim=None):
    """Função para obter commits de um repositório específico."""
    url = f"https://api.github.com/repos/{usuario}/{repo}/commits"
    headers = {"Authorization": f"token {token}"} if token else {}  # Formato correto para tokens
    params = {"since": data_inicio, "per_page": 100}
    
    if data_fim:
        params["until"] = data_fim
    
    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()  # Levanta exceção para status codes de erro
        return res.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao buscar commits de {repo}: {str(e)}")
        return []

# Função para formatar a data sem depender do locale
def formatar_data_pt(data_obj):
    """Formata a data em português sem depender do locale do sistema"""
    dias_semana = {
        0: "Segunda-feira",
        1: "Terça-feira",
        2: "Quarta-feira",
        3: "Quinta-feira",
        4: "Sexta-feira",
        5: "Sábado",
        6: "Domingo"
    }
    
    meses = {
        1: "janeiro",
        2: "fevereiro",
        3: "março",
        4: "abril",
        5: "maio",
        6: "junho",
        7: "julho",
        8: "agosto",
        9: "setembro",
        10: "outubro",
        11: "novembro",
        12: "dezembro"
    }
    
    dia_semana = dias_semana[data_obj.weekday()]
    dia = data_obj.day
    mes = meses[data_obj.month]
    ano = data_obj.year
    
    return f"{dia_semana}, {dia} de {mes} de {ano}"

def main():
    # Título principal
    st.title("📊 Relatório de Commits DemandaNet")
    
    # Configurar locale para português - tentativa para outros recursos
    try:
        for locale_name in ['pt_BR.UTF-8', 'pt_BR.utf8', 'Portuguese_Brazil.1252']:
            try:
                locale.setlocale(locale.LC_TIME, locale_name)
                break
            except locale.Error:
                continue
    except:
        pass  # Silencioso, já que usaremos nossa função personalizada
    
    # Verificar se o token está presente
    if not GITHUB_TOKEN:
        st.warning("Token do GitHub não encontrado no arquivo .env. Apenas repositórios públicos serão acessíveis.")
    
    # Carregar repositórios do usuário
    with st.spinner("Carregando repositórios..."):
        repositorios_infos = obter_repositorios(GITHUB_USER, GITHUB_TOKEN)
    
    if not repositorios_infos:
        st.error(f"Nenhum repositório encontrado para o usuário {GITHUB_USER} ou erro ao acessar a API.")
        st.stop()
    
    # Criar lista formatada para o multiselect
    opcoes_repos = []
    for repo_name, is_private in repositorios_infos:
        label = f"{repo_name} {'🔒' if is_private else '🌐'}"
        opcoes_repos.append((label, repo_name))
    
    # Mostrar quantidade de repositórios disponíveis
    privados = sum(1 for _, private in repositorios_infos if private)
    publicos = len(repositorios_infos) - privados
    st.info(f"Repositórios disponíveis: {len(repositorios_infos)} ({privados} privados, {publicos} públicos)")
    
    # Selecionar repositórios
    labels = [label for label, _ in opcoes_repos]
    default_indices = [0, 1] if len(labels) >= 2 else [0] if labels else []
    default_options = [labels[i] for i in default_indices if i < len(labels)]
    
    selecionados_labels = st.multiselect(
        "Selecione os repositórios (🔒 = privado, 🌐 = público)",
        options=labels,
        default=default_options
    )
    
    # Mapear rótulos selecionados para nomes reais de repositórios
    repositorios_selecionados = []
    for label in selecionados_labels:
        for option_label, repo_name in opcoes_repos:
            if option_label == label:
                repositorios_selecionados.append(repo_name)
                break
    
    if not repositorios_selecionados:
        st.warning("Selecione pelo menos um repositório para gerar o relatório.")
        st.stop()
    
    # Layout para seleção de datas
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        # Data padrão inicial: primeiro dia do mês atual
        data_padrao_inicio = datetime.now().replace(day=1)
        data_inicio = st.date_input("Data inicial", value=data_padrao_inicio)
    
    with col2:
        # Data padrão final: hoje
        data_padrao_fim = datetime.now()
        data_fim = st.date_input("Data final", value=data_padrao_fim)
    
    with col3:
        st.write("")  # Espaço em branco
        st.write("")  # Espaço em branco
        # Botão centralizado
        gerar = st.button("Gerar Relatório", type="primary", use_container_width=True)
    
    # Se botão for pressionado ou na inicialização da aplicação
    if gerar:
        # Verificar se data final é posterior à inicial
        if data_fim < data_inicio:
            st.error("A data final deve ser posterior à data inicial!")
            return
        
        # Converter datas para ISO
        data_inicio_iso = datetime.combine(data_inicio, datetime.min.time()).isoformat()
        data_fim_iso = datetime.combine(data_fim, datetime.max.time()).isoformat()
        
        # Mostrar quais dados serão carregados
        st.info(f"Buscando commits de **{data_inicio.strftime('%d/%m/%Y')}** a **{data_fim.strftime('%d/%m/%Y')}** para {len(repositorios_selecionados)} repositórios")
        
        # Barra de progresso
        progresso = st.progress(0)
        
        # Dicionário para associar cada data formatada à sua data original para ordenação
        datas_para_ordenacao = {}
        # Relatório agrupado por data
        relatorio = defaultdict(list)
        
        # Buscar commits para cada repositório
        for i, repo in enumerate(repositorios_selecionados):
            with st.status(f"Buscando commits em: {repo}...", expanded=False) as status:
                commits = obter_commits(GITHUB_USER, repo, GITHUB_TOKEN, data_inicio_iso, data_fim_iso)
                
                if not commits:
                    status.update(label=f"Nenhum commit encontrado em {repo}", state="error")
                    continue
                
                for commit in commits:
                    try:
                        data_iso = commit["commit"]["author"]["date"]
                        data_obj = datetime.fromisoformat(data_iso.replace("Z", ""))
                        
                        # Usar nossa própria função de formatação em vez do strftime
                        data_formatada = formatar_data_pt(data_obj)
                        
                        # Armazenar a data original para ordenação
                        datas_para_ordenacao[data_formatada] = data_obj
                        
                        mensagem = commit["commit"]["message"].strip()
                        # Guardar apenas a primeira linha da mensagem (o título do commit)
                        primeira_linha = mensagem.split('\n')[0].strip()
                        relatorio[data_formatada].append(primeira_linha)
                    except (KeyError, ValueError) as e:
                        st.warning(f"Erro ao processar commit: {str(e)}")
                
                status.update(label=f"✅ {len(commits)} commits processados em {repo}", state="complete")
            
            # Atualizar barra de progresso
            progresso.progress((i + 1) / len(repositorios_selecionados))
        
        # Remover barra de progresso
        progresso.empty()
        
        # Verificar se encontrou algum commit
        if not relatorio:
            st.warning("Nenhum commit encontrado no período selecionado.")
            return
        
        # Exibir relatório
        st.subheader("Relatório de Atividades")
        
        # Contador de commits
        total_commits = sum(len(msgs) for msgs in relatorio.values())
        st.info(f"Total de commits: {total_commits}")
        
        # Ordenar as datas usando as datas originais para ordenação
        datas_ordenadas = sorted(relatorio.keys(), key=lambda d: datas_para_ordenacao.get(d, datetime.now()))
        
        # Exibir commits agrupados por data em cards simples
        for data in datas_ordenadas:
            # Criar card para cada data
            with st.container():
                st.markdown(f'<div class="date-card"><div class="date-header">📅 {data}</div>', unsafe_allow_html=True)
                
                # Listar os commits deste dia
                for mensagem in relatorio[data]:
                    st.markdown(f'<div class="commit-item">• {mensagem}</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main() 