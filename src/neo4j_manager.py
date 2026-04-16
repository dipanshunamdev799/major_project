import hashlib
import math
import re
import time
from collections import Counter
from typing import Any
from urllib.parse import urlparse

from neo4j import GraphDatabase

import src.config as config
from src.embeddings import compute_similarity, get_embedding

RELATIONSHIP_PATTERN = re.compile(r"[^A-Z0-9_]")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9&.\-]{1,}")


class Neo4jManager:
    def __init__(self):
        self.driver = None
        if not (config.NEO4J_URI and config.NEO4J_USERNAME and config.NEO4J_PASSWORD):
            return
        try:
            self.driver = GraphDatabase.driver(
                config.NEO4J_URI,
                auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD),
            )
            self._create_constraints()
        except Exception as e:
            print(f"Neo4j Connection Error: {e}")
            self.driver = None



    def _create_constraints(self):
        if not self.driver:
            return
        statements = [
            "CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (e:Entity) REQUIRE e.key IS UNIQUE",
            "CREATE CONSTRAINT source_url IF NOT EXISTS FOR (s:Source) REQUIRE s.url IS UNIQUE",
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX source_hash IF NOT EXISTS FOR (s:Source) ON (s.content_hash)",
        ]

        def work(session):
            for statement in statements:
                session.run(statement)
            # Existing graphs from earlier code versions may contain relationships without evidence_count.
            # Setting a default prevents noisy warnings and keeps retrieval scoring consistent.
            session.run(
                """
                MATCH ()-[r]->()
                WHERE r.evidence_count IS NULL
                SET r.evidence_count = 0
                """
            )

        try:
            with self.driver.session() as session:
                session.execute_write(work)
        except Exception as e:
            print(f"Neo4j constrain execution error: {e}")

    @staticmethod
    def _canonicalize_name(name: str) -> str:
        cleaned = re.sub(r"\s+", " ", str(name or "").strip())
        return cleaned

    @staticmethod
    def _entity_key(name: str, entity_type: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        typed = re.sub(r"[^a-z0-9]+", "-", entity_type.lower()).strip("-") or "entity"
        return f"{typed}:{normalized or 'unknown'}"

    @staticmethod
    def _sanitize_label(entity_type: str) -> str:
        letters_only = re.sub(r"[^A-Za-z0-9]", "", entity_type.title()) or "Entity"
        return letters_only

    @staticmethod
    def _sanitize_relationship_type(value: str) -> str:
        candidate = RELATIONSHIP_PATTERN.sub("_", str(value or "RELATED_TO").upper()).strip("_")
        return candidate or "RELATED_TO"

    @staticmethod
    def _hash_source(url: str, content: str = "") -> str:
        return hashlib.sha256(f"{url}|{content}".encode("utf-8")).hexdigest()

    @staticmethod
    def _extract_query_terms(query_text: str) -> list[str]:
        return [token.lower() for token in TOKEN_PATTERN.findall(query_text or "") if len(token) > 2]

    def close(self):
        if self.driver:
            self.driver.close()

    def add_financial_data(self, graph_data: dict, source_url: str, source_title: str = "", source_content: str = "") -> bool:
        if not self.driver or not graph_data:
            return False

        entities = graph_data.get("entities", [])
        relationships = graph_data.get("relationships", [])
        if not entities and not relationships:
            return False

        source_domain = urlparse(source_url).netloc
        source_hash = self._hash_source(source_url, source_content[:1000])
        normalized_entities = []

        for ent in entities:
            name = self._canonicalize_name(ent.get("name", ""))
            entity_type = self._sanitize_label(ent.get("type", "Entity"))
            description = str(ent.get("description", "")).strip()
            if not name:
                continue
            normalized_entities.append(
                {
                    "name": name,
                    "key": self._entity_key(name, entity_type),
                    "type": entity_type,
                    "description": description,
                    "embedding": get_embedding(f"{name}. {description}") if description else [],
                }
            )

        entity_keys = {item["name"]: item["key"] for item in normalized_entities}
        normalized_relationships = []
        for rel in relationships:
            source_name = self._canonicalize_name(rel.get("source", ""))
            target_name = self._canonicalize_name(rel.get("target", ""))
            if source_name not in entity_keys or target_name not in entity_keys:
                continue
            normalized_relationships.append(
                {
                    "source_key": entity_keys[source_name],
                    "target_key": entity_keys[target_name],
                    "source_name": source_name,
                    "target_name": target_name,
                    "type": self._sanitize_relationship_type(rel.get("type", "RELATED_TO")),
                    "period": str(rel.get("period", "Current")).strip(),
                    "description": str(rel.get("description", "")).strip(),
                }
            )

        def work(session):
            session.run(
                """
                MERGE (s:Source {url: $url})
                ON CREATE SET s.first_seen_at = datetime()
                SET s.title = $title,
                    s.domain = $domain,
                    s.content_hash = $content_hash,
                    s.updated_at = datetime()
                """,
                url=source_url,
                title=source_title,
                domain=source_domain,
                content_hash=source_hash,
            )

            for entity in normalized_entities:
                session.run(
                    """
                    MERGE (e:Entity {key: $key})
                    ON CREATE SET e.created_at = datetime(), e.name = $name, e.type = $type
                    SET e.updated_at = datetime(),
                        e.type = $type,
                        e.name = $name,
                        e.description = CASE
                            WHEN e.description IS NULL OR size(trim(e.description)) = 0 THEN $description
                            WHEN size($description) > size(e.description) THEN $description
                            ELSE e.description
                        END,
                        e.embedding = CASE WHEN size($embedding) > 0 THEN $embedding ELSE e.embedding END
                    WITH e
                    MATCH (s:Source {url: $url})
                    MERGE (s)-[r:MENTIONS]->(e)
                    ON CREATE SET r.first_seen_at = datetime(), r.mention_count = 1
                    SET r.updated_at = datetime(), r.mention_count = coalesce(r.mention_count, 0) + 1
                    """,
                    **entity,
                    url=source_url,
                )
                if entity["type"] != "Entity":
                    session.run(
                        f"""
                        MATCH (e:Entity {{key: $key}})
                        SET e:{entity["type"]}
                        """,
                        key=entity["key"],
                    )

            for rel in normalized_relationships:
                session.run(
                    f"""
                    MATCH (a:Entity {{key: $source_key}})
                    MATCH (b:Entity {{key: $target_key}})
                    MERGE (a)-[r:{rel["type"]} {{period: $period}}]->(b)
                    ON CREATE SET r.first_seen_at = datetime(), r.evidence_count = 1
                    SET r.updated_at = datetime(),
                        r.source_urls = CASE
                            WHEN r.source_urls IS NULL THEN [$url]
                            WHEN $url IN r.source_urls THEN r.source_urls
                            ELSE r.source_urls + [$url]
                        END,
                        r.description = CASE
                            WHEN r.description IS NULL OR size(trim(r.description)) = 0 THEN $description
                            WHEN size($description) > size(r.description) THEN $description
                            ELSE r.description
                        END,
                        r.evidence_count = coalesce(r.evidence_count, 0) + 1
                    """,
                    **rel,
                    url=source_url,
                )
            return True

        if not self.driver:
            return False
            
        try:
            with self.driver.session() as session:
                return session.execute_write(work)
        except Exception as e:
            print(f"Neo4j write error: {e}")
            return False

    def retrieve_relevant_subgraph(self, query_text: str, limit: int = 8) -> list[dict[str, Any]]:
        if not self.driver:
            return []

        terms = self._extract_query_terms(query_text)
        query_embedding = get_embedding(query_text)
        term_counter = Counter(terms)

        def work(session):
            return list(
                session.run(
                    """
                    MATCH (a:Entity)
                    OPTIONAL MATCH (a)-[r]->(b:Entity)
                    RETURN
                        a.key AS source_key,
                        a.name AS source_name,
                        a.type AS source_type,
                        a.description AS source_description,
                        a.embedding AS source_embedding,
                        type(r) AS relation_type,
                        r.period AS relation_period,
                        r.description AS relation_description,
                        coalesce(r.evidence_count, 0) AS evidence_count,
                        b.key AS target_key,
                        b.name AS target_name,
                        b.type AS target_type,
                        b.description AS target_description
                    LIMIT 300
                    """
                )
            )

        try:
            with self.driver.session() as session:
                rows = session.execute_read(work) or []
        except Exception as e:
            print(f"Neo4j read error: {e}")
            rows = []
        scored_rows = []

        for row in rows:
            text_parts = [
                row.get("source_name") or "",
                row.get("source_type") or "",
                row.get("source_description") or "",
                row.get("relation_type") or "",
                row.get("relation_description") or "",
                row.get("target_name") or "",
                row.get("target_type") or "",
                row.get("target_description") or "",
            ]
            blob = " ".join(text_parts).lower()
            term_score = sum(count for term, count in term_counter.items() if term in blob)
            embedding_score = 0.0
            source_embedding = row.get("source_embedding") or []
            if query_embedding and source_embedding:
                try:
                    embedding_score = max(compute_similarity(query_text, row.get("source_description") or row.get("source_name") or ""), 0.0)
                except Exception:
                    embedding_score = 0.0

            graph_score = math.log1p(row.get("evidence_count", 0))
            score = term_score * 1.5 + embedding_score * 3 + graph_score
            if score <= 0 and terms:
                continue
            row_data = dict(row)
            row_data["score"] = score
            scored_rows.append(row_data)

        scored_rows.sort(key=lambda item: item["score"], reverse=True)
        return scored_rows[:limit]

    def query_graph(self, query_text: str) -> str:
        rows = self.retrieve_relevant_subgraph(query_text)
        context_lines = []
        for row in rows:
            source_name = row.get("source_name") or "Unknown"
            source_type = row.get("source_type") or "Entity"
            source_description = row.get("source_description") or "No description."
            target_name = row.get("target_name")
            relation_type = row.get("relation_type")
            relation_period = row.get("relation_period") or "Current"
            relation_description = row.get("relation_description") or ""
            if target_name and relation_type:
                context_lines.append(
                    f"[{relation_period}] {source_name} ({source_type}) {relation_type} {target_name}. "
                    f"Entity context: {source_description}. Relationship detail: {relation_description}".strip()
                )
            else:
                context_lines.append(f"{source_name} ({source_type}): {source_description}")
        return "\n".join(dict.fromkeys(context_lines))

    def get_graph_data(self, limit: int = 120):
        if not self.driver:
            return [], []

        nodes, edges = [], []
        seen_nodes = set()

        def work(session):
            return list(
                session.run(
                    """
                    MATCH (n:Entity)
                    OPTIONAL MATCH (n)-[r]->(m:Entity)
                    RETURN
                        n.key AS source_key,
                        n.name AS source_name,
                        n.type AS source_type,
                        type(r) AS rel_type,
                        r.period AS rel_period,
                        coalesce(r.evidence_count, 0) AS evidence_count,
                        m.key AS target_key,
                        m.name AS target_name,
                        m.type AS target_type
                    LIMIT $limit
                    """,
                    limit=limit,
                )
            )

        try:
            with self.driver.session() as session:
                result = session.execute_read(work) or []
        except Exception as e:
            print(f"Neo4j get_graph_data error: {e}")
            result = []
        for record in result:
            src_key = record["source_key"]
            src_name = record["source_name"]
            src_type = record["source_type"] or "Entity"
            target_key = record["target_key"]
            target_name = record["target_name"]
            target_type = record["target_type"] or "Entity"
            rel_type = record["rel_type"]
            evidence_count = record["evidence_count"]

            rel_period = record.get("rel_period") or "Current"

            if src_key and src_key not in seen_nodes:
                nodes.append({"id": src_key, "label": src_name, "group": src_type})
                seen_nodes.add(src_key)
            if target_key and target_key not in seen_nodes:
                nodes.append({"id": target_key, "label": target_name, "group": target_type})
                seen_nodes.add(target_key)
            if src_key and target_key and rel_type:
                edges.append(
                    {
                        "source": src_key,
                        "target": target_key,
                        "label": f"[{rel_period}] {rel_type} ({evidence_count})" if evidence_count else f"[{rel_period}] {rel_type}",
                    }
                )
        return nodes, edges


neo4j_manager = Neo4jManager()
