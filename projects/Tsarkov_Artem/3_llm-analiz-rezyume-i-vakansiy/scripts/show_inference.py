"""Run from the repository root: python scripts/show_inference.py"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skillmatch.embedding.embedders import TfidfEmbedder
from skillmatch.explain.explainers import LLMExplainer
from skillmatch.extraction.extractors import GazetteerExtractor, HybridExtractor, LLMExtractor, SemanticExtractor
from skillmatch.facade import SkillMatchFacade
from skillmatch.llm import OpenAICompatibleLLM
from skillmatch.parsing.parsers import parse
from skillmatch.storage.repository import InMemoryRepository
from skillmatch.taxonomy import SKILLS


class RecordedClient(OpenAICompatibleLLM):
    def complete(self, system, user, max_tokens=800):
        if "evidence" in system:
            item = {"type": "object", "properties": {"name": {"type": "string"}, "evidence": {"type": "string"}},
                    "required": ["name", "evidence"]}
            fields = {"skills": {"type": "array", "items": item, "maxItems": 12}}
        else:
            fields = {"verdict": {"type": "string", "enum": ["подходит", "частично подходит", "не подходит"]},
                      "summary": {"type": "string"}, "recommendations": {"type": "array", "items": {"type": "string"}}}
        schema = {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}
        response = self.http.post("/chat/completions", json={
            "model": self.model, "temperature": 0, "seed": 1, "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "result", "schema": schema}},
        })
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"]
        self.calls.append({"input": user, "raw_output": reply})
        return reply


def main():
    data = ROOT / "dataset"
    resumes, vacancies = [
        [json.loads(line) for line in (data / filename).read_text(encoding="utf-8").splitlines()]
        for filename in ("resumes.jsonl", "vacancies.jsonl")
    ]
    vacancy = vacancies[0]
    resume = next(row for row in resumes if row["role"] == vacancy["role"])
    client = RecordedClient(os.getenv("LLM_BASE_URL", "http://127.0.0.1:18083/v1"),
                            os.getenv("LLM_MODEL", "Qwen2.5-0.5B-Instruct"),
                            os.getenv("LLM_API_KEY", "none"), timeout=240, retries=0)
    client.calls = []
    embedder = TfidfEmbedder([skill.description for skill in SKILLS.values()])
    extractor = HybridExtractor(GazetteerExtractor(), SemanticExtractor(embedder), LLMExtractor(client))
    facade = SkillMatchFacade(InMemoryRepository(), extractor, embedder, LLMExplainer(client))
    documents = []
    for row in (resume, vacancy):
        text = parse(row["text"].encode("utf-8"), row["id"] + ".txt")
        doc = facade.ingest(row["type"], text, row["id"])
        documents.append({**doc.public(), "embedding_size": len(doc.embedding)})
    match = facade.match(resume["id"], vacancy["id"])
    if len(client.calls) != 3:
        raise RuntimeError("Expected two model responses for extraction and one for explanation")
    result = {"model": client.model, "embedder": embedder.name, "documents": documents,
              "model_calls": client.calls, "match": match}
    output = ROOT / "docs/demo/inference.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

