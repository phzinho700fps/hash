import os
import sqlite3
from functools import wraps

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "chave-de-desenvolvimento")
app.config["DATABASE"] = os.path.join(app.instance_path, "site.sqlite3")
os.makedirs(app.instance_path, exist_ok=True)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY,
            usuario TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notas (
            id INTEGER PRIMARY KEY,
            materia TEXT NOT NULL,
            bimestre TEXT NOT NULL,
            nota REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS atividades (
            id INTEGER PRIMARY KEY,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            data TEXT NOT NULL
        );
        """
    )

    if db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
        db.execute(
            "INSERT INTO usuarios (usuario, senha_hash) VALUES (?, ?)",
            ("aluno", generate_password_hash("senha123")),
        )
    if db.execute("SELECT COUNT(*) FROM notas").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO notas (materia, bimestre, nota) VALUES (?, ?, ?)",
            [("Web II", "1º bimestre", 9.5), ("Python", "1º bimestre", 8.5)],
        )
    if db.execute("SELECT COUNT(*) FROM atividades").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO atividades (titulo, descricao, data) VALUES (?, ?, ?)",
            [
                ("Projeto Flask", "Criar páginas com autenticação e SQLite.", "2026-10-10"),
                ("Exercícios de Python", "Entregar a lista de exercícios da turma.", "2026-10-15"),
            ],
        )
    db.commit()


@app.before_request
def prepare_database():
    init_db()


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.path))
        return view(**kwargs)

    return wrapped_view


@app.route("/")
def index():
    aluno = {"nome": "Fumaça", "turma": "2° Ensino Médio Técnico"}
    professores = [
        {"nome": "Felipe Ishara", "materia": "Web II"},
        {"nome": "Mano Garbas", "materia": "Python"},
    ]
    return render_template("index.html", title="home", aluno=aluno, professores=professores)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")
        user = get_db().execute(
            "SELECT id, usuario, senha_hash FROM usuarios WHERE usuario = ?", (usuario,)
        ).fetchone()

        if user is not None and check_password_hash(user["senha_hash"], senha):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["usuario"]
            destino = request.args.get("next", "")
            if destino.startswith("/") and not destino.startswith("//"):
                return redirect(destino)
            return redirect(url_for("boletim"))
        flash("Usuário ou senha incorretos.")

    return render_template("login.html", title="Entrar")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/boletim")
@login_required
def boletim():
    notas = get_db().execute(
        "SELECT materia, bimestre, nota FROM notas ORDER BY materia, bimestre"
    ).fetchall()
    return render_template("boletim.html", title="Boletim", notas=notas)


@app.route("/atividades")
@login_required
def atividades():
    lista = get_db().execute(
        "SELECT titulo, descricao, data FROM atividades ORDER BY data"
    ).fetchall()
    return render_template("atividades.html", title="Atividades", atividades=lista)


@app.route("/sobre")
def sobre():
    return render_template("sobre.html", title="sobre mim")


@app.route("/validacao", methods=["GET", "POST"])
def validacao():
    nome = ""
    sobrenome = ""
    idade = ""
    pode_votar = None
    pode_dirigir = None

    if request.method == "POST":
        nome = request.form.get("nome", "")
        sobrenome = request.form.get("sobrenome", "")
        idade_texto = request.form.get("idade", "")

        try:
            idade = int(idade_texto)
        except (TypeError, ValueError):
            idade = idade_texto

        if isinstance(idade, int):
            pode_votar = idade >= 18
            pode_dirigir = idade >= 18

    return render_template(
        "validacao.html",
        title="Validação",
        nome=nome,
        sobrenome=sobrenome,
        idade=idade,
        pode_votar=pode_votar,
        pode_dirigir=pode_dirigir,
    )