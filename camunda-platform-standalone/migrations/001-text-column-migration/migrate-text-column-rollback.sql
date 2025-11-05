-- ============================================================================
-- ROLLBACK: Reverter coluna TEXT_ de TEXT para VARCHAR(4000)
-- ============================================================================
-- Data de criação: 2025-11-03
-- Autor: DevOps Team
--
-- DESCRIÇÃO:
--   Reverte a migração que alterou TEXT_ de VARCHAR(4000) para TEXT,
--   retornando ao tipo original VARCHAR(4000).
--
-- ⚠️  ATENÇÃO - PERDA DE DADOS:
--   Se houver registros com TEXT_ > 4000 caracteres, eles serão TRUNCADOS!
--   O script possui proteção para evitar perda acidental de dados.
--
-- TABELAS AFETADAS:
--   1. ACT_HI_VARINST  - Histórico de variáveis de instâncias
--   2. ACT_RU_VARIABLE - Variáveis de execução (runtime)
--   3. ACT_HI_DETAIL   - Detalhes históricos
--
-- IMPACTO:
--   - Tempo estimado: 2-5 segundos (baseado em ~9K registros total)
--   - Lock de tabela: SIM (ALTER TABLE)
--   - Risco de perda de dados: SIM (truncamento de textos > 4000 chars)
--
-- PRÉ-REQUISITOS:
--   - Backup do banco criado
--   - Verificação de que NÃO há dados > 4000 caracteres
--   - Camunda pode estar rodando (mas pode haver lentidão durante ALTER)
--
-- EXECUÇÃO:
--   psql -U camunda -d camunda -f migrate-text-column-rollback.sql
--
-- ============================================================================

\echo ''
\echo '=========================================================================='
\echo 'ROLLBACK: TEXT → VARCHAR(4000) em colunas TEXT_'
\echo '=========================================================================='
\echo ''
\echo '⚠️  ATENÇÃO: Esta operação pode TRUNCAR dados!'
\echo ''

-- Mostrar data/hora de início
\echo 'Início do rollback:'
SELECT NOW() as inicio_rollback;

\echo ''
\echo '--- ANTES DO ROLLBACK ---'
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
\echo '=========================================================================='
\echo 'VERIFICAÇÃO DE SEGURANÇA - Detectando possível perda de dados'
\echo '=========================================================================='
\echo ''

-- Verificar se há dados que serão truncados
DO $$
DECLARE
    v_truncated_varinst INTEGER;
    v_truncated_variable INTEGER;
    v_truncated_detail INTEGER;
    v_total_truncated INTEGER;
    v_max_length_varinst INTEGER;
    v_max_length_variable INTEGER;
    v_max_length_detail INTEGER;
BEGIN
    -- Contar registros que serão truncados em cada tabela
    SELECT COUNT(*), COALESCE(MAX(LENGTH(text_)), 0)
    INTO v_truncated_varinst, v_max_length_varinst
    FROM act_hi_varinst
    WHERE LENGTH(text_) > 4000;

    SELECT COUNT(*), COALESCE(MAX(LENGTH(text_)), 0)
    INTO v_truncated_variable, v_max_length_variable
    FROM act_ru_variable
    WHERE LENGTH(text_) > 4000;

    SELECT COUNT(*), COALESCE(MAX(LENGTH(text_)), 0)
    INTO v_truncated_detail, v_max_length_detail
    FROM act_hi_detail
    WHERE LENGTH(text_) > 4000;

    v_total_truncated := v_truncated_varinst + v_truncated_variable + v_truncated_detail;

    -- Exibir resultados da verificação
    RAISE NOTICE '';
    RAISE NOTICE '--- ANÁLISE DE IMPACTO ---';
    RAISE NOTICE 'Registros que serão truncados:';
    RAISE NOTICE '  ACT_HI_VARINST:  % registros (maior: % chars)', v_truncated_varinst, v_max_length_varinst;
    RAISE NOTICE '  ACT_RU_VARIABLE: % registros (maior: % chars)', v_truncated_variable, v_max_length_variable;
    RAISE NOTICE '  ACT_HI_DETAIL:   % registros (maior: % chars)', v_truncated_detail, v_max_length_detail;
    RAISE NOTICE '  TOTAL:           % registros', v_total_truncated;
    RAISE NOTICE '';

    -- Se houver dados que serão truncados, bloquear execução
    IF v_total_truncated > 0 THEN
        RAISE WARNING '═══════════════════════════════════════════════════════════════';
        RAISE WARNING '⚠️  PERDA DE DADOS DETECTADA!';
        RAISE WARNING '═══════════════════════════════════════════════════════════════';
        RAISE WARNING '';
        RAISE WARNING 'Foram encontrados % registros com TEXT_ > 4000 caracteres.', v_total_truncated;
        RAISE WARNING 'Estes dados serão TRUNCADOS se o rollback continuar!';
        RAISE WARNING '';
        RAISE WARNING 'AÇÕES RECOMENDADAS:';
        RAISE WARNING '  1. Revisar os dados que serão afetados';
        RAISE WARNING '  2. Fazer backup específico destes registros';
        RAISE WARNING '  3. Considerar manter a migração (TEXT permite textos maiores)';
        RAISE WARNING '';
        RAISE WARNING 'Para FORÇAR o rollback mesmo assim:';
        RAISE WARNING '  1. Abra este arquivo: migrate-text-column-rollback.sql';
        RAISE WARNING '  2. Localize a linha: RAISE EXCEPTION ''Rollback cancelado...''';
        RAISE WARNING '  3. Comente a linha adicionando -- no início';
        RAISE WARNING '  4. Execute o script novamente';
        RAISE WARNING '';
        RAISE WARNING '═══════════════════════════════════════════════════════════════';

        -- Bloquear execução para evitar perda acidental de dados
        RAISE EXCEPTION 'Rollback cancelado para proteger dados. Leia os avisos acima.';
    END IF;

    RAISE NOTICE '✓ Verificação OK: Nenhum dado será truncado';
    RAISE NOTICE '  Prosseguindo com rollback seguro...';
    RAISE NOTICE '';
END $$;

\echo ''
\echo '=========================================================================='
\echo 'INICIANDO TRANSAÇÃO'
\echo '=========================================================================='
\echo ''

BEGIN;

-- Criar tabela temporária para log do rollback
CREATE TEMP TABLE IF NOT EXISTS rollback_log (
    table_name VARCHAR(50),
    column_name VARCHAR(50),
    old_data_type VARCHAR(50),
    new_data_type VARCHAR(50),
    rollback_timestamp TIMESTAMP DEFAULT NOW()
);

-- Registrar estado antes do rollback
INSERT INTO rollback_log (table_name, column_name, old_data_type, new_data_type)
SELECT
    table_name::VARCHAR(50),
    column_name::VARCHAR(50),
    data_type::VARCHAR(50),
    'character varying'
FROM information_schema.columns
WHERE table_name IN ('act_hi_varinst', 'act_ru_variable', 'act_hi_detail')
  AND column_name = 'text_';

\echo ''
\echo '--- REVERTENDO TABELAS ---'
\echo ''

-- ============================================================================
-- 1. ACT_HI_VARINST - Reverter para VARCHAR(4000)
-- ============================================================================
\echo '1/3 Revertendo ACT_HI_VARINST...'
ALTER TABLE act_hi_varinst
  ALTER COLUMN text_ TYPE VARCHAR(4000);
\echo '    ✓ ACT_HI_VARINST revertida'

-- ============================================================================
-- 2. ACT_RU_VARIABLE - Reverter para VARCHAR(4000)
-- ============================================================================
\echo '2/3 Revertendo ACT_RU_VARIABLE...'
ALTER TABLE act_ru_variable
  ALTER COLUMN text_ TYPE VARCHAR(4000);
\echo '    ✓ ACT_RU_VARIABLE revertida'

-- ============================================================================
-- 3. ACT_HI_DETAIL - Reverter para VARCHAR(4000)
-- ============================================================================
\echo '3/3 Revertendo ACT_HI_DETAIL...'
ALTER TABLE act_hi_detail
  ALTER COLUMN text_ TYPE VARCHAR(4000);
\echo '    ✓ ACT_HI_DETAIL revertida'

\echo ''
\echo '=========================================================================='
\echo 'VALIDAÇÃO DO ROLLBACK'
\echo '=========================================================================='
\echo ''

-- Validação: Verificar se o rollback foi aplicado corretamente
DO $$
DECLARE
    v_count INTEGER;
    v_table_name TEXT;
    v_data_type TEXT;
    v_max_length INTEGER;
BEGIN
    -- Contar colunas revertidas com sucesso
    SELECT COUNT(*) INTO v_count
    FROM information_schema.columns
    WHERE table_name IN ('act_hi_varinst', 'act_ru_variable', 'act_hi_detail')
      AND column_name = 'text_'
      AND data_type = 'character varying'
      AND character_maximum_length = 4000;

    -- Verificar se todas as 3 tabelas foram revertidas
    IF v_count <> 3 THEN
        RAISE EXCEPTION 'ERRO: Rollback falhou! Esperado 3 colunas revertidas, encontrado %', v_count;
    END IF;

    RAISE NOTICE '✓ Validação OK: % colunas revertidas com sucesso', v_count;

    -- Validar tabela por tabela
    FOR v_table_name IN
        SELECT unnest(ARRAY['act_hi_varinst', 'act_ru_variable', 'act_hi_detail'])
    LOOP
        SELECT data_type, character_maximum_length
        INTO v_data_type, v_max_length
        FROM information_schema.columns
        WHERE table_name = v_table_name
          AND column_name = 'text_';

        IF v_data_type <> 'character varying' OR v_max_length <> 4000 THEN
            RAISE EXCEPTION 'ERRO: Tabela % não foi revertida corretamente (tipo: %, max: %)', v_table_name, v_data_type, v_max_length;
        END IF;

        RAISE NOTICE '  ✓ %: TEXT_'' = %(%) ', UPPER(v_table_name), v_data_type, v_max_length;
    END LOOP;
END $$;

\echo ''
\echo '--- APÓS O ROLLBACK ---'
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
\echo '✓ ROLLBACK CONCLUÍDO COM SUCESSO!'
\echo '=========================================================================='
\echo ''
\echo 'Resumo:'
\echo '  - 3 tabelas revertidas (act_hi_varinst, act_ru_variable, act_hi_detail)'
\echo '  - Coluna TEXT_ agora é VARCHAR(4000) (limite de 4000 caracteres)'
\echo '  - Migração original pode ser reaplicada: migrate-text-column-upgrade.sql'
\echo ''

-- Mostrar data/hora de término
\echo 'Término do rollback:'
SELECT NOW() as fim_rollback;

\echo ''
\echo 'IMPORTANTE:'
\echo '  1. Teste o Camunda para garantir que tudo funciona corretamente'
\echo '  2. Se precisar de textos > 4000 chars, reaplique a migração'
\echo '  3. Considere manter a versão TEXT se houver necessidade futura'
\echo ''
\echo '=========================================================================='
