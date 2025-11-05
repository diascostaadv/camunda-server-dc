# Migração 001: Alteração de Colunas TEXT_ (VARCHAR → TEXT)

## Visão Geral

Esta migração altera o tipo de dados da coluna `TEXT_` de `VARCHAR(4000)` para `TEXT` em 3 tabelas do Camunda BPM, permitindo armazenar textos maiores que 4000 caracteres.

**Data de criação:** 2025-11-03
**Versão:** 001
**Status:** Pronto para produção

---

## Tabelas Afetadas

| Tabela | Registros | Tamanho | Descrição |
|--------|-----------|---------|-----------|
| `act_hi_varinst` | ~2.700 | 4.3 MB | Histórico de variáveis de instâncias |
| `act_ru_variable` | ~2.300 | 3.1 MB | Variáveis de execução (runtime) |
| `act_hi_detail` | ~4.200 | 9.2 MB | Detalhes históricos |

**Total:** ~9.200 registros | ~16.6 MB

---

## Motivação

### Problema
A coluna `TEXT_` estava limitada a 4000 caracteres (`VARCHAR(4000)`), causando truncamento de dados ou erros quando variáveis de processo continham textos maiores.

### Solução
Alterar para tipo `TEXT`, que não possui limite de tamanho, permitindo armazenar textos de qualquer tamanho.

### Benefícios
- ✅ Suporte para textos maiores que 4000 caracteres
- ✅ Evita erros de truncamento
- ✅ Compatível com PostgreSQL 16.3
- ✅ Sem impacto de performance (TEXT é eficiente no PostgreSQL)

---

## Arquivos

```
001-text-column-migration/
├── migrate-text-column-upgrade.sql    # Script de migração (VARCHAR → TEXT)
├── migrate-text-column-rollback.sql   # Script de rollback (TEXT → VARCHAR)
├── apply-migration.sh                 # Executor automático com backup
├── README-MIGRATION.md                # Esta documentação
├── backups/                           # Backups automáticos
└── logs/                              # Logs de execução
```

---

## Como Executar

### Opção 1: Script Automático (RECOMENDADO)

O script `apply-migration.sh` realiza todas as etapas automaticamente:

```bash
# 1. Testar sem executar (dry-run)
cd migrations/001-text-column-migration
./apply-migration.sh --dry-run

# 2. Executar migração (com backup automático)
./apply-migration.sh

# 3. Se necessário, fazer rollback
./apply-migration.sh --rollback
```

**O que o script faz:**
- ✅ Verifica pré-requisitos
- ✅ Testa conexão com banco
- ✅ Cria backup automaticamente
- ✅ Executa migração
- ✅ Valida alterações
- ✅ Gera logs detalhados

### Opção 2: Execução Manual

Se preferir executar manualmente via psql:

```bash
# 1. Criar backup manual
pg_dump -U camunda -d camunda > backup-before-migration.sql

# 2. Executar migração
psql -U camunda -d camunda -f migrate-text-column-upgrade.sql

# 3. Verificar resultado
psql -U camunda -d camunda -c "\d act_hi_varinst"
```

### Opção 3: Via Docker (Produção)

```bash
# 1. Conectar à VM
ssh -i ~/.ssh/mac_m2_ssh ubuntu@201.23.67.197

# 2. Navegar para o diretório
cd ~/camunda-platform/migrations/001-text-column-migration

# 3. Executar (irá usar Docker automaticamente)
./apply-migration.sh
```

---

## Pré-Requisitos

### Ambiente
- ✅ PostgreSQL 16.3 ou superior
- ✅ Camunda BPM 7.23.0
- ✅ Acesso ao banco de dados (psql ou Docker)
- ✅ Espaço em disco para backup (~20-30 MB)

### Permissões
- ✅ Usuário com privilégios de ALTER TABLE
- ✅ Acesso SSH à VM (se produção)

### Validações Antes de Executar
```sql
-- Verificar estrutura atual
SELECT table_name, column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name IN ('act_hi_varinst', 'act_ru_variable', 'act_hi_detail')
  AND column_name = 'text_';

-- Resultado esperado ANTES da migração:
-- data_type: character varying
-- character_maximum_length: 4000
```

---

## Impacto e Downtime

### Performance
- **Tempo de execução:** 2-5 segundos
- **Lock de tabela:** Sim (ALTER TABLE adquire lock exclusivo)
- **Impacto em produção:** Baixo (operação rápida)

### Downtime
- **Recomendado:** Executar em janela de manutenção
- **Opcional:** Pode executar com Camunda rodando (mas pode haver lentidão temporária)

### Rollback
- **Tempo:** 2-5 segundos
- **Risco de perda de dados:** **SIM** se houver textos > 4000 chars
- **Proteção:** Script de rollback verifica e bloqueia se detectar possível perda

---

## Validação Pós-Migração

### 1. Verificar Estrutura

```sql
-- Deve retornar: data_type = 'text'
SELECT table_name, column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name IN ('act_hi_varinst', 'act_ru_variable', 'act_hi_detail')
  AND column_name = 'text_';
```

### 2. Verificar Dados

```sql
-- Quantidade de registros deve ser a mesma
SELECT 'act_hi_varinst' as tabela, COUNT(*) FROM act_hi_varinst
UNION ALL
SELECT 'act_ru_variable', COUNT(*) FROM act_ru_variable
UNION ALL
SELECT 'act_hi_detail', COUNT(*) FROM act_hi_detail;
```

### 3. Testar Camunda

```bash
# Verificar se Camunda está funcionando
curl -u demo:DiasCosta@!!2025 http://201.23.67.197:8080/engine-rest/engine

# Iniciar uma instância de processo de teste
# Verificar logs do Camunda
docker logs camunda-platform-camunda-1 --tail 50
```

---

## Rollback

### Quando Fazer Rollback?

- ❌ Erros na aplicação após migração
- ❌ Performance degradada
- ❌ Incompatibilidade detectada
- ⚠️ **ATENÇÃO:** Só faça rollback se não houver textos > 4000 chars!

### Como Fazer Rollback

```bash
# Opção 1: Via script automático
./apply-migration.sh --rollback

# Opção 2: Manual
psql -U camunda -d camunda -f migrate-text-column-rollback.sql
```

### Proteção Contra Perda de Dados

O script de rollback verifica automaticamente se há dados > 4000 caracteres:

```sql
-- Exemplo de output se houver dados que serão truncados:
⚠️  PERDA DE DADOS DETECTADA!
Foram encontrados 5 registros com TEXT_ > 4000 caracteres.
Estes dados serão TRUNCADOS se o rollback continuar!
```

Se você realmente quiser forçar o rollback mesmo assim:
1. Abra `migrate-text-column-rollback.sql`
2. Localize a linha: `RAISE EXCEPTION 'Rollback cancelado...'`
3. Comente a linha: `-- RAISE EXCEPTION 'Rollback cancelado...'`
4. Execute novamente

---

## Troubleshooting

### Erro: "permission denied"

```bash
# Dar permissão ao script
chmod +x apply-migration.sh
```

### Erro: "connection refused"

```bash
# Verificar se banco está rodando
docker ps | grep db

# Testar conexão
docker exec camunda-platform-db-1 psql -U camunda -d camunda -c "SELECT 1"
```

### Migração travou / timeout

```bash
# Verificar locks
SELECT * FROM pg_locks WHERE granted = false;

# Se necessário, matar processo (CUIDADO!)
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE datname = 'camunda' AND state = 'active';
```

### Rollback falhou

```bash
# Restaurar do backup
psql -U camunda -d camunda < backups/camunda-backup-before-text-column-migration-*.sql
```

---

## Logs e Backups

### Backups Automáticos

Localizados em: `migrations/001-text-column-migration/backups/`

```bash
# Listar backups
ls -lh backups/

# Restaurar backup específico
psql -U camunda -d camunda < backups/camunda-backup-before-text-column-migration-YYYYMMDD_HHMMSS.sql
```

### Logs de Execução

Localizados em: `migrations/001-text-column-migration/logs/`

```bash
# Ver último log
tail -f logs/migration-text-column-migration-*.log

# Buscar erros
grep -i error logs/migration-text-column-migration-*.log
```

---

## Checklist de Execução

### Antes da Migração

- [ ] Ler toda esta documentação
- [ ] Verificar backup do banco está atualizado
- [ ] Testar com `--dry-run`
- [ ] Comunicar equipe (se produção)
- [ ] Verificar espaço em disco (mínimo 100 MB livre)

### Durante a Migração

- [ ] Executar `./apply-migration.sh`
- [ ] Monitorar logs em tempo real
- [ ] Verificar se não há erros no output

### Após a Migração

- [ ] Validar estrutura das colunas
- [ ] Testar Camunda (criar instância de processo)
- [ ] Verificar logs do Camunda
- [ ] Manter backup por 7 dias
- [ ] Documentar em histórico de mudanças

---

## FAQ

### P: Posso executar com Camunda rodando?
**R:** Sim, mas pode haver lentidão temporária durante o ALTER TABLE. Recomendamos executar em horário de baixo uso.

### P: Quanto tempo leva?
**R:** 2-5 segundos com ~9K registros. O tempo é proporcional ao tamanho das tabelas.

### P: Há risco de perda de dados?
**R:** Não na migração (VARCHAR → TEXT). Sim no rollback se houver textos > 4000 chars.

### P: Preciso parar o Camunda?
**R:** Não é obrigatório, mas recomendado para evitar locks e garantir consistência.

### P: Como sei se deu certo?
**R:** O script mostra "✓ MIGRAÇÃO CONCLUÍDA COM SUCESSO!" e valida automaticamente.

### P: Posso executar múltiplas vezes?
**R:** Sim, a migração é idempotente. Se já estiver em TEXT, não terá efeito.

### P: E se der erro?
**R:** O script usa transações (BEGIN/COMMIT). Se der erro, nada é alterado. Verifique os logs.

---

## Suporte

**Documentação:**
- Camunda Database: https://docs.camunda.org/manual/latest/user-guide/process-engine/database/
- PostgreSQL ALTER TABLE: https://www.postgresql.org/docs/16/sql-altertable.html

**Contato:**
- DevOps Team
- Email: devops@empresa.com
- Slack: #camunda-support

---

## Histórico de Mudanças

| Data | Versão | Autor | Descrição |
|------|--------|-------|-----------|
| 2025-11-03 | 1.0 | DevOps | Criação inicial da migração |

---

**Última atualização:** 2025-11-03
