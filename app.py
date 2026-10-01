import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Lê a URL do banco da variável de ambiente DATABASE_URL.
# No Render, essa variável está configurada no painel.
# No seu PC, ela pode não existir — nesse caso, usamos um valor vazio.
database_url = os.environ.get("DATABASE_URL", "")

# O SQLAlchemy exige que a URL comece com "postgresql://".
# Alguns provedores (Heroku, antigamente) entregavam "postgres://".
# Aqui, por garantia, normalizamos.
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://"):      
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)


app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


@app.route("/")
def home():
    # Tenta abrir uma conexão com o banco e rodar um SELECT 1 simples.
    # Se funcionar, mostramos "Banco conectado!".
    # Se falhar, mostramos o erro — para a gente saber o que está acontecendo.
    try:
        db.session.execute(db.text("SELECT 1"))
        status = "Banco conectado! ✅"
    except Exception as e:
        status = f"Erro ao conectar no banco: {e}"
    return f"Dark Library está no ar! 🎉<br>{status}"


if __name__ == "__main__":
    app.run(debug=True)

    