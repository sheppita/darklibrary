import os
import re
from flask import Flask, render_template, request, redirect, url_for
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

    def __repr__(self):
        return f"<Livro {self.titulo}>"


# ─────────────────────────────────────────────
# Funções auxiliares de ordenação
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
    """Usada só para ordenar a lista de estantes (dropdown e estatísticas)."""
    estante = (estante or "").strip().upper()
    m = re.fullmatch(r"([A-Z]+)(\d+)", estante)
    if m:
        return (0, m.group(1), int(m.group(2)))
    return (1, estante, 0)


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

    # Pré-calcula o hex da cor da lombada de cada livro.
    for livro in livros:
        cor = (livro.cor_lombada or "").strip()
        livro.cor_hex = CORES_HEX.get(cor, CORES_HEX["Multi"])

    # Agrupa por estante.
    grupos = []
    estante_atual = "__inicio__"
    for livro in livros:
        if livro.estante != estante_atual:
            grupos.append((livro.estante, []))
            estante_atual = livro.estante
        grupos[-1][1].append(livro)

    # Monta o degradê CSS para cada grupo.
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

    # Estantes disponíveis no banco (para o dropdown).
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

    return render_template("novo.html", cores=CORES_ORDEM)


@app.route("/estatisticas")
def estatisticas():
    # ── Totais gerais ──
    total = Livro.query.count()
    total_lidos = Livro.query.filter(Livro.lido.is_(True)).count()
    total_nao_lidos = total - total_lidos

    if total > 0:
        pct_lidos = round(total_lidos / total * 100)
    else:
        pct_lidos = 0

    # ── Por estante ──
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

    # ── Top autores ──
    top_autores = (
        db.session.query(Livro.autor, db.func.count(Livro.id))
        .group_by(Livro.autor)
        .order_by(db.func.count(Livro.id).desc(), Livro.autor.asc())
        .all()
    )

    # ── Por nacionalidade ──
    por_nacionalidade = (
        db.session.query(Livro.nacionalidade, db.func.count(Livro.id))
        .group_by(Livro.nacionalidade)
        .order_by(db.func.count(Livro.id).desc())
        .all()
    )

    # ── Por cor ──
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


# ─────────────────────────────────────────────
# Criação automática da tabela
# ─────────────────────────────────────────────

with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
