import unittest
from pathlib import Path
from backend.services.rag_service import RAGService, tokenize


class TestPhase9RAG(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("backend/data/test_docs")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.test_db = "backend/data/test_rag.db"
        self.rag = RAGService(doc_dir=str(self.test_dir), db_path=self.test_db)

    def tearDown(self):
        for f in self.test_dir.glob("*"):
            try:
                f.unlink()
            except Exception:
                pass
        try:
            self.test_dir.rmdir()
        except Exception:
            pass
        test_db_path = Path(self.test_db)
        if test_db_path.exists():
            try:
                test_db_path.unlink()
            except Exception:
                pass

    def test_01_tokenize(self):
        tokens = tokenize("What did my project notes say about SQLite database?")
        self.assertIn("project", tokens)
        self.assertIn("sqlite", tokens)
        self.assertIn("database", tokens)
        self.assertNotIn("what", tokens)
        self.assertNotIn("about", tokens)

    def test_02_indexing_and_search(self):
        doc1 = self.test_dir / "setup.md"
        doc1.write_text(
            "# Architecture\n\nAURA uses Faster-Whisper on CPU and Ollama on GPU.\n\n"
            "## Database Configuration\nWe use SQLite database named aura.db for zero-config persistence.",
            encoding="utf-8",
        )

        res = self.rag.index_directory()
        self.assertGreater(res["total_files"], 0)

        matches = self.rag.search("SQLite database configuration")
        self.assertGreater(len(matches), 0)
        self.assertEqual(matches[0]["doc_name"], "setup.md")
        self.assertIn("SQLite", matches[0]["snippet"])

    def test_03_format_context_for_prompt(self):
        matches = [
            {"doc_name": "guide.txt", "snippet": "Press spacebar to activate AURA push to talk."}
        ]
        context = self.rag.format_context_for_prompt(matches)
        self.assertIn("guide.txt", context)
        self.assertIn("push to talk", context)


if __name__ == "__main__":
    unittest.main()
