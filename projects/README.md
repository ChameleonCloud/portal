# Publication Collection and Analysis

A subset of this projects django app is used for publication analysis.

## Data Collection

The `./user_publication/publications.py:import_pubs` function is the main entrypoint for automatic publication collection.
The `./user_publication/` directory contains files for pulling pubs from Scopus, Semantic Scholar, OpenAlex, and Science Direct.

Users and admins can submit bibtex via `forms.py:AddBibtexPublicationForm`. Admins do this on the admin page from google scholar
library exports.

Additionally, `/user_publication/publications.py:update_citations_task` is used to update citation counts of all approved publications.

We also have django management commands to normalize publication types (see `./management/commands/normalize_pub_types.py`) and
to normalize forum data (see `./management/commands/normalize_publication_forums.py`)

## Review

We review publications using the admin panel. See `./admin.py` for some custom form fields that we add to make this process easier.

See `./user_publication/utils.py` for how we find similar publications for reviewers to check during this process.

## Analysis

Here are SQL queries that we used in combination with grafana to analyze the publication data

### Publication count
```
SELECT COUNT(id)
FROM chameleon_prod.projects_publication
WHERE status LIKE '%approved%' and year < 2026
```

### Top publications
Select the top publications based on citation count, and a summary of their attributes
```
SELECT
    pp.id AS publication_id,
    pp.title,
    pp.author,
    pp.forum,
    pp.year AS year,
    GROUP_CONCAT(DISTINCT rp.name ORDER BY rp.name SEPARATOR ', ') AS sources,
    pc.semantic_scholar_citation_count AS citations,
    pc.semantic_scholar_citation_count
        / NULLIF(YEAR(CURDATE()) - pp.year, 0) AS citations_per_year,
    CASE
        WHEN COUNT(DISTINCT rp.name) = 1
         AND MAX(rp.name) = 'user_reported'
        THEN TRUE
        ELSE FALSE
    END AS `user reported only`,
    MAX(rp.acknowledges_chameleon = 1) AS `acks`,
    (MAX(cp.id IS NOT NULL) or MAX(rp.cites_chameleon)) AS `cites`,
    CASE
        WHEN MAX(rp.acknowledges_chameleon = 1) = 0
         AND MAX(cp.id IS NOT NULL) = 0
         AND (MAX(rp.approved_with = 'justification') = 1 or MAX(rp.approved_with = 'email') = 1)
        THEN TRUE
        ELSE FALSE
    END AS `email or justification`
FROM projects_publicationcitation pc
    JOIN projects_publication pp
        ON pp.id = pc.publication_id
    JOIN projects_rawpublication rp
        ON rp.publication_id = pp.id
    LEFT JOIN projects_rawpublication_chameleon_publications cp
        ON cp.rawpublication_id = rp.id
    LEFT JOIN projects_rawpublication_publication_queries pq
        ON pq.rawpublication_id = rp.id
WHERE pc.semantic_scholar_citation_count > 100
  AND (
        cp.id IS NOT NULL
     OR pq.id IS NOT NULL
     OR rp.name = 'user_reported'
  )
GROUP BY
    pp.id,
    pp.title,
    pp.author,
    pp.forum,
    pp.year,
    pc.semantic_scholar_citation_count
ORDER BY citations_per_year DESC;
```

### Top Forum Organizers
```
select 
pf.organization, count(pp.id) as c
from projects_publication pp
join projects_forum pf on  pf.id = pp.normalized_forum_id
group by pf.organization
order by c desc
```

### Top Forums
```
select 
pf.name, count(pp.id) as c
from projects_publication pp
join projects_forum pf on  pf.id = pp.normalized_forum_id
group by pf.name
order by c desc
```