import os
import sqlite3
import tempfile
import unittest

from werkzeug.security import check_password_hash

from app import app


class PaginasRestritasTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_database = app.config["DATABASE"]
        app.config.update(
            TESTING=True,
            DATABASE=os.path.join(self.temp_dir.name, "test.sqlite3"),
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config["DATABASE"] = self.original_database
        self.temp_dir.cleanup()

    def test_paginas_restritas_exigem_login(self):
        for caminho in ("/boletim", "/atividades"):
            resposta = self.client.get(caminho)
            self.assertEqual(resposta.status_code, 302)
            self.assertIn("/login?next=", resposta.location)

    def test_login_valida_senha_com_hash(self):
        resposta = self.client.post(
            "/login", data={"usuario": "aluno", "senha": "senha123"}
        )
        self.assertEqual(resposta.status_code, 302)
        with sqlite3.connect(app.config["DATABASE"]) as db:
            senha_hash = db.execute(
                "SELECT senha_hash FROM usuarios WHERE usuario = ?", ("aluno",)
            ).fetchone()[0]
        self.assertNotEqual(senha_hash, "senha123")
        self.assertTrue(check_password_hash(senha_hash, "senha123"))

    def test_senha_incorreta_nao_autentica(self):
        resposta = self.client.post(
            "/login", data={"usuario": "aluno", "senha": "incorreta"}
        )
        self.assertIn("Usuário ou senha incorretos".encode(), resposta.data)
        self.assertEqual(self.client.get("/boletim").status_code, 302)

    def test_paginas_exibem_dados_do_sqlite(self):
        self.client.post(
            "/login", data={"usuario": "aluno", "senha": "senha123"}
        )
        with sqlite3.connect(app.config["DATABASE"]) as db:
            db.execute(
                "INSERT INTO notas (materia, bimestre, nota) VALUES (?, ?, ?)",
                ("Banco de Dados", "2º bimestre", 10),
            )
            db.execute(
                "INSERT INTO atividades (titulo, descricao, data) VALUES (?, ?, ?)",
                ("Atividade dinâmica", "Conteúdo do banco", "2026-11-01"),
            )

        self.assertIn("Banco de Dados".encode(), self.client.get("/boletim").data)
        self.assertIn(
            "Atividade dinâmica".encode(), self.client.get("/atividades").data
        )

    def test_logout_remove_acesso(self):
        self.client.post(
            "/login", data={"usuario": "aluno", "senha": "senha123"}
        )
        self.client.post("/logout")
        self.assertEqual(self.client.get("/atividades").status_code, 302)


if __name__ == "__main__":
    unittest.main()