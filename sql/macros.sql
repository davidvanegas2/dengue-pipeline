-- Epidemiological weeks: the MMWR calendar used by INS.
-- DuckDB week() uses ISO weeks; dayofweek() returns Sunday=0 through Saturday=6.
-- The linter treats some DuckDB macro parameters as types; disable only those rules.
-- noqa: disable=CP03,CP05

CREATE OR REPLACE MACRO epi_week_start(date_value) AS (
    CAST(date_value AS DATE) - CAST(dayofweek(CAST(date_value AS DATE)) AS INTEGER)
);

-- Wednesday determines the epidemiological epi_year.
CREATE OR REPLACE MACRO epi_year(date_value) AS (
    year(epi_week_start(date_value) + 3)
);

-- Week 1 contains January 4.
CREATE OR REPLACE MACRO first_epi_week_start(year_value) AS (
    epi_week_start(make_date(CAST(year_value AS BIGINT), 1, 4))
);

CREATE OR REPLACE MACRO epi_week(date_value) AS (
    1 + datediff(
        'day', first_epi_week_start(epi_year(date_value)), epi_week_start(date_value)
    ) // 7
);

-- Uppercase place names and remove accents and punctuation.
CREATE OR REPLACE MACRO normalize_name(text_value) AS (
    trim(
        regexp_replace(
            regexp_replace(upper(strip_accents(text_value)), '[^A-Z0-9 ]', ' ', 'g'),
            ' +', ' ', 'g'
        )
    )
);

-- Normalize Excel-style codes: " 8.0 " -> "8".
CREATE OR REPLACE MACRO clean_code(value) AS (
    regexp_replace(trim(CAST(value AS VARCHAR)), '\.0+$', '')
);

-- Pad leading zeros: dane_code('8', 2) -> '08'.
-- lpad() also truncates values longer than the requested width.
CREATE OR REPLACE MACRO dane_code(value, width) AS (
    lpad(clean_code(value), width, '0')
);

-- Accept either a three-digit municipality suffix or a complete DIVIPOLA code.
CREATE OR REPLACE MACRO municipality_code(department, municipality) AS (
    CASE
        WHEN length(clean_code(municipality)) = 5 THEN clean_code(municipality)
        ELSE dane_code(department, 2) || dane_code(municipality, 3)
    END
);

-- Parse the date part of SIVIGILA text dates. INS Excel exports write
-- '16/05/2024 12:00:00 a. m.' (day first, Spanish AM/PM); other sources use ISO dates.
-- Try day-first before ISO so '6/08/2024' is never read as month-first.
CREATE OR REPLACE MACRO parse_date_text(value) AS (
    coalesce(
        CAST(try_strptime(split_part(trim(CAST(value AS VARCHAR)), ' ', 1), '%d/%m/%Y') AS DATE),
        try_cast(split_part(trim(CAST(value AS VARCHAR)), ' ', 1) AS DATE)
    )
);
