import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ─────────────────────────────────────────────
# Configuração do banco de dados
# ─────────────────────────────────────────────

database_url = os.environ.get("DATABASE_URL", "")

# O SQLAlchemy precisa saber QUAL driver usar.
# O Neon entrega a URL no formato "postgresql://".
# Nós usamos o driver psycopg (v3), então precisamos
# escrever "postgresql+psycopg://" na URL.
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

db = SQLAlchemy(app)


# ─────────────────────────────────────────────
# Modelo: define a tabela "livro" no banco
# ─────────────────────────────────────────────

class Livro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(150), nullable=False)
    nacionalidade = db.Column(db.String(80))
    cor_lombada = db.Column(db.String(20))
    estante = db.Column(db.String(20))
    isbn = db.Column(db.String(20))
    lido = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Livro {self.titulo}>"


# ─────────────────────────────────────────────
# Rotas
# ─────────────────────────────────────────────

@app.route("/")
def home():
    """Página inicial: lista todos os livros, mais recentes primeiro."""
    livros = Livro.query.order_by(Livro.id.desc()).all()
    return render_template("lista.html", livros=livros)


@app.route("/novo", methods=["GET", "POST"])
def novo():
    """Página de cadastro de livro."""
    if request.method == "POST":
        # request.form.get("nome") devolve o valor enviado pelo formulário.
        # Usamos .get() (em vez de ["nome"]) para evitar erro se o campo
        # não vier; nesse caso, devolve None.
        # O "or None" transforma string vazia ("") em None,
        # para não guardar "" no banco.
        livro = Livro(
            titulo=request.form.get("titulo", "").strip(),
            autor=request.form.get("autor", "").strip(),
            nacionalidade=request.form.get("nacionalidade", "").strip() or None,
            cor_lombada=request.form.get("cor_lombada", "").strip() or None,
            estante=request.form.get("estante", "").strip().upper() or None,
            isbn=request.form.get("isbn", "").strip() or None,
            lido=("lido" in request.form),
        )
        db.session.add(livro)
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("novo.html")


# ─────────────────────────────────────────────
# Criação automática da tabela (na primeira execução)
# ─────────────────────────────────────────────

with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
    