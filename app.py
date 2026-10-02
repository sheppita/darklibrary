import os
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, Response, jsonify
import requests
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# ─────────────────────────────────────────────
# Configuração do banco de dados
# ─────────────────────────────────────────────

database_url = os.environ.get("DATABASE_URL", "")

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
# Constantes
# ─────────────────────────────────────────────

CORES_ORDEM = [
    "Branco", "Verde", "Azul", "Rosa", "Marrom",
    "Vermelho", "Laranja", "Amarelo", "Cinza", "Preto", "Multi",
]
CORES_INDICE = {cor: i for i, cor in enumerate(CORES_ORDEM)}

CORES_HEX = {
    "Branco":   "#f0ede6",
    "Verde":    "#4a7c59",
    "Azul":     "#3d5a80",
    "Rosa":     "#d88ba6",
    "Marrom":   "#7a5c3e",
    "Vermelho": "#b33a3a",
    "Laranja":  "#d97736",
    "Amarelo":  "#e0b73c",
    "Cinza":    "#9a9a9a",
    "Preto":    "#2a2a2a",
    "Multi":    "#e8dfc9",
}


# ─────────────────────────────────────────────
# Modelo
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
    capa_url = db.Column(db.String(500))

    def __repr__(self):
        return f"<Livro {self.titulo}>"


# ─────────────────────────────────────────────
# Funções auxiliares
# ─────────────────────────────────────────────

def chave_ordenacao(livro):
    estante = (livro.estante or "").strip().upper()
    if not estante:
        grupo_estante = (1, "", 0)
    else:
        m = re.fullmatch(r"([A-Z]+)(\d+)", estante)
        if m:
            grupo_estante = (0, m.group(1), int(m.group(2)))
        else:
            grupo_estante = (1, estante, 0)

    cor = (livro.cor_lombada or "").strip()
    ordem_cor = CORES_INDICE.get(cor, CORES_INDICE["Multi"])

    titulo = (livro.titulo or "").lower()

    return (grupo_estante, ordem_cor, titulo)


def chave_ordenacao_estante_simples(estante):
    estante = (estante or "").strip().upper()
    m = re.fullmatch(r"([A-Z]+)(\d+)", estante)
    if m:
        return (0, m.group(1), int(m.group(2)))
    return (1, estante, 0)


def sql_escape(valor):
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "TRUE" if valor else "FALSE"
    texto = str(valor).replace("'", "''")
    return f"'{texto}'"


def url_capa_open_library(isbn):
    if not isbn:
        return None
    isbn_limpo = re.sub(r"[^0-9Xx]", "", isbn)
    if not isbn_limpo:
        return None
    return f"https://covers.openlibrary.org/b/isbn/{isbn_limpo}-L.jpg?default=false"


def buscar_google_books(isbn_limpo):
    """
    Consulta o Google Books pelo ISBN.
    Devolve um dict com titulo, autor, capa — ou None se não achou.
    """
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_limpo}"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        dados = r.json()
    except requests.RequestException:
        return None

    items = dados.get("items", [])
    if not items:
        return None

    info = items[0].get("volumeInfo", {})
    titulo = info.get("title", "")
    autores = info.get("authors", [])
    autor = autores[0] if autores else ""

    # A capa vem com http:// e &zoom=1. Ajustamos:
    capa = ""
    links = info.get("imageLinks", {})
    if links:
        capa = links.get("thumbnail") or links.get("smallThumbnail") or ""
        if capa:
            capa = capa.replace("http://", "https://", 1)
            capa = re.sub(r"&zoom=\d+", "", capa)

    return {"titulo": titulo, "autor": autor, "capa": capa}


def buscar_open_library(isbn_limpo):
    """
    Consulta a Open Library pelo ISBN.
    Devolve um dict com titulo, autor, capa — ou None se não achou.
    """
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn_limpo}&format=json&jscmd=data"
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        dados = r.json()
    except requests.RequestException:
        return None

    chave = f"ISBN:{isbn_limpo}"
    if chave not in dados:
        return None

    info = dados[chave]
    titulo = info.get("title", "")
    autores = info.get("authors", [])
    autor = autores[0]["name"] if autores else ""

    capa = ""
    if "cover" in info and "medium" in info["cover"]:
        capa = info["cover"]["medium"]

    return {"titulo": titulo, "autor": autor, "capa": capa}


# ─────────────────────────────────────────────
# Rotas
# ─────────────────────────────────────────────

@app.route("/")
def home():
    busca = request.args.get("q", "").strip()
    filtro_estante = request.args.get("estante", "").strip().upper()
    filtro_cor = request.args.get("cor", "").strip()
    filtro_status = request.args.get("status", "").strip()

    query = Livro.query

    if busca:
        termo = f"%{busca}%"
        query = query.filter(
            db.or_(
                Livro.titulo.ilike(termo),
                Livro.autor.ilike(termo),
            )
        )

    if filtro_estante:
        query = query.filter(Livro.estante == filtro_estante)

    if filtro_cor:
        query = query.filter(Livro.cor_lombada == filtro_cor)

    if filtro_status == "lido":
        query = query.filter(Livro.lido.is_(True))
    elif filtro_status == "nao_lido":
        query = query.filter(Livro.lido.is_(False))

    livros = query.all()
    livros.sort(key=chave_ordenacao)

    for livro in livros:
        cor = (livro.cor_lombada or "").strip()
        livro.cor_hex = CORES_HEX.get(cor, CORES_HEX["Multi"])

        if livro.capa_url:
            livro.capa_final = livro.capa_url
        else:
            livro.capa_final = url_capa_open_library(livro.isbn)

    grupos = []
    estante_atual = "__inicio__"
    for livro in livros:
        if livro.estante != estante_atual:
            grupos.append((livro.estante, []))
            estante_atual = livro.estante
        grupos[-1][1].append(livro)

    grupos_com_gradiente = []
    for estante, livros_do_grupo in grupos:
        cores = [livro.cor_hex for livro in livros_do_grupo]

        if len(cores) == 1:
            gradiente = cores[0]
        else:
            passo = 100 / len(cores)
            stops = []
            for i, cor in enumerate(cores):
                inicio = i * passo
                fim = (i + 1) * passo
                stops.append(f"{cor} {inicio:.2f}% {fim:.2f}%")
            gradiente = f"linear-gradient(to right, {', '.join(stops)})"

        grupos_com_gradiente.append((estante, livros_do_grupo, gradiente))

    estantes_disponiveis = sorted(
        [e for (e,) in db.session.query(Livro.estante).distinct().all() if e],
        key=chave_ordenacao_estante_simples,
    )

    return render_template(
        "lista.html",
        grupos=grupos_com_gradiente,
        total=len(livros),
        busca=busca,
        filtro_estante=filtro_estante,
        filtro_cor=filtro_cor,
        filtro_status=filtro_status,
        estantes=estantes_disponiveis,
        cores=CORES_ORDEM,
    )


@app.route("/novo", methods=["GET", "POST"])
def novo():
    if request.method == "POST":
        isbn = request.form.get("isbn", "").strip() or None
        capa_form = request.form.get("capa_url", "").strip() or None

        livro = Livro(
            titulo=request.form.get("titulo", "").strip(),
            autor=request.form.get("autor", "").strip(),
            nacionalidade=request.form.get("nacionalidade", "").strip() or None,
            cor_lombada=request.form.get("cor_lombada", "").strip() or None,
            estante=request.form.get("estante", "").strip().upper() or None,
            isbn=isbn,
            lido=("lido" in request.form),
            capa_url=capa_form or url_capa_open_library(isbn),
        )
        db.session.add(livro)
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("novo.html", cores=CORES_ORDEM)


@app.route("/editar/<int:livro_id>", methods=["GET", "POST"])
def editar(livro_id):
    livro = db.get_or_404(Livro, livro_id)

    if request.method == "POST":
        isbn = request.form.get("isbn", "").strip() or None
        capa_form = request.form.get("capa_url", "").strip() or None

        livro.titulo = request.form.get("titulo", "").strip()
        livro.autor = request.form.get("autor", "").strip()
        livro.nacionalidade = request.form.get("nacionalidade", "").strip() or None
        livro.cor_lombada = request.form.get("cor_lombada", "").strip() or None
        livro.estante = request.form.get("estante", "").strip().upper() or None
        livro.isbn = isbn
        livro.lido = ("lido" in request.form)
        livro.capa_url = capa_form or url_capa_open_library(isbn)

        db.session.commit()
        return redirect(url_for("home"))

    return render_template("editar.html", livro=livro, cores=CORES_ORDEM)


@app.route("/excluir/<int:livro_id>", methods=["GET", "POST"])
def excluir(livro_id):
    livro = db.get_or_404(Livro, livro_id)

    if request.method == "POST":
        db.session.delete(livro)
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("excluir.html", livro=livro)


@app.route("/estatisticas")
def estatisticas():
    total = Livro.query.count()
    total_lidos = Livro.query.filter(Livro.lido.is_(True)).count()
    total_nao_lidos = total - total_lidos

    if total > 0:
        pct_lidos = round(total_lidos / total * 100)
    else:
        pct_lidos = 0

    por_estante_raw = (
        db.session.query(Livro.estante, db.func.count(Livro.id))
        .group_by(Livro.estante)
        .all()
    )
    por_estante = sorted(
        [(e, n) for (e, n) in por_estante_raw if e],
        key=lambda par: chave_ordenacao_estante_simples(par[0]),
    )
    sem_estante = sum(n for (e, n) in por_estante_raw if not e)
    if sem_estante > 0:
        por_estante.append((None, sem_estante))

    top_autores = (
        db.session.query(Livro.autor, db.func.count(Livro.id))
        .group_by(Livro.autor)
        .order_by(db.func.count(Livro.id).desc(), Livro.autor.asc())
        .all()
    )

    por_nacionalidade = (
        db.session.query(Livro.nacionalidade, db.func.count(Livro.id))
        .group_by(Livro.nacionalidade)
        .order_by(db.func.count(Livro.id).desc())
        .all()
    )

    por_cor_raw = dict(
        db.session.query(Livro.cor_lombada, db.func.count(Livro.id))
        .group_by(Livro.cor_lombada)
        .all()
    )
    por_cor = [(cor, por_cor_raw.get(cor, 0)) for cor in CORES_ORDEM]
    sem_cor = por_cor_raw.get(None, 0)

    return render_template(
        "estatisticas.html",
        total=total,
        total_lidos=total_lidos,
        total_nao_lidos=total_nao_lidos,
        pct_lidos=pct_lidos,
        por_estante=por_estante,
        top_autores=top_autores,
        por_nacionalidade=por_nacionalidade,
        por_cor=por_cor,
        sem_cor=sem_cor,
        cores_hex=CORES_HEX,
    )


@app.route("/backup")
def backup():
    livros = Livro.query.order_by(Livro.id).all()

    agora = datetime.now()
    data_iso = agora.strftime("%Y-%m-%d %H:%M:%S")
    data_arquivo = agora.strftime("%Y%m%d-%H%M")

    linhas = []
    linhas.append("-- Dark Library — Backup")
    linhas.append(f"-- Gerado em: {data_iso}")
    linhas.append(f"-- Total de livros: {len(livros)}")
    linhas.append("")
    linhas.append("-- Restauração:")
    linhas.append("-- 1. Abra o SQL Editor do Neon")
    linhas.append("-- 2. Cole este arquivo e execute")
    linhas.append("-- (atenção: os comandos abaixo APAGAM os dados atuais)")
    linhas.append("")
    linhas.append("DELETE FROM livro;")
    linhas.append("")

    if not livros:
        linhas.append("-- Nenhum livro cadastrado.")
    else:
        for livro in livros:
            valores = ", ".join([
                str(livro.id),
                sql_escape(livro.titulo),
                sql_escape(livro.autor),
                sql_escape(livro.nacionalidade),
                sql_escape(livro.cor_lombada),
                sql_escape(livro.estante),
                sql_escape(livro.isbn),
                sql_escape(livro.lido),
                sql_escape(livro.capa_url),
            ])
            linhas.append(
                "INSERT INTO livro (id, titulo, autor, nacionalidade, cor_lombada, estante, isbn, lido, capa_url) "
                f"VALUES ({valores});"
            )

    conteudo = "\n".join(linhas)

    nome_arquivo = f"darklibrary-backup-{data_arquivo}.sql"

    return Response(
        conteudo,
        mimetype="application/sql",
        headers={
            "Content-Disposition": f'attachment; filename="{nome_arquivo}"',
        },
    )


@app.route("/api/buscar_isbn/<isbn>")
def buscar_isbn(isbn):
    isbn_limpo = re.sub(r"[^0-9Xx]", "", isbn)

    if not isbn_limpo:
        return jsonify({"erro": "ISBN vazio"}), 400

    # 1ª tentativa: Google Books
    resultado = buscar_google_books(isbn_limpo)
    fonte = "Google Books"

    # 2ª tentativa: Open Library
    if not resultado:
        resultado = buscar_open_library(isbn_limpo)
        fonte = "Open Library"

    if not resultado:
        return jsonify({"erro": "ISBN não encontrado no Google Books nem na Open Library"}), 404

    titulo = resultado.get("titulo", "")
    autor = resultado.get("autor", "")
    capa = resultado.get("capa", "")

    # Se Google Books achou o livro mas sem capa, tenta Open Library só pela capa.
    if not capa:
        capa_ol = url_capa_open_library(isbn_limpo)
        # Não temos como saber se existe sem fazer HEAD. Vamos devolver a URL
        # da Open Library; se não existir, o onerror do <img> esconde.
        capa = capa_ol

    return jsonify({
        "isbn": isbn_limpo,
        "titulo": titulo,
        "autor": autor,
        "capa": capa,
        "fonte": fonte,
    })


# ─────────────────────────────────────────────
# Criação automática da tabela
# ─────────────────────────────────────────────

with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
    