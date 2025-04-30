# Instruções para limpar o histórico Git e remover tokens expostos

Siga estas instruções para limpar completamente o histórico do Git e remover tokens expostos:

## Método 1: Desbloqueio via GitHub

1. Acesse o link fornecido pelo GitHub na mensagem de erro:
   https://github.com/dshzr/relatorio-demandanet-py/security/secret-scanning/unblock-secret/2wQTPTwUywDPTXN64T0mrBJwFOb

2. Faça login no GitHub e selecione uma razão para desbloquear:
   - "O token já foi revogado" (se você já invalidou o token nas configurações do GitHub)
   - "Token usado para testes" ou outra opção apropriada

3. Clique em "Desbloquear segredo"

4. Depois disso, você poderá fazer o push normalmente

## Método 2: Revogar o token e limpar o histórico

1. **PRIMEIRO, REVOGUE O TOKEN**:
   - Acesse: https://github.com/settings/tokens
   - Encontre o token exposto e clique em "Delete" ou "Revogar"
   - Crie um novo token se necessário para uso futuro

2. **Comandos para limpar o histórico**:
   ```bash
   # Cria uma nova branch sem histórico
   git checkout --orphan temp_branch
   
   # Adiciona todos os arquivos atuais
   git add .
   
   # Cometa os arquivos
   git commit -m "Início limpo"
   
   # Deleta a branch principal antiga (pode ser main ou master)
   git branch -D main
   # OU
   git branch -D master
   
   # Renomeia a nova branch para main
   git branch -m main
   
   # Force push para sobrescrever o histórico remoto
   git push -f origin main
   ```

**IMPORTANTE**: Esse método apaga permanentemente o histórico de commits. Todos os colaboradores precisarão clonar o repositório novamente.

## Método 3: Filtrar o histórico (avançado)

Se você quiser preservar o histórico mas remover apenas o token:

```bash
git filter-branch --force --index-filter \
  "git ls-files -z '*.py' | xargs -0 sed -i 's/ghp_[a-zA-Z0-9]\{36\}/TOKEN_REMOVIDO/g'" \
  --prune-empty --tag-name-filter cat -- --all
  
git push -f origin main
```

Este comando é mais avançado e substitui o token por "TOKEN_REMOVIDO" em todos os arquivos .py do histórico. 