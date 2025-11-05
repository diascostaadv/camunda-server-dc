-- ============================================================================
-- MIGRAÇÃO: Alterar coluna TEXT_ de VARCHAR(4000) para TEXT
-- ============================================================================
-- Data de criação: 2025-11-03
-- Autor: DevOps Team
--
-- DESCRIÇÃO:
--   Altera o tipo da coluna TEXT_ de VARCHAR(4000) para TEXT em 3 tabelas
--   do Camunda BPM, permitindo armazenar textos maiores que 4000 caracteres.
--
-- TABELAS AFETADAS:
--   1. ACT_HI_VARINST  - Histórico de variáveis de instâncias
--   2. ACT_RU_VARIABLE - Variáveis de execução (runtime)
--   3. ACT_HI_DETAIL   - Detalhes históricos
--
-- IMPACTO:
--   - Tempo estimado: 2-5 segundos (baseado em ~9K registros total)
--   - Lock de tabela: SIM (ALTER TABLE)
--   - Reversível: SIM (via migrate-text-column-rollback.sql)
--
-- PRÉ-REQUISITOS:
--   - Backup do banco criado
--   - Camunda pode estar rodando (mas pode haver lentidão durante ALTER)
--   - Recomendado: executar em janela de manutenção
--
-- EXECUÇÃO:
--   psql -U camunda -d camunda -f migrate-text-column-upgrade.sql
--
-- ============================================================================

\echo ''
\echo '=========================================================================='
\echo 'MIGRAÇÃO: VARCHAR(4000) → TEXT em colunas TEXT_'
\echo '=========================================================================='
\echo ''

-- Mostrar data/hora de início
\echo 'Início da migração:'
SELECT NOW() as inicio_migracao;

\echo ''
\echo '--- ANTES DA MIGRAÇÃO ---'
\echo 'Estrutura atual das colunas:'
SELECT
    table_name,
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_name IN ('act_hi_varinst', 'act_ru_variable', 'act_hi_detail')
  AND column_name = 'text_'
ORDER BY table_name;

\echo ''
\echo 'Quantidade de registros por tabela:'
SELECT 'act_hi_varinst' as tabela, COUNT(*) as total FROM act_hi_varinst
UNION ALL
SELECT 'act_ru_variable', COUNT(*) FROM act_ru_variable
UNION ALL
SELECT 'act_hi_detail', COUNT(*) FROM act_hi_detail;

\echo ''
\echo '=========================================================================='
\echo 'INICIANDO TRANSAÇÃO'
\echo '=========================================================================='
\echo ''

BEGIN;

-- Criar tabela temporária para log da migração
CREATE TEMP TABLE IF NOT EXISTS migration_log (
    table_name VARCHAR(50),
    column_name VARCHAR(50),
    old_data_type VARCHAR(50),
    old_max_length INTEGER,
    migration_timestamp TIMESTAMP DEFAULT NOW()
);

-- Registrar estado antes da migração
INSERT INTO migration_log (table_name, column_name, old_data_type, old_max_length)
SELECT
    table_name::VARCHAR(50),
    column_name::VARCHAR(50),
    data_type::VARCHAR(50),
    character_maximum_length
FROM information_schema.columns
WHERE table_name IN ('act_hi_varinst', 'act_ru_variable', 'act_hi_detail')
  AND column_name = 'text_';

\echo ''
\echo '--- ALTERANDO TABELAS ---'
\echo ''

-- ============================================================================
-- 1. ACT_HI_VARINST - Histórico de variáveis
-- ============================================================================
\echo '1/3 Alterando ACT_HI_VARINST...'
ALTER TABLE act_hi_varinst
  ALTER COLUMN text_ TYPE TEXT;
\echo '    ✓ ACT_HI_VARINST alterada'

-- ============================================================================
-- 2. ACT_RU_VARIABLE - Variáveis runtime
-- ============================================================================
\echo '2/3 Alterando ACT_RU_VARIABLE...'
ALTER TABLE act_ru_variable
  ALTER COLUMN text_ TYPE TEXT;
\echo '    ✓ ACT_RU_VARIABLE alterada'

-- ============================================================================
-- 3. ACT_HI_DETAIL - Detalhes históricos
-- ============================================================================
\echo '3/3 Alterando ACT_HI_DETAIL...'
ALTER TABLE act_hi_detail
  ALTER COLUMN text_ TYPE TEXT;
\echo '    ✓ ACT_HI_DETAIL alterada'

\echo ''
\echo '=========================================================================='
\echo 'VALIDAÇÃO DA MIGRAÇÃO'
\echo '=========================================================================='
\echo ''

-- Validação: Verificar se as alterações foram aplicadas corretamente
DO $$
DECLARE
    v_count INTEGER;
    v_table_name TEXT;
    v_data_type TEXT;
BEGIN
    -- Contar colunas alteradas com sucesso
    SELECT COUNT(*) INTO v_count
    FROM information_schema.columns
    WHERE table_name IN ('act_hi_varinst', 'act_ru_variable', 'act_hi_detail')
      AND column_name = 'text_'
      AND data_type = 'text';

    -- Verificar se todas as 3 tabelas foram alteradas
    IF v_count <> 3 THEN
        RAISE EXCEPTION 'ERRO: Migração falhou! Esperado 3 colunas alteradas, encontrado %', v_count;
    END IF;

    RAISE NOTICE '✓ Validação OK: % colunas alteradas com sucesso', v_count;

    -- Validar tabela por tabela
    FOR v_table_name IN
        SELECT unnest(ARRAY['act_hi_varinst', 'act_ru_variable', 'act_hi_detail'])
    LOOP
        SELECT data_type INTO v_data_type
        FROM information_schema.columns
        WHERE table_name = v_table_name
          AND column_name = 'text_';

        IF v_data_type <> 'text' THEN
            RAISE EXCEPTION 'ERRO: Tabela % não foi alterada corretamente (tipo: %)', v_table_name, v_data_type;
        END IF;

        RAISE NOTICE '  ✓ %: TEXT_'' = %', UPPER(v_table_name), v_data_type;
    END LOOP;
END $$;

\echo ''
\echo '--- APÓS A MIGRAÇÃO ---'
\echo 'Nova estrutura das colunas:'
SELECT
    table_name,
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_name IN ('act_hi_varinst', 'act_ru_variable', 'act_hi_detail')
  AND column_name = 'text_'
ORDER BY table_name;

\echo ''
\echo '=========================================================================='
\echo 'COMMIT DA TRANSAÇÃO'
\echo '=========================================================================='
\echo ''

COMMIT;

\echo ''
\echo '=========================================================================='
\echo '✓ MIGRAÇÃO CONCLUÍDA COM SUCESSO!'
\echo '=========================================================================='
\echo ''
\echo 'Resumo:'
\echo '  - 3 tabelas alteradas (act_hi_varinst, act_ru_variable, act_hi_detail)'
\echo '  - Coluna TEXT_ agora é do tipo TEXT (sem limite de tamanho)'
\echo '  - Rollback disponível em: migrate-text-column-rollback.sql'
\echo ''

-- Mostrar data/hora de término
\echo 'Término da migração:'
SELECT NOW() as fim_migracao;

\echo ''
\echo 'IMPORTANTE:'
\echo '  1. Teste o Camunda para garantir que tudo funciona corretamente'
\echo '  2. Mantenha o backup por pelo menos 7 dias'
\echo '  3. Se necessário reverter, use: migrate-text-column-rollback.sql'
\echo ''
\echo '=========================================================================='
